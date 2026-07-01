"""
Smart-Transit API Gateway — Main application entry point.

Entrypoint: uvicorn backend.app.main:app --reload --port 8000
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.app.config import settings
from backend.app.db.pool import create_pool, close_pool
from backend.app.rate_limit import limiter
from ml_engine.predictor import ETAPredictor

from backend.app.routers import auth, eta, health, routes, stats, tracking, websocket

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
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(tracking.router)
app.include_router(routes.router)
app.include_router(eta.router)
app.include_router(stats.router)
app.include_router(websocket.router)
from backend.app.routers import analytics
app.include_router(analytics.router)
from backend.app.routers import admin
app.include_router(admin.router)

# --- Prometheus Metrics ---
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    logger.info("Prometheus metrics exposed at /metrics")
except ImportError:
    logger.warning("prometheus-fastapi-instrumentator not installed — metrics disabled.")

# --- Static Files ---
# Serve frontend static files — must be LAST (catch-all route)
from fastapi.staticfiles import StaticFiles
from pathlib import Path

frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
