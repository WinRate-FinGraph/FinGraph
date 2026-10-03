from pathlib import Path
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PLACEHOLDERS = {
    "", "change-me", "change_me", "change-this-secret-key", "change_me_in_production",
    "fingraph", "fingraph123", "password", "password123",
    "fingraph_qris_local_password", "fingraph_neo4j_password",
}


class Settings(BaseSettings):
    APP_ENV: str = "demo"
    DEMO_MODE: bool = True
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    PROJECT_NAME: str = "FinGraph QRIS API"
    API_VERSION: str = "v1"
    ENABLE_API_DOCS: bool = True
    ENABLE_DEMO_ENDPOINTS: bool = True
    PUBLIC_REGISTRATION_ENABLED: bool = True
    TRUSTED_HOSTS: str = "localhost,127.0.0.1,testserver"

    DATABASE_URL: str | None = None
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "fingraph_qris"
    POSTGRES_USER: str = "fingraph_qris"
    POSTGRES_PASSWORD: str = "fingraph_qris_local_password"

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "fingraph_neo4j_password"
    NEO4J_REQUIRED: bool = False
    NEO4J_CONNECTION_TIMEOUT_SECONDS: float = 3.0
    NEO4J_MAX_RETRY_SECONDS: float = 3.0

    JWT_SECRET_KEY: str = "change-this-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "fingraph-qris"
    JWT_AUDIENCE: str = "fingraph-qris-api"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    PJP_SIMULATOR_SECRET: str = ""
    PJP_SIMULATOR_NAME: str = "TrustPay Sandbox"
    QRIS_WEBHOOK_TOLERANCE_SECONDS: int = 300
    QRIS_DEFAULT_CURRENCY: str = "IDR"
    QRIS_DEMO_MODE: bool = True
    PAYER_PSEUDONYM_KEY: str = ""
    QRIS_ALERT_MIN_SCORE: float = 0.40
    QRIS_LOW_THRESHOLD: float = 0.40
    QRIS_HIGH_THRESHOLD: float = 0.70

    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"
    ADAPTIVE_RETRAIN_MIN_LABELS: int = 5
    ADAPTIVE_RETRAIN_LIMIT_ROWS: int = 200000
    QRIS_ADAPTIVE_MIN_LABELS: int = 10
    MAX_PAGE_SIZE: int = 100
    ML_ARTIFACT_DIR: str = str(Path(__file__).resolve().parents[1] / "ml" / "artifacts")
    ML_ARTIFACT_SIGNING_KEY: str = "demo-artifact-signing-key"
    QRIS_GNN_DATA_DIR: str = "/app/data/raw/qris"
    QRIS_GNN_ENABLED: bool = True
    QRIS_GNN_BLEND_WEIGHT: float = 0.50
    QRIS_GNN_MAX_NODES: int = 500

    AUTO_MIGRATE: bool = False
    AUTO_SEED: bool = False
    SEED_GRAPH_SYNC: bool = False
    UVICORN_WORKERS: int = 2

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_runtime(self):
        self.APP_ENV = self.APP_ENV.lower().strip()
        if self.APP_ENV not in {"development", "demo", "staging", "production", "test"}:
            raise ValueError("APP_ENV harus development, demo, staging, production, atau test")
        if self.APP_ENV == "production":
            if self.DEMO_MODE or self.QRIS_DEMO_MODE or self.ENABLE_DEMO_ENDPOINTS:
                raise ValueError("Production membutuhkan DEMO_MODE=false, QRIS_DEMO_MODE=false, dan ENABLE_DEMO_ENDPOINTS=false")
            if self.AUTO_SEED:
                raise ValueError("AUTO_SEED tidak boleh aktif pada production")
            if self.PUBLIC_REGISTRATION_ENABLED:
                raise ValueError("PUBLIC_REGISTRATION_ENABLED harus false pada production")
            self._require_secret("JWT_SECRET_KEY", self.JWT_SECRET_KEY)
            self._require_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
            self._require_secret("PAYER_PSEUDONYM_KEY", self.PAYER_PSEUDONYM_KEY)
            self._require_secret("ML_ARTIFACT_SIGNING_KEY", self.ML_ARTIFACT_SIGNING_KEY)
            if "*" in self.cors_origins or not self.trusted_hosts or "*" in self.trusted_hosts:
                raise ValueError("Production membutuhkan CORS dan TRUSTED_HOSTS eksplisit tanpa wildcard")
            if self.NEO4J_REQUIRED:
                self._require_secret("NEO4J_PASSWORD", self.NEO4J_PASSWORD)
        if self.demo_mode:
            if not self.PJP_SIMULATOR_SECRET:
                raise ValueError("PJP_SIMULATOR_SECRET wajib ketika Mode Demo aktif")
            if not self.PAYER_PSEUDONYM_KEY:
                raise ValueError("PAYER_PSEUDONYM_KEY wajib ketika Mode Demo aktif")
        Path(self.ML_ARTIFACT_DIR).expanduser()
        if not 0 <= self.QRIS_GNN_BLEND_WEIGHT <= 1:
            raise ValueError("QRIS_GNN_BLEND_WEIGHT harus berada di antara 0 dan 1")
        if self.QRIS_GNN_MAX_NODES < 10:
            raise ValueError("QRIS_GNN_MAX_NODES minimal 10")
        return self

    @staticmethod
    def _require_secret(name: str, value: str):
        normalized = value.strip().lower()
        if normalized in PLACEHOLDERS or normalized.startswith(("change", "replace", "example")) or len(value.strip()) < 32:
            raise ValueError(f"{name} production wajib berupa secret kuat minimal 32 karakter")

    @property
    def demo_mode(self) -> bool:
        return self.DEMO_MODE and self.QRIS_DEMO_MODE

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [host.strip() for host in self.TRUSTED_HOSTS.split(",") if host.strip()]

    @property
    def database_host(self) -> str | None:
        return urlparse(self.database_url.replace("postgresql+psycopg2", "postgresql")).hostname


settings = Settings()
