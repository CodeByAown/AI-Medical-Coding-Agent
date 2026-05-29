import warnings
from functools import lru_cache
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "AI Medical Coder"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    json_logs: bool = False

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    api_key_header: str = "X-API-Key"
    allowed_api_keys: str = ""

    # JWT (optional override — uses secret_key by default)
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # PHI Encryption
    phi_encryption_key: Optional[str] = None  # base64 AES-256 key
    enable_phi_encryption: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/medical_coder.db"
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379"

    # LLM
    llm_provider: str = "ollama"
    llm_model: str = "llama3.1:8b"
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout: int = 120
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"

    # Embeddings
    embedding_model: str = "pritamdeka/S-PubMedBert-MS-MARCO"

    # Vector Store
    chroma_persist_dir: str = "./knowledge_base/indices"
    chroma_collection_icd10: str = "icd10_codes"
    chroma_collection_cpt: str = "cpt_codes"
    chroma_collection_hcpcs: str = "hcpcs_codes"

    # Knowledge Base
    knowledge_base_dir: str = "./knowledge_base/data"
    icd10_data_dir: str = "./knowledge_base/data/icd10"
    cpt_data_dir: str = "./knowledge_base/data/cpt"
    hcpcs_data_dir: str = "./knowledge_base/data/hcpcs"

    # Coding
    max_codes_per_request: int = 20
    min_confidence_threshold: float = 0.70
    auto_approve_threshold: float = 0.90
    human_review_threshold: float = 0.70
    rag_top_k: int = 15
    rag_similarity_threshold: float = 0.3

    # NLP
    scispacy_model: str = "en_core_web_sm"
    enable_umls_linking: bool = True

    # Document Processing
    max_document_size_mb: int = 50
    supported_formats: str = "pdf,txt,docx,png,jpg,jpeg,tiff"
    tesseract_cmd: str = "tesseract"
    ocr_language: str = "eng"

    # Review Queue
    review_queue_enabled: bool = True
    auto_expire_hours: int = 72

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8080"
    cors_allow_credentials: bool = True
    cors_allow_all_origins: bool = False

    # Rate limiting
    rate_limit_requests_per_minute: int = 60

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        if v in ("dev-secret-key-change-in-production", "change-this-secret-key-in-production"):
            warnings.warn(
                "SECRET_KEY is using the default development value. "
                "Set a strong SECRET_KEY in production.",
                UserWarning,
                stacklevel=2,
            )
        return v

    @property
    def api_keys_list(self) -> List[str]:
        return [k.strip() for k in self.allowed_api_keys.split(",") if k.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        if self.cors_allow_all_origins:
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def supported_formats_list(self) -> List[str]:
        return [f.strip().lower() for f in self.supported_formats.split(",") if f.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
