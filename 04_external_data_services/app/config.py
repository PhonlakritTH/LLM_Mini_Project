from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    price_api_key: str = "dev-test-key"
    stock_api_key: str = "dev-test-key"
    benchmark_api_key: str = "dev-test-key"
    provider_timeout: float = 5
    cache_ttl_price: int = 120        # prices change fast
    cache_ttl_stock: int = 60
    cache_ttl_benchmark: int = 86400  # benchmarks change slowly
    rate_limit: int = 60
    user_agent: str = "pc-spec-builder/1.0"
    internal_token: str = "dev-internal"
    allowed_outbound_domains: str = "api.mock-retailer.local,api.mock-retailer-backup.local"
    mock_fail: str = ""   # e.g. "price_primary" to force failover

settings = Settings()
