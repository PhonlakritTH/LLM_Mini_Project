from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    llm_api_key: str = ""
    llm_model_explainer: str = "claude-sonnet-5"
    temperature: float = 0
    decision_policy_version: str = "policy-2026-09"
    prompt_version: str = "p1"
    max_input_tokens: int = 4000
    max_output_tokens: int = 600
    llm_timeout: float = 15
    supported_locales: str = "th-TH,en-US"
    budget_over_tolerance_pct: float = 5
    price_high_vs_trend_pct: float = 12
    internal_token: str = "dev-internal"

settings = Settings()
