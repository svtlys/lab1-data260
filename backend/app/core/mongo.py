"""lazy MongoDB access for the opt-in Lab 2 foundation."""

from __future__ import annotations

from typing import Any

from pymongo import MongoClient

from app.core.config import Settings, settings


class MongoConfigurationError(RuntimeError):
    """indicate that Mongo access was requested without safe configuration."""


_client: MongoClient[Any] | None = None


def create_mongo_client(config: Settings = settings) -> MongoClient[Any]:
    """create a pooled client without constructing a credential-bearing URI."""

    if config.mongo_username is None or config.mongo_password is None:
        raise MongoConfigurationError("mongo credentials are not configured")

    return MongoClient(
        host=config.mongo_host,
        port=config.mongo_port,
        username=config.mongo_username.get_secret_value(),
        password=config.mongo_password.get_secret_value(),
        authSource="admin",
        maxPoolSize=20,
        serverSelectionTimeoutMS=1500,
    )


def get_mongo_client(config: Settings = settings) -> MongoClient[Any] | None:
    """return the shared client only when Mongo reads are explicitly enabled."""

    global _client
    if not config.mongo_reads_enabled:
        return None
    if _client is None:
        _client = create_mongo_client(config)
    return _client


def get_mongo_database(config: Settings = settings) -> Any | None:
    """return the configured database or none while the feature flag is off."""

    client = get_mongo_client(config)
    return None if client is None else client[config.mongo_database]


def ping_mongo(config: Settings = settings) -> dict[str, Any]:
    """return sanitized Mongo health status without exposing connection details."""

    if not config.mongo_reads_enabled:
        return {"enabled": False, "status": "disabled"}

    try:
        client = get_mongo_client(config)
        if client is None:
            return {"enabled": False, "status": "disabled"}
        result = client.admin.command("ping")
        return {
            "enabled": True,
            "status": "healthy" if result.get("ok") == 1 else "unhealthy",
        }
    except MongoConfigurationError:
        return {"enabled": True, "status": "not_configured"}
    except Exception:
        return {"enabled": True, "status": "unavailable"}


def close_mongo_client() -> None:
    """close the shared client during application shutdown."""

    global _client
    if _client is not None:
        _client.close()
        _client = None
