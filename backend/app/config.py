"""
Centralized application configuration.
Loads settings from environment variables with sensible defaults.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Resolve project root (two levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Load .env from project root
load_dotenv(PROJECT_ROOT / ".env")

# Ensure project root is on sys.path for ml_engine imports
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class Settings:
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://user:secretpass123@localhost:5433/transit_db"
    )

    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5500")

    # ML Model
    ML_MODEL_PATH: str = str(
        PROJECT_ROOT / os.getenv("ML_MODEL_PATH", "ml_engine/eta_model.pkl")
    )

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Database Pool
    DB_POOL_MIN_SIZE: int = int(os.getenv("DB_POOL_MIN_SIZE", "2"))
    DB_POOL_MAX_SIZE: int = int(os.getenv("DB_POOL_MAX_SIZE", "10"))

    # Simulator
    BUS_POLL_STALE_SECONDS: int = 120  # Buses older than 2 min are "inactive"


settings = Settings()
