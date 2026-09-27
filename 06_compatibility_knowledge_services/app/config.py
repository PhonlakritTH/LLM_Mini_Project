from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    model_uri: str = "local://baseline-v1"
    model_version: str = "1.0.0"
    feature_schema_version: str = "1.0"
    embedding_model: str = "mock-multilingual-embed"
    collection_version: str = "1.0"
    top_k: int = 5
    rerank_top_n: int = 3
    rag_min_confidence: float = 0.35
    value_threshold_compatible: float = 0.8
    value_threshold_needs_review: float = 0.5
    substitution_max_hops: int = 2
    knowledge_cutoff: str = "2026-01-31"
    internal_token: str = "dev-internal"

settings = Settings()
