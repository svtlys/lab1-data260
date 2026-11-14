"""
seed data for the memory consolidation demo (Lab 2, Part 3).

62 entries for one student: 24 one-off facts, 22 entries that repeat 8 earlier facts, and 16 entries
on 6 single-valued topics where the student changed their mind. consolidating keeps the newest
answer for each topic and one copy of each repeated fact, which leaves 38 entries (under 40):
8 outdated answers and 16 duplicates (14 repeats plus 2 old answers that match the newest one) go.
"""

from __future__ import annotations

from typing import Any

from app.assistant.memory import MEMORY_COLLECTION

SEED_SOURCE = "seed"

# (date, category, text)
ONE_OFF = [
    ("2026-08-27", "activity", "Applied to the Data Analyst Intern role at Cobalt Labs"),
    ("2026-09-02", "activity", "Submitted a resume to Harness Labs"),
    ("2026-09-15", "activity", "Registered for the Women in Data meetup"),
    ("2026-09-29", "activity", "Completed the SQL window functions tutorial"),
    ("2026-10-06", "activity", "Finished a Tableau dashboard for the class project"),
    ("2026-10-14", "activity", "Had a mock interview with the career center"),
    ("2026-10-22", "activity", "Updated LinkedIn headline and photo"),
    ("2026-11-03", "activity", "Saved the Machine Learning Engineer posting in Mountain View"),
    ("2026-09-08", "event_interest", "Wants events about cloud certifications"),
    ("2026-09-21", "event_interest", "Curious about the Kafka streaming talk series"),
    ("2026-10-09", "event_interest", "Would attend a hackathon on weekends"),
    ("2026-10-27", "event_interest", "Likes small networking dinners better than large career fairs"),
    ("2026-11-05", "event_interest", "Asked about alumni panels on analytics careers"),
    ("2026-09-11", "note", "Has an interview prep session on Thursdays"),
    ("2026-09-25", "note", "Works part-time at a campus library"),
    ("2026-10-03", "note", "Needs a letter of recommendation from Professor Lee"),
    ("2026-10-18", "note", "Car is unavailable so the commute must be short"),
    ("2026-11-08", "note", "Portfolio site is being rebuilt with React"),
    ("2026-08-30", "profile", "Skills include Python, SQL, and Tableau"),
    ("2026-09-18", "profile", "Has two years of tutoring experience"),
    ("2026-10-12", "profile", "Speaks English and Spanish"),
    ("2026-09-05", "preference", "Likes small teams with mentorship"),
    ("2026-10-01", "preference", "Prefers companies that sponsor conference travel"),
    ("2026-10-30", "preference", "Wants a manager who gives weekly feedback"),
]

# the same fact written again (different case, punctuation, or one extra word); 8 facts, 22 entries
DUPLICATES = [
    ("2026-09-03", "event_interest", "Interested in data engineering roles."),
    ("2026-09-24", "event_interest", "interested in data engineering roles"),
    ("2026-10-20", "event_interest", "Interested in Data-Engineering roles!"),
    ("2026-09-10", "activity", "Attended the resume workshop in Sunnyvale"),
    ("2026-09-28", "activity", "Attended resume workshop in Sunnyvale."),
    ("2026-10-16", "activity", "attended the Resume Workshop in Sunnyvale"),
    ("2026-09-06", "preference", "Likes Python and SQL projects"),
    ("2026-10-02", "preference", "Likes Python, SQL projects"),
    ("2026-11-01", "preference", "likes python and sql projects."),
    ("2026-09-12", "note", "Wants feedback on the portfolio"),
    ("2026-10-08", "note", "Wants feedback on portfolio"),
    ("2026-11-06", "note", "wants feedback on the portfolio!"),
    ("2026-08-29", "profile", "Comfortable with Git and GitHub"),
    ("2026-09-30", "profile", "Comfortable with Git, GitHub"),
    ("2026-10-24", "profile", "comfortable with git and github."),
    ("2026-09-17", "activity", "Followed up with the recruiter at Cobalt Labs"),
    ("2026-10-11", "activity", "Followed up with recruiter at Cobalt Labs"),
    ("2026-11-09", "activity", "Followed up with the recruiter at Cobalt Labs."),
    ("2026-09-19", "event_interest", "Wants to attend more networking events in Cupertino"),
    ("2026-10-29", "event_interest", "Wants to attend more networking events in Cupertino soon"),
    ("2026-09-23", "note", "Prefers email over phone calls from recruiters"),
    ("2026-11-04", "note", "Prefers email over phone calls from recruiters."),
]

# the student changed their mind: 6 topics, 16 entries, the newest entry in each topic is the truth
CHANGED_MIND = [
    ("2026-09-03", "preference", "Prefers on-site jobs near campus"),
    ("2026-09-20", "preference", "Prefers remote jobs"),
    ("2026-10-10", "preference", "Wants a hybrid role"),
    ("2026-11-02", "preference", "Prefers remote jobs only"),
    ("2026-09-07", "profile", "Looking for an internship"),
    ("2026-10-15", "preference", "Looking for a full-time role"),
    ("2026-11-07", "preference", "Wants full-time work after graduation"),
    ("2026-09-04", "profile", "Major is Computer Science."),
    ("2026-10-13", "profile", "Major is Data Science."),
    ("2026-11-09", "profile", "Major is Data Analytics and AI."),
    ("2026-09-09", "profile", "Graduating in 2027"),
    ("2026-11-04", "profile", "Now graduating in 2028 instead"),
    ("2026-09-14", "preference", "Preferred city is Sunnyvale."),
    ("2026-10-21", "preference", "Preferred city is Cupertino."),
    ("2026-09-16", "preference", "Can work 20 hours per week"),
    ("2026-11-05", "preference", "Can work 12 hours a week"),
]

SEED_ROWS = ONE_OFF + DUPLICATES + CHANGED_MIND
EXPECTED_BEFORE = 62
EXPECTED_AFTER = 38


def seed_entries(student_id: int) -> list[dict[str, Any]]:
    """the seed as student_memory documents."""
    return [
        {"_id": f"seed-{student_id}-{n:03d}", "student_id": student_id, "date": day, "category": category,
         "text": text, "source": SEED_SOURCE, "active": True}
        for n, (day, category, text) in enumerate(SEED_ROWS, start=1)
    ]


def seed_student_memory(database: Any, student_id: int) -> int:
    """(re)load the seed for one student. earlier seed rows are replaced; the student's own are kept."""
    collection = database[MEMORY_COLLECTION]
    collection.delete_many({"student_id": student_id, "source": SEED_SOURCE})
    entries = seed_entries(student_id)
    for entry in entries:
        collection.insert_one(entry)
    return len(entries)
