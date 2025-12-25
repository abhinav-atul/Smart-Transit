import pandas as pd
import joblib
import os
import numpy as np # Needed for handling inf values in speed calculation
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# --- Configuration ---
# FIX 1: Corrected file name to match the output of your generator script.
DATA_FILE = 'transit_data.csv' 
MODEL_OUTPUT_FILE = 'eta_model.pkl'

def train_and_evaluate_model():
    """
    Loads data, prepares features, trains the ETA prediction model, 
    evaluates its efficiency, and saves the serialized model file.
    """
    print("🚀 Starting model training and evaluation...")
    
    # Check for the data file
    if not os.path.exists(DATA_FILE):
        print(f"\n❌ Error: Training data file '{DATA_FILE}' not found.")
        print("Please ensure the file is in the root directory or adjust the DATA_FILE path.")
        return

    # 1. Load Data
    try:
        data = pd.read_csv(DATA_FILE) 
    except Exception as e:
        print(f"\n❌ Error loading data: {e}")
        return

    # 2. Prepare and Rename Columns for ML Model
    
    # FIX 2: Rename Target Column (Fixes KeyError: 'time_taken_minutes')
    TARGET_COLUMN_OLD = 'travel_time_min'
    TARGET_COLUMN_NEW = 'time_taken_minutes'
    data.rename(columns={TARGET_COLUMN_OLD: TARGET_COLUMN_NEW}, inplace=True)

    # Prepare ML Model Features: 'distance_meters', 'speed', 'hour'

    # Convert Distance (km -> meters)
    data['distance_meters'] = data['distance_km'] * 1000

    # Calculate 'speed' (km/h) from distance and time
    # Formula: Speed (km/h) = Distance (km) / Time (h)
    # Time (h) = Time (min) / 60
    data['speed'] = data['distance_km'] / (data[TARGET_COLUMN_NEW] / 60.0)
    
    # Handle division by zero (where travel_time_min is very close to zero)
    data['speed'].replace([np.inf, -np.inf], 0, inplace=True) 
    
    # Rename Hour Column
    data.rename(columns={'hour_of_day': 'hour'}, inplace=True)

    # 3. Define Features (X) and Target (y)
    FEATURE_COLUMNS = ['distance_meters', 'speed', 'hour']
    
    # Filter out records where target time is zero or negative (due to noise in generator)
    data = data[data[TARGET_COLUMN_NEW] > 0] 

    X = data[FEATURE_COLUMNS]
    y = data[TARGET_COLUMN_NEW]
    
    # 4. Split the data into training and testing sets (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print(f"Data Split: Training set ({len(X_train)} samples), Test set ({len(X_test)} samples)")
    
    # 5. Train the Model
    model = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42)
    model.fit(X_train, y_train)

    # 6. Evaluate the Model on the unseen Test Set (Efficiency Check)
    y_pred = model.predict(X_test)

    # Calculate key efficiency metrics
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print("-" * 35)
    print("✅ Training Complete.")
    print("🎯 Model Efficiency Metrics (on 20% Test Data):")
    print(f"   - Mean Absolute Error (MAE): {mae:.3f} minutes")
    print(f"     (Interpretation: Predictions are off by an average of {mae:.3f} minutes.)")
    print(f"   - R-squared (R2): {r2:.3f}")
    print(f"     (Interpretation: {r2*100:.1f}% of the variance in ETA is explained.)")
    print("-" * 35)

    # 7. Save the model for deployment
    joblib.dump(model, MODEL_OUTPUT_FILE) 
    print(f"✅ Model saved to {MODEL_OUTPUT_FILE}")


if __name__ == "__main__":
    train_and_evaluate_model()