-- Enable TimescaleDB extension for time-series data (graceful if not available)
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS timescaledb;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'TimescaleDB extension not available, skipping hypertable creation.';
END $$;

-- 1. Routes Table (Static Data)
CREATE TABLE IF NOT EXISTS routes (
    route_id VARCHAR(50) PRIMARY KEY, -- e.g., 'RT-101'
    route_name VARCHAR(100),
    polylines TEXT -- JSON string or encoded polyline
);

-- 2. Stops Table (Static Data)
CREATE TABLE IF NOT EXISTS stops (
    stop_id SERIAL PRIMARY KEY,
    route_id VARCHAR(50) REFERENCES routes(route_id) ON DELETE CASCADE,
    stop_name VARCHAR(100),
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    stop_sequence INT -- Order of stops (0, 1, 2...)
);

-- Create unique constraint to prevent duplicate stops
CREATE UNIQUE INDEX IF NOT EXISTS idx_stops_unique 
ON stops (route_id, stop_name, stop_sequence);

-- 3. Vehicle Logs (High Volume / Time-Series)
CREATE TABLE IF NOT EXISTS vehicle_logs (
    time TIMESTAMPTZ NOT NULL,
    vehicle_id VARCHAR(50),
    route_id VARCHAR(50),
    latitude FLOAT,
    longitude FLOAT,
    speed FLOAT, -- For ETA calculation
    passenger_count INT DEFAULT 0
);

-- Index for fast latest-position queries
CREATE INDEX IF NOT EXISTS idx_vehicle_logs_vehicle_time
ON vehicle_logs (vehicle_id, time DESC);

-- Convert to Hypertable for efficiency (TimescaleDB feature, graceful)
DO $$
BEGIN
    PERFORM create_hypertable('vehicle_logs', 'time', if_not_exists => TRUE);
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Could not create hypertable (TimescaleDB may not be available). Using regular table.';
END $$;