# Smart-Transit — Week 3-4 Execution Handoff

## Project Location
```
k:\Projects\Smart-Transit
```
GitHub: `https://github.com/abhinav-atul/Smart-Transit.git`

---

## Current State (After Week 1-2 Recovery)

The project is a **real-time bus tracking system** with ML-powered ETA prediction for Amritsar city transit. It was stuck for 6 months and has just been restructured from a single-file prototype into a modular, tested architecture.

### What's Working Now
- FastAPI backend with **modular router architecture** (5 routers: health, tracking, routes, eta, stats)
- **15 pytest tests** all passing
- TimescaleDB via Docker for time-series GPS data
- Bus simulator sends GPS pings via OSRM road paths
- Leaflet.js frontend with glassmorphism UI, dark/light mode
- **ML ETA predictor** with GradientBoostingRegressor (retrained, feature-aligned)
- Connection status badge, skeleton loading, error states in UI
- Dockerfile + docker-compose for full-stack launch
- `.env`-based configuration everywhere

### Current Architecture
```
backend/app/
├── main.py              # App factory, lifespan context manager
├── config.py            # Settings from .env via python-dotenv
├── models.py            # Pydantic schemas (GPSPing, ETAResponse, etc.)
├── db/
│   ├── pool.py          # asyncpg connection pool with retry
│   └── schema.sql       # TimescaleDB schema
└── routers/
    ├── health.py        # GET /
    ├── tracking.py      # POST /location, GET /buses/live
    ├── routes.py        # GET /routes
    ├── eta.py           # GET /eta
    └── stats.py         # GET /stats

frontend/
├── index.html           # Tailwind + custom CSS, Leaflet map
└── assets/
    ├── app.js           # ~650 lines, vanilla JS, all globals
    ├── style.css        # Custom glassmorphism design system
    └── bus-icon.svg     # Self-hosted bus marker

ml_engine/
├── predictor.py         # ETAPredictor class, loads joblib model
├── train_model.py       # GradientBoostingRegressor training
└── dataset_generator.py # Synthetic data generator

simulation/
├── bus_simulator.py     # GPS ping simulator with OSRM paths
└── data/config.json     # 3 routes, 10 stops, 6 buses (Amritsar)

tests/
└── test_api.py          # 15 tests covering health, ETA, validation, degraded mode

docker-compose.yml       # TimescaleDB + API services
Dockerfile               # Python 3.11 slim backend container
.env / .env.example      # Config: DATABASE_URL, FRONTEND_ORIGIN, ML_MODEL_PATH, etc.
```

### Key Config (.env)
```
DATABASE_URL=postgresql://user:secretpass123@localhost:5433/transit_db
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_ORIGIN=http://localhost:5500
ML_MODEL_PATH=ml_engine/eta_model.pkl
LOG_LEVEL=INFO
```

### How to Run
```bash
# Start DB
docker compose up -d

# Init DB
python scripts/setup_tables.py
python scripts/init_db_data.py

# Start API
uvicorn backend.app.main:app --reload --port 8000

# Start simulator
python simulation/bus_simulator.py

# Start frontend
cd frontend && python -m http.server 5500
```

---

## Week 3-4 Tasks (Production Upgrade)

### TASK 1: WebSocket for Real-Time Bus Positions (HIGH PRIORITY)

**Problem:** Frontend polls `GET /buses/live` every 2 seconds via HTTP. This creates 1800 request/response cycles per hour per client. Wasteful and not truly real-time.

**Goal:** Replace HTTP polling with WebSocket for live position streaming.

**Implementation:**

