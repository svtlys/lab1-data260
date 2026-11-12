"""
test student profile lookup authorization.
"""

import re
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user, require_company
from app.api.routes.student_profile import get_student_profile, search_students
from app.core.database import Base
from app.models.company_profile import CompanyProfile
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole
from app.schemas.student_profile import StudentProfileResponse, StudentSearchResult


class FakeMongoCursor:
    def __init__(self, documents):
        self.documents = list(documents)

    def sort(self, field, direction):
        return FakeMongoCursor(
            sorted(
                self.documents,
                key=lambda document: document.get(field),
                reverse=direction < 0,
            )
        )

    def __iter__(self):
        return iter(self.documents)


class FakeMongoCollection:
    def __init__(self, documents):
        self.documents = list(documents)

    def find(self, query):
        def matches(document):
            for field, expected in query.items():
                actual = document.get(field)
                if isinstance(expected, dict) and "$regex" in expected:
                    flags = re.IGNORECASE if "i" in expected.get("$options", "") else 0
                    if re.search(expected["$regex"], str(actual or ""), flags) is None:
                        return False
                elif actual != expected:
                    return False
            return True

        return FakeMongoCursor(
            [document for document in self.documents if matches(document)]
        )

    def find_one(self, query):
        return next(iter(self.find(query)), None)


class FakeMongoDatabase:
    def __init__(self, documents):
        self.collections = {"student_profiles": FakeMongoCollection(documents)}

    def __getitem__(self, collection):
        return self.collections[collection]


