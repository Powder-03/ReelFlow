from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    GOOGLE_CLOUD_PROJECT: str = "project-1b52589d-0827-46ab-9be"
    GOOGLE_CLOUD_LOCATION: str = "us-central1"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # App Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    MEMORY_DIR: Path = BASE_DIR / "data" / "memory"
    
    # Evaluation & Guardrail Thresholds
    PASS_THRESHOLD: float = 0.85      # 8.5/10
    MAX_REWRITES: int = 3
    MAX_GUARDRAIL_RETRIES: int = 2
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()
