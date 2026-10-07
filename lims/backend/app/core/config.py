from enum import StrEnum
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEV = "dev"
    TEST = "test"
    PRODUCTION = "production"


class AuthMode(StrEnum):
    OIDC = "oidc"
    DEV = "dev"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LIMS_", env_file=".env", extra="ignore")

    environment: Environment = Environment.DEV
    database_url: str = "postgresql+psycopg://lims:lims@localhost:5432/lims"

    auth_mode: AuthMode = AuthMode.DEV
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    # Claim that identifies the person; matched against User.oidc_subject.
    oidc_subject_claim: str = "oid"
    # An e-signature needs a token whose auth_time is no older than this.
    signature_reauth_max_age_seconds: int = 300

    file_store: str = "local"  # "local" or "s3"
    file_store_path: str = "./var/files"
    s3_endpoint_url: str | None = None
    s3_bucket: str = "lims-files"
    s3_object_lock_days: int = 3650

    @model_validator(mode="after")
    def _production_guards(self) -> "Settings":
        if self.environment == Environment.PRODUCTION:
            if self.auth_mode != AuthMode.OIDC:
                raise ValueError("Production must use OIDC authentication")
            if not (self.oidc_issuer and self.oidc_audience and self.oidc_jwks_url):
                raise ValueError("Production requires oidc_issuer, oidc_audience, oidc_jwks_url")
            if self.file_store != "s3":
                raise ValueError("Production must use the S3 (object-lock) file store")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
