import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
import joblib

# Load your synthetic csv
data = pd.read_csv('training_data.csv') 

# Features: Distance to stop, Current Speed. Target: Time taken.
X = data[['distance_meters', 'speed']]
y = data[['time_taken_minutes']]

model = GradientBoostingRegressor()
model.fit(X, y)

joblib.dump(model, 'eta_model.pkl')
print("Model saved!")