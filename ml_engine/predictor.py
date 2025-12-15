import joblib
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

# --- ML Model Preparation (Dummy for Demonstration) ---
# This function creates and saves a simple linear regression model
# that can be loaded by the ETAPredictor class.
def create_dummy_model(model_path='eta_model.pkl'):
    """
    Creates and saves a simple dummy Linear Regression model.
    In a real application, this would be your trained, robust model.
    """
    # Create synthetic data: ETA (in minutes) = Distance / Speed + Hour_Effect
    data_size = 100
    np.random.seed(42)
    distances = np.random.randint(500, 10000, data_size)  # 0.5km to 10km
    speeds = np.random.randint(10, 80, data_size)          # 10 to 80 km/h
    hours = np.random.randint(0, 24, data_size)            # 0 to 23 (Hour of Day)

    # Simplified ETA calculation with some noise and hour penalty (traffic)
    eta_base = (distances / (speeds * 1000 / 3600)) / 60  # Distance/Speed in minutes
    eta = eta_base + (hours / 10) + np.random.rand(data_size) * 5
    
    # Features and Target
    X = pd.DataFrame({'dist': distances, 'speed': speeds, 'hour': hours})
    y = eta

    # Train a simple model
    model = LinearRegression()
    model.fit(X, y)

    # Save the model
    joblib.dump(model, model_path)
    print(f"Dummy model saved to {model_path}. ML prediction is now enabled.")


# --- ETAPredictor Class (Your Original Code, Completed) ---

class ETAPredictor:
    """
    Predicts Estimated Time of Arrival (ETA) using a trained ML model.
    Falls back to a rule-based calculation if the model is not found.
    """
    def __init__(self, model_path='eta_model.pkl'):
        try:
            self.model = joblib.load(model_path)
            self.ready = True
            print(f"Successfully loaded ML model from {model_path}.")
        except:
            print("No model found at specified path. Using fallback rule-based logic.")
            self.ready = False

    def predict(self, distance_meters, current_speed, hour_of_day):
        """
        Predicts ETA in minutes.

        Args:
            distance_meters (float): Remaining distance to travel (in meters).
            current_speed (float): Current vehicle speed (in meters per second, m/s).
            hour_of_day (int): The current hour (0-23) for traffic impact.
        
        Returns:
            float: The estimated time of arrival in minutes.
        """
        
        # Ensure speed is not zero or extremely low to avoid division by zero
        # The fallback rule needs speed in m/s, so we use current_speed directly.
        SAFE_SPEED_M_S = max(current_speed, 0.1) 

        if not self.ready:
            # Fallback: Time (s) = Distance (m) / Speed (m/s). Convert to minutes.
            # max(current_speed, 10) ensures minimum speed of 10 m/s for prediction (approx 36 km/h)
            eta_seconds = distance_meters / SAFE_SPEED_M_S
            eta_minutes = eta_seconds / 60
            print(f" (FALLBACK) ETA = {eta_minutes:.2f} minutes")
            return eta_minutes
        
        # ML Prediction
        # Ensure feature names match the training data used to create the model
        features = pd.DataFrame([[distance_meters, current_speed, hour_of_day]], 
                                columns=['dist', 'speed', 'hour'])
        
        # Make the prediction
        predicted_eta_minutes = self.model.predict(features)[0]
        
        print(f" (ML) ETA = {predicted_eta_minutes:.2f} minutes")
        return predicted_eta_minutes

# --- Driver Code for Demonstration ---

if __name__ == "__main__":
    MODEL_FILE = 'eta_model_demo.pkl'
    
    # 1. Test the Fallback Logic (Model does not exist yet)
    print("--- 1. Testing FALLBACK Mode ---")
    eta_predictor_fallback = ETAPredictor(model_path=MODEL_FILE)
    
    # Inputs: 5000 meters remaining, 15 m/s speed, 10 AM
    fallback_prediction = eta_predictor_fallback.predict(
        distance_meters=5000, 
        current_speed=15, 
        hour_of_day=10
    )
    print(f"Fallback Prediction: {fallback_prediction:.2f} minutes\n") # Expected: 5000 / 15 / 60 = 5.56 min


    # 2. Create the Dummy Model
    create_dummy_model(model_path=MODEL_FILE)
    print("-" * 35)

    # 3. Test the ML Prediction Logic (Model now exists)
    print("--- 2. Testing ML Mode ---")
    eta_predictor_ml = ETAPredictor(model_path=MODEL_FILE)

    # Inputs: Same as above (5000 meters remaining, 15 m/s speed, 10 AM)
    ml_prediction = eta_predictor_ml.predict(
        distance_meters=5000, 
        current_speed=15, 
        hour_of_day=10
    )
    print(f"ML Prediction: {ml_prediction:.2f} minutes\n")

    # Example 2: High Traffic (Rush Hour at 18:00)
    print("--- 3. Testing ML (Rush Hour Effect) ---")
    rush_hour_prediction = eta_predictor_ml.predict(
        distance_meters=5000, 
        current_speed=15, 
        hour_of_day=18 # High hour_of_day should increase ETA
    )
    print(f"Rush Hour Prediction: {rush_hour_prediction:.2f} minutes")