from collections import Counter
from unittest import TestCase

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.main import app as monolith_app
from app.service_entrypoints.application import app as application_app
from app.service_entrypoints.assistant import app as assistant_app
from app.service_entrypoints.company import app as company_app
from app.service_entrypoints.event import app as event_app
from app.service_entrypoints.job import app as job_app
from app.service_entrypoints.student import app as student_app


SERVICE_APPS = {
    "student": (student_app, "p16-student-service"),
    "company": (company_app, "p16-company-service"),
    "job": (job_app, "p16-job-service"),
    "application": (application_app, "p16-application-service"),
    "event": (event_app, "p16-event-service"),
    "assistant": (assistant_app, "p16-assistant-service"),
}


EXPECTED_ROUTES = {
    "student": {
        ("/api/auth/student/signup", "POST"),
        ("/api/auth/company/signup", "POST"),
        ("/api/auth/login", "POST"),
        ("/api/auth/logout", "POST"),
        ("/api/students/me", "GET"),
        ("/api/students/me", "PUT"),
        ("/health", "GET"),
    },
    "company": {
        ("/api/companies/me", "GET"),
        ("/api/companies/me", "PUT"),
        ("/api/companies/me/profile-picture", "POST"),
        ("/api/companies/profile-images/{filename}", "GET"),
        ("/api/companies/me/jobs", "POST"),
        ("/api/companies/me/jobs", "GET"),
        ("/api/companies/me/events", "POST"),
        ("/api/companies/me/events", "GET"),
        ("/api/companies/me/events/{event_id}", "GET"),
        ("/api/companies/me/events/{event_id}/registrations", "GET"),
        ("/api/students/search", "GET"),
        ("/api/students/{student_id}", "GET"),
        ("/health", "GET"),
    },
    "job": {
        ("/api/jobs", "GET"),
        ("/api/jobs/{job_id}", "GET"),
        ("/health", "GET"),
    },
    "application": {
        ("/api/jobs/{job_id}/applications", "POST"),
        ("/api/students/me/applications", "GET"),
        ("/api/companies/me/jobs/{job_id}/applications", "GET"),
        ("/api/companies/me/applications/{application_id}/status", "PATCH"),
        ("/api/companies/me/applications/{application_id}/status", "PUT"),
        ("/api/companies/me/applications/{application_id}/resume", "GET"),
        ("/health", "GET"),
    },
    "event": {
        ("/api/events", "GET"),
        ("/api/events/registered", "GET"),
        ("/api/events/{event_id}", "GET"),
        ("/api/events/{event_id}/register", "POST"),
        ("/health", "GET"),
    },
    "assistant": {
        ("/api/assistant/chat", "POST"),
        ("/health", "GET"),
    },
}


def _route_signatures_from_router(router) -> list[tuple[str, str]]:
    signatures = []
    for route in getattr(router, "routes", []):
        nested_router = getattr(route, "original_router", None)
        if nested_router is not None:
            signatures.extend(_route_signatures_from_router(nested_router))
        elif isinstance(route, APIRoute):
            signatures.extend(
                (route.path, method) for method in (route.methods or set())
            )
    return signatures


def route_signatures(application: FastAPI) -> list[tuple[str, str]]:
    signatures = []
    for route in application.routes:
        nested_router = getattr(route, "original_router", None)
        if nested_router is not None:
            signatures.extend(_route_signatures_from_router(nested_router))
        elif isinstance(route, APIRoute):
            signatures.extend(
                (route.path, method) for method in (route.methods or set())
            )
    return signatures


def health_result(application: FastAPI) -> dict[str, str]:
    for route in application.routes:
        if isinstance(route, APIRoute) and route.path == "/health":
            return route.endpoint()
    raise AssertionError("health route not found")


class ServiceEntrypointTests(TestCase):
    def test_every_service_imports_as_a_fastapi_app(self):
        for application, _service_name in SERVICE_APPS.values():
            self.assertIsInstance(application, FastAPI)

    def test_every_service_has_service_specific_health(self):
        for application, service_name in SERVICE_APPS.values():
            self.assertEqual(
                health_result(application),
                {"status": "healthy", "service": service_name},
            )

    def test_each_service_contains_only_assigned_routes(self):
        for service_name, (application, _service_label) in SERVICE_APPS.items():
            self.assertEqual(
                set(route_signatures(application)),
                EXPECTED_ROUTES[service_name],
            )

    def test_service_routes_have_no_duplicates(self):
        for application, _service_name in SERVICE_APPS.values():
            signatures = route_signatures(application)
            duplicates = [
                signature
                for signature, count in Counter(signatures).items()
                if count > 1
            ]
            self.assertEqual(duplicates, [])

    def test_auth_routes_are_only_in_student_service(self):
        auth_paths = {
            ("/api/auth/student/signup", "POST"),
            ("/api/auth/company/signup", "POST"),
            ("/api/auth/login", "POST"),
            ("/api/auth/logout", "POST"),
        }
        self.assertTrue(auth_paths.issubset(set(route_signatures(student_app))))
        for application in (
            company_app,
            job_app,
            application_app,
            event_app,
            assistant_app,
        ):
            self.assertTrue(auth_paths.isdisjoint(set(route_signatures(application))))

    def test_nested_application_routes_belong_only_to_application_service(self):
        nested_application_paths = {
            ("/api/jobs/{job_id}/applications", "POST"),
            ("/api/students/me/applications", "GET"),
            ("/api/companies/me/jobs/{job_id}/applications", "GET"),
        }
        self.assertTrue(
            nested_application_paths.issubset(set(route_signatures(application_app)))
        )
        for application in (
            student_app,
            company_app,
            job_app,
            event_app,
            assistant_app,
        ):
            self.assertTrue(
                nested_application_paths.isdisjoint(set(route_signatures(application)))
            )

    def test_cors_middleware_is_preserved(self):
        for application, _service_name in SERVICE_APPS.values():
            self.assertTrue(
                any(
                    middleware.cls is CORSMiddleware
                    for middleware in application.user_middleware
                )
            )

    def test_monolith_still_exposes_lab1_routes(self):
        monolith_routes = set(route_signatures(monolith_app))
        required_routes = {
            ("/api/auth/login", "POST"),
            ("/api/students/me", "GET"),
            ("/api/jobs", "GET"),
            ("/api/jobs/{job_id}", "GET"),
            ("/api/jobs/{job_id}/applications", "POST"),
            ("/api/events", "GET"),
            ("/api/assistant/chat", "POST"),
            ("/health", "GET"),
        }
        self.assertTrue(required_routes.issubset(monolith_routes))
