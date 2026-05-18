"""
ETA Predictor — ML model wrapper with rule-based fallback.

Predicts Estimated Time of Arrival using a trained sklearn model.
Falls back to physics-based calculation (distance / speed) when no model is available.
"""

import logging
import joblib
import pandas as pd

logger = logging.getLogger("smart_transit.ml")


class ETAPredictor:
    """
    Predicts ETA in minutes using a trained ML model.
    Falls back to a rule-based calculation if the model is not found.
    """

    # Feature columns must match what train_model.py uses during training
    FEATURE_COLUMNS = ["distance_meters", "speed", "hour"]

    def __init__(self, model_path: str = "eta_model.pkl"):
        try:
            self.model = joblib.load(model_path)
            self.ready = True
            logger.info("ML model loaded from %s", model_path)
        except Exception:
            logger.warning("No model found at '%s'. Using rule-based fallback.", model_path)
            self.model = None
            self.ready = False

    def predict(self, distance_meters: float, current_speed: float, hour_of_day: int) -> float:
        """
        Predict ETA in minutes.

        Args:
            distance_meters: Remaining distance to travel (meters).
            current_speed: Current vehicle speed (meters per second).
            hour_of_day: Current hour (0-23) for traffic impact.

        Returns:
            Estimated time of arrival in minutes.
        """
        # Ensure speed is not zero to avoid division-by-zero in fallback
        safe_speed = max(current_speed, 0.1)

        if not self.ready:
            # Fallback: Time(s) = Distance(m) / Speed(m/s), convert to minutes
            eta_minutes = (distance_meters / safe_speed) / 60.0
            logger.debug("Fallback ETA: %.2f min (dist=%.0fm, speed=%.1fm/s)", eta_minutes, distance_meters, safe_speed)
            return eta_minutes

        # ML Prediction — feature names MUST match train_model.py columns
        features = pd.DataFrame(
            [[distance_meters, current_speed, hour_of_day]],
            columns=self.FEATURE_COLUMNS,
        )

        predicted = self.model.predict(features)[0]

        # Clamp to non-negative (model could predict negative with bad input)
        predicted = max(predicted, 0.0)

        logger.debug("ML ETA: %.2f min (dist=%.0fm, speed=%.1fm/s, hour=%d)", predicted, distance_meters, current_speed, hour_of_day)
        return predicted