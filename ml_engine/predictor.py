import joblib
import pandas as pd

class ETAPredictor:
    def __init__(self, model_path='eta_model.pkl'):
        try:
            self.model = joblib.load(model_path)
            self.ready = True
        except:
            print("No model found. Using fallback rule-based logic.")
            self.ready = False

    def predict(self, distance_meters, current_speed, hour_of_day):
        if not self.ready:
            # Fallback: Time = Distance / Speed
            return (distance_meters / max(current_speed, 10)) / 60 
        
        # ML Prediction
        features = pd.DataFrame([[distance_meters, current_speed, hour_of_day]], 
                                columns=['dist', 'speed', 'hour'])
        return self.model.predict(features)[0]