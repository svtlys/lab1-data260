from unittest import TestCase

from fastapi.routing import APIRoute

from app.api.routes.jobs import company_jobs_router, student_jobs_router
from app.main import app


def route_signatures(router) -> set[tuple[str, frozenset[str]]]:
    return {
        (route.path, frozenset(route.methods or set()))
        for route in router.routes
        if isinstance(route, APIRoute)
    }


class JobRouterSplitTests(TestCase):
    def test_student_jobs_router_contains_only_student_routes(self):
        self.assertEqual(
            route_signatures(student_jobs_router),
            {
                ("/api/jobs", frozenset({"GET"})),
                ("/api/jobs/{job_id}", frozenset({"GET"})),
            },
        )

    def test_company_jobs_router_contains_only_company_routes(self):
        self.assertEqual(
            route_signatures(company_jobs_router),
            {
                ("/api/companies/me/jobs", frozenset({"POST"})),
                ("/api/companies/me/jobs", frozenset({"GET"})),
            },
        )

    def test_monolith_exposes_each_original_job_endpoint_once(self):
        included_routes = [
            (route.path, frozenset(route.methods or set()))
            for included_router in app.routes
            for route in getattr(
                getattr(included_router, "original_router", None),
                "routes",
                [],
            )
            if isinstance(route, APIRoute)
        ]

        self.assertEqual(
            included_routes.count(("/api/jobs", frozenset({"GET"}))),
            1,
        )
        self.assertEqual(
            included_routes.count(
                ("/api/jobs/{job_id}", frozenset({"GET"}))
            ),
            1,
        )
        self.assertEqual(
            included_routes.count(
                ("/api/companies/me/jobs", frozenset({"GET"}))
            ),
            1,
        )
        self.assertEqual(
            included_routes.count(
                ("/api/companies/me/jobs", frozenset({"POST"}))
            ),
            1,
        )