1. **Create `backend/app/routers/websocket.py`:**
```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
import logging
from backend.app.db.pool import get_pool

logger = logging.getLogger("smart_transit.ws")
router = APIRouter()

# Track connected clients
connected_clients: set[WebSocket] = set()

@router.websocket("/ws/buses")
async def bus_positions_ws(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info("WebSocket client connected. Total: %d", len(connected_clients))
    try:
        while True:
            # Query latest bus positions
            pool = get_pool()
            if pool:
                async with pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT DISTINCT ON (vehicle_id)
                            vehicle_id, route_id, latitude, longitude, speed, time
                        FROM vehicle_logs
                        WHERE time > NOW() - INTERVAL '5 minutes'
                        ORDER BY vehicle_id, time DESC
                    """)
                    buses = [
                        {
                            "vehicle_id": r["vehicle_id"],
                            "route_id": r["route_id"],
                            "lat": float(r["latitude"]),
                            "lng": float(r["longitude"]),
                            "speed": float(r["speed"]),
                            "last_update": r["time"].isoformat(),
                        }
                        for r in rows
                    ]
                    await websocket.send_json({"type": "bus_update", "buses": buses})
            await asyncio.sleep(1)  # Push every 1 second
    except WebSocketDisconnect:
        connected_clients.discard(websocket)
        logger.info("WebSocket client disconnected. Total: %d", len(connected_clients))
```

2. **Register in `main.py`:**
```python
from backend.app.routers import health, tracking, routes, eta, stats, websocket
# ...
app.include_router(websocket.router)
```

3. **Update `frontend/assets/app.js`:**
   - Add WebSocket connection logic with auto-reconnect
   - Keep HTTP polling as fallback if WebSocket fails
   - On `bus_update` message, call `updateBusMarker()` for each bus
   - Remove `setInterval(fetchLiveBusData, POLL_INTERVAL_MS)` when WS is connected

```javascript
// Add after initMap()
let ws = null;
let wsReconnectTimer = null;

function connectWebSocket() {
    ws = new WebSocket(`ws://localhost:8000/ws/buses`);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        updateConnectionBadge(true);
        // Stop HTTP polling when WS is active
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'bus_update') {
            handleLiveBusUpdate(data.buses);
        }
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected, falling back to polling');
        updateConnectionBadge(false);
        // Restart HTTP polling as fallback
        if (!pollTimer) pollTimer = setInterval(fetchLiveBusData, POLL_INTERVAL_MS);
        // Auto-reconnect after 3 seconds
        wsReconnectTimer = setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = () => ws.close();
}

// Extract the bus processing logic from fetchLiveBusData into a shared function
function handleLiveBusUpdate(liveBuses) {
    const activeBusIds = new Set();
    const formattedBuses = [];
    liveBuses.forEach(bus => {
        const busData = { id: bus.vehicle_id, routeId: bus.route_id, lat: bus.lat, lng: bus.lng, speed: bus.speed };
        liveBusDataCache[busData.id] = busData;
        updateBusMarker(busData);
        activeBusIds.add(busData.id);
        formattedBuses.push(busData);
    });
    for (const busId in busMarkers) {
        if (!activeBusIds.has(busId)) {
            map.removeLayer(busMarkers[busId]);
            delete busMarkers[busId];
            delete liveBusDataCache[busId];
        }
    }
    updateAuthorityList(formattedBuses);
    updateConnectionBadge(true);
}
```

   - Call `connectWebSocket()` in `main()` after `fetchAndProcessStaticData()`

---

### TASK 2: JWT Authentication (HIGH PRIORITY)

**Problem:** Any person on the network can POST fake GPS data to `/location`, corrupting the system. Zero access control.

**Goal:** Add JWT auth for fleet management endpoints and API key auth for the simulator.

**Implementation:**

1. **Install:** Add `python-jose[cryptography]` and `passlib[bcrypt]` to `requirements.txt`

2. **Create `backend/app/auth.py`:**
```python
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from backend.app.config import settings

