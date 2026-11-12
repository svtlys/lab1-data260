from pathlib import Path
from unittest import TestCase


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GATEWAY_DIR = REPOSITORY_ROOT / "gateway"


class GatewayConfigTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nginx_config = (GATEWAY_DIR / "nginx.conf").read_text(encoding="utf-8")
        cls.dockerfile = (GATEWAY_DIR / "Dockerfile").read_text(encoding="utf-8")

    def test_all_service_upstreams_exist(self):
        for service_name in (
            "p16-student-service",
            "p16-company-service",
            "p16-job-service",
            "p16-application-service",
            "p16-event-service",
            "p16-assistant-service",
        ):
            with self.subTest(service_name=service_name):
                self.assertIn(f"server {service_name}:8000;", self.nginx_config)

    def test_health_identifies_gateway(self):
        self.assertIn("location = /health", self.nginx_config)
        self.assertIn('"service":"p16-gateway"', self.nginx_config)

    def test_application_routes_precede_general_routes(self):
        ordered_markers = [
            "location ~ ^/api/jobs/[0-9]+/applications",
            "location ~ ^/api/students/me/applications",
            "location ~ ^/api/companies/me/jobs/[0-9]+/applications",
            "location ~ ^/api/companies/me/applications",
            "location ~ ^/api/jobs(?:/|$)",
            "location ~ ^/api/companies(?:/|$)",
            "location ~ ^/api/students(?:/|$)",
        ]
        positions = [self.nginx_config.index(marker) for marker in ordered_markers]
        self.assertEqual(positions, sorted(positions))

    def test_auth_and_assistant_routes_use_expected_services(self):
        auth_position = self.nginx_config.index("location ~ ^/api/auth(?:/|$)")
        assistant_position = self.nginx_config.index(
            "location ~ ^/api/assistant(?:/|$)"
        )
        auth_block = self.nginx_config[auth_position : auth_position + 180]
        assistant_block = self.nginx_config[assistant_position : assistant_position + 200]
        self.assertIn("proxy_pass http://p16_student_service;", auth_block)
        self.assertIn("proxy_pass http://p16_assistant_service;", assistant_block)

    def test_forwarded_headers_and_upload_settings_exist(self):
        for header in (
            "proxy_set_header Authorization $http_authorization;",
            "proxy_set_header Content-Type $http_content_type;",
            "proxy_set_header X-Trace-Id $p16_trace_id;",
        ):
            self.assertIn(header, self.nginx_config)
        self.assertIn("proxy_pass_request_body on;", self.nginx_config)
        self.assertIn("proxy_request_buffering off;", self.nginx_config)
        self.assertIn("client_max_body_size 10m;", self.nginx_config)

    def test_gateway_dockerfile_is_safe(self):
        self.assertIn("FROM nginx:1.27-alpine", self.dockerfile)
        self.assertIn("EXPOSE 80", self.dockerfile)
        self.assertIn("HEALTHCHECK", self.dockerfile)
        self.assertIn("COPY nginx.conf /etc/nginx/nginx.conf", self.dockerfile)
        lowered = self.dockerfile.lower()
        for forbidden in (".env", "uploads", "secrets", "credentials"):
            self.assertNotIn(forbidden, lowered)
