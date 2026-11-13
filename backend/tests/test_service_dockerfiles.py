from pathlib import Path
from unittest import TestCase


BACKEND_DIR = Path(__file__).resolve().parents[1]

DOCKERFILES = {
    "Dockerfile.student": "app.service_entrypoints.student:app",
    "Dockerfile.company": "app.service_entrypoints.company:app",
    "Dockerfile.job": "app.service_entrypoints.job:app",
    "Dockerfile.application": "app.service_entrypoints.application:app",
    "Dockerfile.event": "app.service_entrypoints.event:app",
    "Dockerfile.assistant": "app.service_entrypoints.assistant:app",
}


class ServiceDockerfileTests(TestCase):
    def test_service_dockerfiles_have_safe_static_configuration(self):
        for filename, entrypoint in DOCKERFILES.items():
            with self.subTest(filename=filename):
                dockerfile = (BACKEND_DIR / filename).read_text(encoding="utf-8")

                self.assertIn("FROM python:3.12-slim", dockerfile)
                self.assertIn("COPY requirements.txt ./requirements.txt", dockerfile)
                self.assertIn("RUN pip install --no-cache-dir -r requirements.txt", dockerfile)
                self.assertIn("COPY app ./app", dockerfile)
                self.assertIn("EXPOSE 8000", dockerfile)
                self.assertIn("HEALTHCHECK", dockerfile)
                self.assertIn(entrypoint, dockerfile)
                self.assertIn('"--host", "0.0.0.0"', dockerfile)
                self.assertIn('"--port", "8000"', dockerfile)

                lowered = dockerfile.lower()
                for forbidden in (
                    ".env",
                    "uploads",
                    ".venv",
                    "node_modules",
                    "__pycache__",
                ):
                    self.assertNotIn(forbidden, lowered)
