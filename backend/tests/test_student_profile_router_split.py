from unittest import TestCase

from fastapi.routing import APIRoute

from app.api.dependencies import require_company, require_student
from app.api.routes.student_profile import (
    company_student_router,
    student_profile_router,
)
from app.main import app


def route_signatures(router) -> set[tuple[str, frozenset[str]]]:
    return {
        (route.path, frozenset(route.methods or set()))
        for route in router.routes
        if isinstance(route, APIRoute)
    }


def route_for(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if (
            isinstance(route, APIRoute)
            and route.path == path
            and method in (route.methods or set())
        ):
            return route
    raise AssertionError(f"route not found: {method} {path}")


def included_route_signatures(router) -> list[tuple[str, frozenset[str]]]:
    signatures = []
    for route in getattr(router, "routes", []):
        nested_router = getattr(route, "original_router", None)
        if nested_router is not None:
            signatures.extend(included_route_signatures(nested_router))
        elif isinstance(route, APIRoute):
            signatures.append((route.path, frozenset(route.methods or set())))
    return signatures


class StudentProfileRouterSplitTests(TestCase):
    def test_student_profile_router_contains_only_student_owned_routes(self):
        self.assertEqual(
            route_signatures(student_profile_router),
            {
                ("/api/students/me", frozenset({"GET"})),
                ("/api/students/me", frozenset({"PUT"})),
            },
        )

    def test_company_student_router_contains_only_lookup_routes(self):
        self.assertEqual(
            route_signatures(company_student_router),
            {
                ("/api/students/search", frozenset({"GET"})),
                ("/api/students/{student_id}", frozenset({"GET"})),
            },
        )

    def test_route_dependencies_preserve_role_guards(self):
        student_me = route_for(student_profile_router, "/api/students/me", "GET")
        company_search = route_for(
            company_student_router,
            "/api/students/search",
            "GET",
        )

        student_dependencies = {
            dependency.call for dependency in student_me.dependant.dependencies
        }
        company_dependencies = {
            dependency.call for dependency in company_search.dependant.dependencies
        }

        self.assertIn(require_student, student_dependencies)
        self.assertIn(require_company, company_dependencies)

    def test_monolith_exposes_original_student_paths_once(self):
        included_routes = []
        for included_router in app.routes:
            original_router = getattr(included_router, "original_router", None)
            if original_router is not None:
                included_routes.extend(included_route_signatures(original_router))

        expected = [
            ("/api/students/me", frozenset({"GET"})),
            ("/api/students/me", frozenset({"PUT"})),
            ("/api/students/search", frozenset({"GET"})),
            ("/api/students/{student_id}", frozenset({"GET"})),
        ]

        for route_signature in expected:
            self.assertEqual(included_routes.count(route_signature), 1)