security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=24)):
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != settings.SIMULATOR_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
```

3. **Add to `config.py`:**
```python
JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
SIMULATOR_API_KEY: str = os.getenv("SIMULATOR_API_KEY", "sim-key-change-me")
```

4. **Add to `.env` and `.env.example`:**
```
JWT_SECRET=your-secret-key-here
SIMULATOR_API_KEY=your-simulator-api-key-here
```

5. **Protect endpoints:**
   - `POST /location` → requires API key (`Depends(verify_api_key)`)
   - `GET /stats` → requires JWT token (`Depends(verify_token)`)
   - `GET /`, `/routes`, `/buses/live`, `/eta` → public (commuter endpoints)

6. **Add `POST /auth/token` endpoint** in a new `backend/app/routers/auth.py` for getting tokens (can be simple hardcoded admin user for now)

7. **Update `simulation/bus_simulator.py`** to send `X-API-Key` header with each POST request:
```python
headers = {"X-API-Key": os.getenv("SIMULATOR_API_KEY", "sim-key-change-me")}
requests.post(API_URL, json=payload, headers=headers, timeout=0.5)
```

---

### TASK 3: CI/CD Pipeline (MEDIUM PRIORITY)

**Goal:** GitHub Actions workflow for automated testing on every push.

**Create `.github/workflows/ci.yml`:**
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest tests/ -v --tb=short

      - name: Lint check
        run: |
          pip install ruff
          ruff check backend/ ml_engine/ simulation/ scripts/ tests/
```

---

### TASK 4: Rate Limiting (MEDIUM PRIORITY)

**Problem:** `/location` endpoint accepts unlimited POST requests. A malfunctioning simulator could flood the DB.

**Implementation:**

1. **Install:** Add `slowapi` to `requirements.txt`

2. **Add to `main.py`:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

3. **Apply to `tracking.py`:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

# On the endpoint:
@router.post("/location")
@limiter.limit("60/minute")  # Max 60 pings per minute per IP
async def receive_location_ping(request: Request, ping: GPSPing):
    ...
```

---

### TASK 5: Query Performance Optimization (MEDIUM PRIORITY)

**Problem:** The `DISTINCT ON` query for live buses scans all recent logs. As data grows, this slows down.

**Implementation:**

1. **Create a `vehicle_latest_positions` table** that gets upserted on each GPS ping:

Add to `schema.sql`:
```sql
CREATE TABLE IF NOT EXISTS vehicle_latest_positions (
    vehicle_id VARCHAR(50) PRIMARY KEY,
    route_id VARCHAR(50),
    latitude FLOAT,
    longitude FLOAT,
    speed FLOAT,
    last_update TIMESTAMPTZ NOT NULL
);
```

2. **Update `tracking.py` POST `/location`** to also upsert into this table:
```sql
INSERT INTO vehicle_latest_positions (vehicle_id, route_id, latitude, longitude, speed, last_update)
VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT (vehicle_id) DO UPDATE SET
    route_id = EXCLUDED.route_id,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    speed = EXCLUDED.speed,
    last_update = EXCLUDED.last_update
```

3. **Update `GET /buses/live`** to query from `vehicle_latest_positions` instead:
```sql
SELECT vehicle_id, route_id, latitude, longitude, speed, last_update
FROM vehicle_latest_positions
WHERE last_update > NOW() - INTERVAL '5 minutes'
ORDER BY vehicle_id
```

This changes the query from `O(n log n)` on potentially millions of rows to `O(k)` where `k` = number of active buses.

---

### TASK 6: Cloud Deployment (LOW PRIORITY)

**Goal:** Deploy to Railway or Render for public demo URL.

**For Railway:**
1. Create `Procfile`:
```
web: uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

2. Create `railway.toml`:
```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT"
```

