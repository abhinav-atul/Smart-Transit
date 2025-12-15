import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def generate_smart_transit_data(num_records=20000, output_file='transit_data.csv'):
    """
    Generates a synthetic dataset for a Smart Transit ETA prediction model.

    The model predicts 'travel_time_min' based on route, time, and traffic conditions.
    """
    print(f"Generating {num_records} transit records...")

    # --- 1. Define Static Variables ---
    
    # Define a few synthetic routes and distances (in kilometers)
    routes = {
        'R-A1': {'avg_speed_kph': 30, 'base_travel_time_min': 5, 'distance_km': 2.5},
        'R-B2': {'avg_speed_kph': 20, 'base_travel_time_min': 8, 'distance_km': 3.0},
        'R-C3': {'avg_speed_kph': 45, 'base_travel_time_min': 3, 'distance_km': 2.2},
    }
    route_ids = list(routes.keys())
    
    # Define potential stop pairs for each route (for realism)
    stop_pairs = {
        'R-A1': [('S-A1', 'S-A2'), ('S-A2', 'S-A3'), ('S-A3', 'S-A4')],
        'R-B2': [('S-B1', 'S-B2'), ('S-B2', 'S-B3')],
        'R-C3': [('S-C1', 'S-C2'), ('S-C2', 'S-C3'), ('S-C3', 'S-C4'), ('S-C4', 'S-C5')],
    }

    # Time period for the simulation (e.g., 6 months)
    start_date = datetime(2025, 1, 1)
    
    # --- 2. Generate Features ---
    
    data = {
        'route_id': np.random.choice(route_ids, num_records),
        'stop_start': np.empty(num_records, dtype=object),
        'stop_end': np.empty(num_records, dtype=object),
        'timestamp': [start_date + timedelta(minutes=np.random.randint(0, 60 * 24 * 180)) 
                      for _ in range(num_records)],
    }
    
    # Assign specific stop pairs based on the chosen route
    for route_id in route_ids:
        indices = np.where(data['route_id'] == route_id)[0]
        if len(indices) > 0:
            pair_choices = np.random.choice(len(stop_pairs[route_id]), len(indices))
            for i, idx in enumerate(indices):
                start, end = stop_pairs[route_id][pair_choices[i]]
                data['stop_start'][idx] = start
                data['stop_end'][idx] = end
    
    df = pd.DataFrame(data)

    # Extract Time/Date Features
    df['day_of_week'] = df['timestamp'].dt.dayofweek    # 0=Monday, 6=Sunday
    df['hour_of_day'] = df['timestamp'].dt.hour         # 0-23
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    
    # Assign Traffic/Weather Conditions
    df['weather'] = np.random.choice(['Clear', 'Rainy', 'Snowy'], num_records, p=[0.7, 0.2, 0.1])
    
    # --- 3. Calculate Target (Travel Time) ---

    df['distance_km'] = df['route_id'].apply(lambda r: routes[r]['distance_km'] / len(stop_pairs[r]))
    
    # 3.1. Calculate Base Time (Time = Distance / Avg_Speed)
    def calculate_base_time(row):
        route_config = routes[row['route_id']]
        # Time in hours = Distance (km) / Speed (km/h)
        time_h = row['distance_km'] / route_config['avg_speed_kph']
        return time_h * 60 # Convert to minutes

    df['base_time_min'] = df.apply(calculate_base_time, axis=1)

    # 3.2. Apply Traffic/Time-of-Day Multipliers
    
    # Rush Hour Multiplier (7-9 AM and 4-6 PM)
    df['traffic_mult'] = 1.0
    df.loc[df['hour_of_day'].isin([7, 8, 16, 17]), 'traffic_mult'] = 1.4 
    
    # Weekend Multiplier (Slightly lower traffic)
    df.loc[df['is_weekend'] == 1, 'traffic_mult'] = 0.95 

    # Weather Multiplier
    df.loc[df['weather'] == 'Rainy', 'traffic_mult'] *= 1.15
    df.loc[df['weather'] == 'Snowy', 'traffic_mult'] *= 1.30
    
    # Final Travel Time (Target Variable)
    df['travel_time_min'] = df['base_time_min'] * df['traffic_mult']
    
    # Add Random Noise (to simulate unexpected events)
    noise = np.random.normal(loc=0, scale=0.5, size=num_records)
    df['travel_time_min'] += noise
    
    # Remove intermediate columns before saving
    df.drop(columns=['traffic_mult', 'base_time_min'], inplace=True)
    
    # --- 4. Save and Summarize ---
    df.to_csv(output_file, index=False)
    print(f"\n✅ Data generation complete. Saved to: {os.path.abspath(output_file)}")
    print("\nFirst 5 rows:")
    print(df.head())
    print(f"\nTarget Variable Summary ('travel_time_min'):\n{df['travel_time_min'].describe()}")
    
if __name__ == "__main__":
    generate_smart_transit_data(num_records=50000)