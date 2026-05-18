"""
Smart-Transit API Gateway — Main application entry point.

Entrypoint: uvicorn backend.app.main:app --reload --port 8000
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.db.pool import create_pool, close_pool
from ml_engine.predictor import ETAPredictor

from backend.app.routers import health, tracking, routes, eta, stats

# --- Logging Setup ---
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("smart_transit")


# --- Lifespan (replaces deprecated on_event) ---
@asynccontextmanager
async def lifespan(application: FastAPI):
    """Manage startup and shutdown resources."""

    # --- Startup ---
    logger.info("Starting Smart-Transit API Gateway v2.1.0")

    # 1. Database connection pool
    await create_pool()

    # 2. ML Model
    if os.path.exists(settings.ML_MODEL_PATH):
        application.state.eta_predictor = ETAPredictor(model_path=settings.ML_MODEL_PATH)
        if application.state.eta_predictor.ready:
            logger.info("ML model loaded successfully from %s", settings.ML_MODEL_PATH)
        else:
            logger.warning("ML model file exists but failed to load — using rule-based fallback.")
    else:
        application.state.eta_predictor = ETAPredictor(model_path="NON_EXISTENT")
        logger.warning("ML model not found at %s — using rule-based fallback.", settings.ML_MODEL_PATH)

    yield  # Application runs here

    # --- Shutdown ---
    await close_pool()
    logger.info("Smart-Transit API Gateway shut down.")


# --- App Factory ---
app = FastAPI(
    title="Smart-Transit API Gateway",
    description="Real-time intelligent transit navigation with ML-powered ETA prediction.",
    version="2.1.0",
    lifespan=lifespan,
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(health.router)
app.include_router(tracking.router)
app.include_router(routes.router)
app.include_router(eta.router)
app.include_router(stats.router)