3. Set environment variables in Railway dashboard (DATABASE_URL from Railway's managed Postgres, JWT_SECRET, etc.)

4. The frontend can be deployed to Vercel/Netlify as a static site, or served via FastAPI's `StaticFiles`.

**For serving frontend from FastAPI** (simpler single-deploy):
Add to `main.py`:
```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
```

---

### TASK 7: Monitoring & Error Tracking (LOW PRIORITY)

1. **Add Sentry integration:**
```bash
pip install sentry-sdk[fastapi]
```

```python
# In main.py
import sentry_sdk
sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)
```

2. **Add basic Prometheus metrics:**
   - Request count per endpoint
   - Response latency histogram
   - Active WebSocket connections gauge
   - Active buses gauge

---

## File-by-File Summary of Current Code

### `backend/app/main.py` (80 lines)
- Uses `@asynccontextmanager` lifespan pattern
- Creates DB pool, loads ML model at startup
- Registers 5 routers, CORS middleware locked to `FRONTEND_ORIGIN`
- Structured logging via Python `logging` module

### `backend/app/config.py` (50 lines)
- `Settings` class loading from `.env` via `python-dotenv`
- Properties: `DATABASE_URL`, `API_HOST`, `API_PORT`, `FRONTEND_ORIGIN`, `ML_MODEL_PATH`, `LOG_LEVEL`, `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`

### `backend/app/models.py` (45 lines)
- `GPSPing`: lat bounded [-90,90], lng [-180,180], speed >= 0, min_length=1 on IDs
- `HealthResponse`, `BusPosition`, `ETAResponse`, `FleetStats`: typed response models

### `backend/app/db/pool.py` (50 lines)
- `create_pool()`: 10 retries, 2s delay, configurable min/max pool size
- `close_pool()`: graceful shutdown
- `get_pool()`: returns current pool or None

### `backend/app/routers/tracking.py` (70 lines)
- `POST /location`: inserts GPS ping into `vehicle_logs`, requires DB
- `GET /buses/live`: `DISTINCT ON` query with 5-minute window filter

### `backend/app/routers/eta.py` (56 lines)
- `GET /eta`: `distance_meters` (gt=0), `current_speed_kmh` (ge=0)
- Converts km/h to m/s, calls `ETAPredictor.predict()`
- Returns source: "ML_model" or "rule_based_fallback"

### `ml_engine/predictor.py` (65 lines)
- `ETAPredictor` class with `FEATURE_COLUMNS = ["distance_meters", "speed", "hour"]`
- `predict()`: returns ETA in minutes, clamps to non-negative
- Fallback: physics-based `distance / speed / 60`

### `frontend/assets/app.js` (~650 lines)
- All globals, no modules/framework
- `initMap()` → `main()` → `fetchAndProcessStaticData()` + polling
- `fetchLiveBusData()` polls every 2s, updates markers with smooth animation
- `switchView()` toggles Finder/Routes/Fleet views
- `updateConnectionBadge()` manages online/offline indicator
- `showRouteSkeletons()` / `showFinderSkeletons()` for loading states

### `simulation/bus_simulator.py` (120 lines)
- Loads `config.json`, fetches OSRM road paths, simulates 6 buses
- Variable speed (0-80 km/h with random acceleration/deceleration)
- Posts GPS pings to `/location` every 1 second

### `tests/test_api.py` (120 lines)
- 15 tests: health, ETA validation (negative/zero/missing), GPS validation (invalid coords, empty IDs), degraded-mode 503s, OpenAPI schema

---

## Priority Order for Execution

1. **WebSocket** (Task 1) — biggest user-visible improvement
2. **JWT Auth** (Task 2) — biggest security improvement  
3. **Query Optimization** (Task 5) — necessary before real deployment
4. **Rate Limiting** (Task 4) — quick win
5. **CI/CD** (Task 3) — quick win
6. **Cloud Deploy** (Task 6) — makes it demo-ready
7. **Monitoring** (Task 7) — nice to have

---

## Important Notes

- Python version: **3.10** (installed on user's machine)
- The user is on **Windows** (PowerShell)
- DB runs on Docker at **port 5433** (not default 5432)
- Frontend uses **Tailwind CDN** (not installed, loaded via `<script>` tag)
- The ML model's near-perfect R² is because the training data is synthetic — the model just learns to reverse the generator's formula. This is expected and documented.
- The `train_model.py` outputs `eta_model.pkl` to the **project root**, needs to be copied to `ml_engine/eta_model.pkl`
- All `print()` statements in the backend have been replaced with `logging` — maintain this pattern
- CORS is locked to `FRONTEND_ORIGIN` from `.env` — when adding WebSocket, ensure CORS still works
