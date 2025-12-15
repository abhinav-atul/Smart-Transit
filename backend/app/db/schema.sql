-- Enable TimescaleDB extension for time-series data
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 1. Routes Table (Static Data)
CREATE TABLE routes (
    route_id VARCHAR(50) PRIMARY KEY, -- e.g., 'AS-1'
    route_name VARCHAR(100),
    polylines TEXT -- JSON string or encoded polyline
);

-- 2. Stops Table (Static Data)
CREATE TABLE stops (
    stop_id SERIAL PRIMARY KEY,
    route_id VARCHAR(50) REFERENCES routes(route_id),
    stop_name VARCHAR(100),
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    stop_sequence INT -- Order of stops (0, 1, 2...)
);

-- 3. Vehicle Logs (High Volume / Time-Series)
-- This replaces the Firestore 'buses' collection updates
CREATE TABLE vehicle_logs (
    time TIMESTAMPTZ NOT NULL,
    vehicle_id VARCHAR(50),
    route_id VARCHAR(50),
    latitude FLOAT,
    longitude FLOAT,
    speed FLOAT, -- New field for ETA calculation
    passenger_count INT DEFAULT 0 -- For low bandwidth analytics
);

-- Convert to Hypertable for efficiency (TimescaleDB feature)
SELECT create_hypertable('vehicle_logs', 'time');