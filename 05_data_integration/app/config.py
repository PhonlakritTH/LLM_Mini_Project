from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    canonical_schema_version: str = "1.0"
    default_currency: str = "THB"
    price_freshness_seconds: int = 900
    spec_freshness_seconds: int = 31536000
    quality_weight_freshness: float = 0.4
    quality_weight_coverage: float = 0.4
    quality_weight_completeness: float = 0.2
    retention_days: int = 90
    internal_token: str = "dev-internal"

settings = Settings()
