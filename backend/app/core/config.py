"""
application configuration loaded from the local environment file.
"""

from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """store application and security settings."""

    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # configure the local model runtime for the Week 3 assistant
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:8b"
    ollama_timeout_seconds: float = 120.0

    mongo_host: str = "127.0.0.1"
    mongo_port: int = 27017
    mongo_database: str = Field(
        default="p16_handshake",
        validation_alias=AliasChoices("MONGO_DATABASE", "MONGO_INITDB_DATABASE"),
    )
    mongo_username: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "MONGO_USERNAME", "MONGO_INITDB_ROOT_USERNAME"
        ),
    )
    mongo_password: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "MONGO_PASSWORD", "MONGO_INITDB_ROOT_PASSWORD"
        ),
    )
    mongo_reads_enabled: bool = False

    kafka_enabled: bool = False
    kafka_bootstrap_servers: str = "p16-kafka:9092"
    kafka_topic_prefix: str = "p16"
    kafka_request_timeout_ms: int = 5000
    kafka_delivery_timeout_ms: int = 10000
    kafka_publish_timeout_seconds: float = 5.0

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# create one shared settings object for the application
settings = Settings()
