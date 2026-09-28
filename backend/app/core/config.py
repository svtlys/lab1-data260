"""
application configuration loaded from the local environment file.
"""

from pathlib import Path

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

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# create one shared settings object for the application
settings = Settings()