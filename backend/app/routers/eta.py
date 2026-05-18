"""
ML-powered ETA prediction endpoint.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from backend.app.models import ETAResponse

logger = logging.getLogger("smart_transit.eta")
router = APIRouter(tags=["ML Prediction"])


@router.get("/eta", response_model=ETAResponse)
async def get_eta_prediction(
    distance_meters: float = Query(
        ..., gt=0, description="Distance remaining to destination stop in meters"
    ),
    current_speed_kmh: float = Query(
        ..., ge=0, description="Vehicle speed in km/h"
    ),
):
    """
    Predicts ETA using the loaded ML model or a rule-based fallback.
    """
    from backend.app.main import app

    predictor = getattr(app.state, "eta_predictor", None)
    if predictor is None:
        raise HTTPException(status_code=503, detail="ETA predictor not initialized.")

    try:
        # Convert speed from km/h to m/s for the predictor
        current_speed_m_s = current_speed_kmh / 3.6
        hour_of_day = datetime.now().hour

        prediction_minutes = predictor.predict(
            distance_meters=distance_meters,
            current_speed=current_speed_m_s,
            hour_of_day=hour_of_day,
        )

        source = "ML_model" if predictor.ready else "rule_based_fallback"

        return ETAResponse(
            prediction=f"{prediction_minutes:.2f} mins",
            seconds=prediction_minutes * 60,
            source=source,
        )

    except Exception as e:
        logger.error("ML prediction error: %s", e)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")
