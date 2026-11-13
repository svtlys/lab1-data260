"""focused tests for the opt-in MongoDB access foundation."""

import os
from unittest import TestCase
from unittest.mock import Mock, patch

from app.core.config import Settings
from app.core import mongo


class MongoFoundationTests(TestCase):
    def setUp(self):
        mongo.close_mongo_client()

    def tearDown(self):
        mongo.close_mongo_client()

    def make_settings(self, **overrides):
        values = {
            "DB_HOST": "mysql",
            "DB_PORT": "3306",
            "DB_USER": "user",
            "DB_PASSWORD": "password",
            "DB_NAME": "p16_handshake",
            "JWT_SECRET_KEY": "jwt-secret",
            "MONGO_HOST": "p16-mongo",
            "MONGO_PORT": "27017",
            "MONGO_DATABASE": "p16_handshake",
            "MONGO_USERNAME": "mongo-user",
            "MONGO_PASSWORD": "mongo-password",
            "MONGO_READS_ENABLED": "true",
        }
        values.update(overrides)
        with patch.dict(os.environ, values, clear=False):
            return Settings(_env_file=None)

    def test_configuration_loads_mongo_settings_without_printing_secrets(self):
        config = self.make_settings()

        self.assertEqual(config.mongo_host, "p16-mongo")
        self.assertEqual(config.mongo_port, 27017)
        self.assertEqual(config.mongo_database, "p16_handshake")
        self.assertEqual(config.mongo_username.get_secret_value(), "mongo-user")
        self.assertEqual(config.mongo_password.get_secret_value(), "mongo-password")
        self.assertTrue(config.mongo_reads_enabled)

    def test_database_name_prefers_application_variable(self):
        config = self.make_settings(
            MONGO_DATABASE="application_database",
            MONGO_INITDB_DATABASE="image_database",
        )
        self.assertEqual(config.mongo_database, "application_database")

    def test_disabled_feature_flag_does_not_create_a_client(self):
        config = self.make_settings(MONGO_READS_ENABLED="false")

        with patch("app.core.mongo.MongoClient") as client:
            self.assertIsNone(mongo.get_mongo_client(config))
            self.assertIsNone(mongo.get_mongo_database(config))
            self.assertEqual(
                mongo.ping_mongo(config),
                {"enabled": False, "status": "disabled"},
            )
            client.assert_not_called()

    def test_safe_client_creation_uses_pooling_options(self):
        config = self.make_settings()
        fake_client = Mock()

        with patch("app.core.mongo.MongoClient", return_value=fake_client) as client:
            created = mongo.create_mongo_client(config)

        self.assertIs(created, fake_client)
        client.assert_called_once_with(
            host="p16-mongo",
            port=27017,
            username="mongo-user",
            password="mongo-password",
            authSource="admin",
            maxPoolSize=20,
            serverSelectionTimeoutMS=1500,
        )

    def test_ping_failure_is_sanitized(self):
        config = self.make_settings()
        failing_client = Mock()
        failing_client.admin.command.side_effect = RuntimeError(
            "mongodb://mongodb.invalid:27017/p16_handshake"
        )

        with patch("app.core.mongo.MongoClient", return_value=failing_client):
            result = mongo.ping_mongo(config)

        self.assertEqual(result, {"enabled": True, "status": "unavailable"})
        self.assertNotIn("mongodb.invalid", str(result))


if __name__ == "__main__":
    import unittest

    unittest.main()
