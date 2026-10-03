import os
from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    
    # LangSmith Observability & Tracing
    LANGSMITH_TRACING: bool = True
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: str = "Reel"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()

# Check if a genuine LangSmith API key has been supplied
is_valid_langsmith_key = bool(
    settings.LANGSMITH_API_KEY
    and settings.LANGSMITH_API_KEY.strip() != ""
    and settings.LANGSMITH_API_KEY != "your_langsmith_api_key_here"
    and not settings.LANGSMITH_API_KEY.startswith("your_")
)

if is_valid_langsmith_key and settings.LANGSMITH_TRACING:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
else:
    # Disable tracing until valid key is placed in .env
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