class StudentLookupTests(TestCase):
    """verify companies can view students and students stay scoped."""

    @classmethod
    def setUpClass(cls):
        # create one shared in-memory database for this test class
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)

    def setUp(self):
        # create two students and one company
        self.db = Session(self.engine)
        self.student_user = User(
            role=UserRole.STUDENT,
            email="lookup-student@example.com",
            password_hash="test-hash",
        )
        self.other_student_user = User(
            role=UserRole.STUDENT,
            email="lookup-other-student@example.com",
            password_hash="test-hash",
        )
        self.company_user = User(
            role=UserRole.COMPANY,
            email="lookup-company@example.com",
            password_hash="test-hash",
        )
        self.db.add_all([self.student_user, self.other_student_user, self.company_user])
        self.db.flush()
        self.student = StudentProfile(
            user_id=self.student_user.id,
            full_name="Lookup Student",
            college_name="Test College",
            major="Computer Science",
            skills="Python, SQL",
            city="Sunnyvale",
            state="CA",
            degree="Bachelor's",
            graduation_year=2027,
        )
        self.other_student = StudentProfile(
            user_id=self.other_student_user.id,
            full_name="Other Student",
            college_name="Other College",
            major="Marketing",
            skills="Writing, Research",
            city="Cupertino",
            state="CA",
        )
        self.db.add_all([self.student, self.other_student])
        self.db.add(
            CompanyProfile(
                user_id=self.company_user.id,
                company_name="Lookup Company",
                location="Sunnyvale",
            )
        )
        self.db.commit()
        self.db.refresh(self.student)
        self.db.refresh(self.other_student)

    def tearDown(self):
        # remove test rows before closing the isolated session
        self.db.query(StudentProfile).delete()
        self.db.query(CompanyProfile).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def migrated_profile_documents(self):
        return [
            {
                "id": profile.id,
                "user_id": profile.user_id,
                "full_name": profile.full_name,
                "college_name": profile.college_name,
                "career_objective": profile.career_objective,
                "date_of_birth": profile.date_of_birth,
                "city": profile.city,
                "state": profile.state,
                "country": profile.country,
                "degree": profile.degree,
                "major": profile.major,
                "graduation_year": profile.graduation_year,
                "cgpa": profile.cgpa,
                "experience": profile.experience,
                "skills": profile.skills,
                "phone": profile.phone,
                "profile_picture_url": profile.profile_picture_url,
                "created_at": profile.created_at,
                "updated_at": profile.updated_at,
            }
            for profile in self.db.query(StudentProfile).all()
        ]

    def test_company_can_view_any_student(self):
        profile = get_student_profile(self.student.id, self.company_user, self.db)
        self.assertEqual(profile.full_name, "Lookup Student")

    def test_mongo_profile_reads_match_mysql_shape(self):
        from app.api.routes.student_profile import get_my_student_profile

        mysql_profile = StudentProfileResponse.model_validate(
            get_my_student_profile(self.student_user, self.db)
        ).model_dump()
        database = FakeMongoDatabase(self.migrated_profile_documents())

        with patch(
            "app.api.routes.student_profile.get_mongo_database",
            return_value=database,
        ):
            mongo_profile = get_my_student_profile(self.student_user, self.db)

        self.assertEqual(mongo_profile, mysql_profile)
        self.assertNotIn("_id", mongo_profile)

    def test_mongo_company_search_matches_mysql_results(self):
        mysql_results = [
            StudentSearchResult.model_validate(profile).model_dump()
            for profile in search_students(
                name="student",
                college="test",
                major="science",
                skills="python",
                current_user=self.company_user,
                db=self.db,
            )
        ]
        database = FakeMongoDatabase(self.migrated_profile_documents())

        with patch(
            "app.api.routes.student_profile.get_mongo_database",
            return_value=database,
        ):
            mongo_results = search_students(
                name="student",
                college="test",
                major="science",
                skills="python",
                current_user=self.company_user,
                db=self.db,
            )

        self.assertEqual(mongo_results, mysql_results)
        self.assertTrue(all("_id" not in result for result in mongo_results))

    def test_mongo_ownership_check_and_sql_fallback_are_preserved(self):
        database = FakeMongoDatabase(self.migrated_profile_documents())
        with patch(
            "app.api.routes.student_profile.get_mongo_database",
            return_value=database,
        ):
            profile = get_student_profile(self.student.id, self.student_user, self.db)
            self.assertEqual(profile["full_name"], "Lookup Student")
            with self.assertRaises(HTTPException) as context:
                get_student_profile(self.other_student.id, self.student_user, self.db)
            self.assertEqual(context.exception.status_code, 403)

        with patch(
            "app.api.routes.student_profile.get_mongo_database",
            side_effect=RuntimeError("mongo unavailable"),
        ):
            profile = get_student_profile(self.student.id, self.student_user, self.db)
        self.assertEqual(profile.full_name, "Lookup Student")

    def test_student_can_view_only_own_profile(self):
        profile = get_student_profile(self.student.id, self.student_user, self.db)
        self.assertEqual(profile.full_name, "Lookup Student")

        with self.assertRaises(HTTPException) as context:
            get_student_profile(self.other_student.id, self.student_user, self.db)
        self.assertEqual(context.exception.status_code, 403)

    def test_company_can_search_by_name(self):
        results = search_students(name="lookup", current_user=self.company_user, db=self.db)
        self.assertEqual([profile.full_name for profile in results], ["Lookup Student"])

    def test_company_can_search_by_college(self):
        results = search_students(college="test college", current_user=self.company_user, db=self.db)
        self.assertEqual([profile.full_name for profile in results], ["Lookup Student"])

    def test_company_can_search_by_major(self):
        results = search_students(major="computer", current_user=self.company_user, db=self.db)
        self.assertEqual([profile.full_name for profile in results], ["Lookup Student"])

    def test_company_can_search_by_skills(self):
        results = search_students(skills="sql", current_user=self.company_user, db=self.db)
        self.assertEqual([profile.full_name for profile in results], ["Lookup Student"])

    def test_company_can_combine_search_filters(self):
        results = search_students(
            name="student",
            college="test",
            major="science",
            skills="python",
            current_user=self.company_user,
            db=self.db,
        )
        self.assertEqual([profile.full_name for profile in results], ["Lookup Student"])

    def test_company_receives_empty_list_for_no_matches(self):
        results = search_students(name="does not exist", current_user=self.company_user, db=self.db)
        self.assertEqual(results, [])

    def test_student_cannot_search_students(self):
        with self.assertRaises(HTTPException) as context:
            require_company(self.student_user)
        self.assertEqual(context.exception.status_code, 403)

    def test_unauthenticated_user_cannot_search_students(self):
        with self.assertRaises(HTTPException) as context:
            get_current_user(token="", db=self.db)
        self.assertEqual(context.exception.status_code, 401)


if __name__ == "__main__":
    import unittest

    unittest.main()
