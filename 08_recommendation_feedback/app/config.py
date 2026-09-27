from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    recommendation_schema_version: str = "1.0"
    feedback_retention_days: int = 180
    price_alert_refresh_interval: int = 300
    notification_provider_keys: str = ""
    warranty_contact_directory_version: str = "2026-01"
    feature_flag_live_alerts: bool = False
    rollout_percentage: int = 100
    internal_token: str = "dev-internal"
    alert_cooldown_seconds: int = 1800

settings = Settings()
