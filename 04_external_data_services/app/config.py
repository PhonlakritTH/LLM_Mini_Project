from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    serpapi_api_key: str = ""
    google_domain: str = "google.co.th"
    google_country: str = "th"
    google_language: str = "th"
    google_location: str = "Bangkok, Thailand"
    provider_timeout: float = 5
    cache_ttl_price: int = 120        # prices change fast
    rate_limit: int = 60
    user_agent: str = "pc-spec-builder/1.0"
    internal_token: str = "dev-internal"
    allowed_outbound_domains: str = "serpapi.com"

settings = Settings()
