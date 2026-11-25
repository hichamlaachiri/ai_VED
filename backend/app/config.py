import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroDrama AI Studio"
    ENV: str = "development"
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR / 'microdrama.db'}"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Configurable Gemini Models
    DIRECTOR_MODEL: str = os.getenv("DIRECTOR_MODEL", "gemini-2.5-flash")
    NANO_BANANA_MODEL: str = os.getenv("NANO_BANANA_MODEL", "gemini-2.5-flash-image")
    IMAGEN_FALLBACK_MODEL: str = os.getenv("IMAGEN_FALLBACK_MODEL", "imagen-3.0-generate-002")
    OMNI_VIDEO_MODEL: str = os.getenv("OMNI_VIDEO_MODEL", "gemini-omni-1.2-flash")

    # Storage
    STORAGE_PATH: Path = STORAGE_DIR

    # Video Generation Mode (set true for local dev/testing without spending video API credits)
    MOCK_VIDEO_MODE: bool = os.getenv("MOCK_VIDEO_MODE", "false").lower() in ("true", "1")

    # Cost & Pricing (in USD and credits: 1 credit = $0.01)
    PASS1_COST_USD: float = 0.35   # 360p 15s clip
    PASS2_COST_USD: float = 1.04   # 720p 15s clip
    PASS1_CREDITS: int = 35        # 35 credits
    PASS2_CREDITS: int = 104       # 104 credits
    IMAGE_GEN_CREDITS: int = 5     # 5 credits per reference image

    # Defaults
    INITIAL_USER_CREDITS: int = 1000  # $10 worth of starter credits

    class Config:
        env_file = str(BASE_DIR / ".env")
        extra = "ignore"


settings = Settings()
