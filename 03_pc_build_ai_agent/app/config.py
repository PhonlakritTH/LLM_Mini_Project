from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    llm_model_planner: str = ""
    llm_api_key: str = ""
    llm_timeout_seconds: float = 20
    max_agent_steps: int = 20
    max_tool_calls: int = 12
    agent_total_timeout: float = 25
    tool_timeout: float = 5
    retry_base_delay: float = 0.2
    price_service_url: str = ""
    stock_service_url: str = ""
    benchmark_service_url: str = ""
    rag_service_url: str = ""
    alternatives_service_url: str = ""
    prompt_version: str = "p1"
    policy_version: str = "policy-2026-09"
    price_max_age_seconds: int = 900
    internal_token: str = "dev-internal"
    mock_fail: str = ""          # e.g. "stock,benchmark" to simulate outages

settings = Settings()
