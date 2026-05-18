# Smart-Transit — Week 5-6 Implementation Plan

## Current State Summary (Post Week 1-4)

| Metric | Value |
|---|---|
| Source files | 31 |
| Codebase size | 101 KB |
| Tests | 20/20 passing (1.35s) |
| Architecture | Modular FastAPI with 8 routers |
| Security | JWT auth + API keys + rate limiting + CORS locked |
| Database | TimescaleDB + `vehicle_latest_positions` optimization table |
| Real-time | WebSocket endpoint `/ws/buses` (backend ready) |
| CI/CD | GitHub Actions (pytest + ruff) |
| ML | GradientBoosting ETA predictor (feature-aligned, retrained) |

### One Carried-Over Gap
The frontend `app.js` still uses HTTP polling — the WebSocket client was never wired up. Task 1 below fixes this.

---

## Week 5-6 Tasks

### TASK 1: Frontend WebSocket Client (CRITICAL — Gap Fix)

**Problem:** Backend has `/ws/buses` endpoint ready but frontend still uses `setInterval(fetchLiveBusData, 2000)` HTTP polling.

**File:** `frontend/assets/app.js`

**Implementation — Add after the `updateConnectionBadge` function (~line 88):**

```javascript
// --- WEBSOCKET ---
let ws = null;
let wsReconnectTimer = null;
const WS_URL = `ws://localhost:8000/ws/buses`;

function connectWebSocket() {
    if (ws && ws.readyState <= WebSocket.OPEN) return; // Already connected

    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        console.log('[WS] Connected');
        updateConnectionBadge(true);
        // Stop HTTP polling — WebSocket takes over
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
        if (wsReconnectTimer) {
            clearTimeout(wsReconnectTimer);
            wsReconnectTimer = null;
        }
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'bus_update') {
                handleLiveBusUpdate(data.buses);
            }
        } catch (e) {
            console.error('[WS] Parse error:', e);
        }
    };

    ws.onclose = () => {
        console.log('[WS] Disconnected — falling back to polling');
        updateConnectionBadge(false);
        ws = null;
        // Restart HTTP polling as fallback
        if (!pollTimer) {
            pollTimer = setInterval(fetchLiveBusData, POLL_INTERVAL_MS);
        }
        // Auto-reconnect after 3s
        wsReconnectTimer = setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = () => ws.close();
}
```

**Extract shared bus update logic — refactor `fetchLiveBusData`'s success body into a shared function:**

```javascript
function handleLiveBusUpdate(liveBuses) {
    const activeBusIds = new Set();
    const formattedBuses = [];

    liveBuses.forEach(bus => {
        const busData = {
            id: bus.vehicle_id,
            routeId: bus.route_id,
            lat: bus.lat,
            lng: bus.lng,
            speed: bus.speed,
        };
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

**Update `main()` to prefer WebSocket:**
```javascript
async function main() {
    showRouteSkeletons();
    await fetchAndProcessStaticData();
    // Try WebSocket first, HTTP polling is fallback
    connectWebSocket();
    // Also start initial polling in case WS takes time to connect
    fetchLiveBusData();
    pollTimer = setInterval(fetchLiveBusData, POLL_INTERVAL_MS);
}
```

**Also update `fetchLiveBusData` to call `handleLiveBusUpdate` instead of duplicating the logic.**

---

### TASK 2: Serve Frontend from FastAPI (HIGH PRIORITY)

**Problem:** Frontend requires a separate HTTP server (`python -m http.server 5500`). This complicates deployment — need 3 terminals to run.

**Goal:** Serve the frontend as static files from FastAPI so everything runs on port 8000.

**File:** `backend/app/main.py`

**Add at the bottom, AFTER all router registrations:**
```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Serve frontend static files — must be LAST (catch-all route)
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
```

**Update `frontend/assets/app.js` config:**
```javascript
// Auto-detect API base URL (works in both dev and production)
const API_BASE_URL = window.location.origin;
const WS_URL = `ws://${window.location.host}/ws/buses`;
```

**Update `config.py` — widen CORS for development:**
```python
FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:8000")
```

**Update `.env` and `.env.example`:**
```
FRONTEND_ORIGIN=http://localhost:8000
```

Now the entire app runs with just: `uvicorn backend.app.main:app --port 8000`

---

### TASK 3: Cloud Deployment — Railway (HIGH PRIORITY)

**Goal:** Deploy to Railway for a public demo URL.

**1. Create `Procfile` at project root:**
```
web: uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

**2. Create `runtime.txt`:**
```
python-3.11
```

**3. Update `Dockerfile`:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**4. Update `backend/app/config.py`** to handle Railway's `DATABASE_URL` format:
```python
import re

# Railway provides DATABASE_URL as postgres:// but asyncpg needs postgresql://
_raw_db_url = os.getenv("DATABASE_URL", "postgresql://user:secretpass123@localhost:5433/transit_db")
DATABASE_URL: str = re.sub(r'^postgres://', 'postgresql://', _raw_db_url)
```

**5. Update `frontend/assets/app.js`** to detect WebSocket protocol:
```javascript
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = `${wsProtocol}//${window.location.host}/ws/buses`;
```

**6. Railway setup steps (manual):**
- Connect GitHub repo `Devansh-Bansal-AI/Smart-Transit`
- Add Railway managed PostgreSQL (with TimescaleDB extension if available, or use regular Postgres)
- Set environment variables: `JWT_SECRET`, `SIMULATOR_API_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`
- Railway auto-detects `Procfile` and deploys

---

### TASK 4: Historical Analytics API (MEDIUM PRIORITY)

**Goal:** Leverage TimescaleDB's time-series capabilities to provide fleet analytics.

**Create `backend/app/routers/analytics.py`:**

```python
"""
Historical fleet analytics endpoints using TimescaleDB aggregate queries.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.app.auth import verify_token
from backend.app.db.pool import get_pool

logger = logging.getLogger("smart_transit.analytics")
router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _require_db():
    pool = get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    return pool


@router.get("/fleet/summary")
async def fleet_summary(_token: dict = Depends(verify_token)):
    """Overall fleet statistics for the last 24 hours."""
    pool = _require_db()
    async with pool.acquire() as conn:
        data = await conn.fetchrow("""
            SELECT
                COUNT(DISTINCT vehicle_id) AS unique_buses,
                COUNT(*) AS total_pings,
                ROUND(AVG(speed)::numeric, 2) AS avg_speed_kmh,
                ROUND(MAX(speed)::numeric, 2) AS max_speed_kmh,
                MIN(time) AS earliest_ping,
                MAX(time) AS latest_ping
            FROM vehicle_logs
            WHERE time > NOW() - INTERVAL '24 hours'
        """)
    return dict(data) if data else {}


@router.get("/fleet/hourly")
async def fleet_hourly_activity(_token: dict = Depends(verify_token)):
    """Hourly ping counts and average speed for the last 24h."""
    pool = _require_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                date_trunc('hour', time) AS hour,
                COUNT(DISTINCT vehicle_id) AS active_buses,
                COUNT(*) AS total_pings,
                ROUND(AVG(speed)::numeric, 2) AS avg_speed
            FROM vehicle_logs
            WHERE time > NOW() - INTERVAL '24 hours'
            GROUP BY date_trunc('hour', time)
            ORDER BY hour
        """)
    return [dict(r) for r in rows]


@router.get("/bus/{vehicle_id}/history")
async def bus_history(
    vehicle_id: str,
    hours: int = Query(default=1, ge=1, le=24),
    _token: dict = Depends(verify_token),
):
    """GPS trail for a specific bus over the last N hours."""
    pool = _require_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT latitude, longitude, speed, time
            FROM vehicle_logs
            WHERE vehicle_id = $1 AND time > NOW() - INTERVAL '1 hour' * $2
            ORDER BY time ASC
        """, vehicle_id, hours)
    return [
        {"lat": r["latitude"], "lng": r["longitude"], "speed": r["speed"], "time": r["time"].isoformat()}
        for r in rows
    ]


@router.get("/routes/performance")
async def route_performance(_token: dict = Depends(verify_token)):
    """Average speed per route for the last 24 hours."""
    pool = _require_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                vl.route_id,
                r.route_name,
                COUNT(DISTINCT vl.vehicle_id) AS buses_operated,
                ROUND(AVG(vl.speed)::numeric, 2) AS avg_speed,
                COUNT(*) AS total_pings
            FROM vehicle_logs vl
            LEFT JOIN routes r ON vl.route_id = r.route_id
            WHERE vl.time > NOW() - INTERVAL '24 hours'
            GROUP BY vl.route_id, r.route_name
            ORDER BY avg_speed DESC
        """)
    return [dict(r) for r in rows]
```

**Register in `main.py`:**
```python
from backend.app.routers import analytics
app.include_router(analytics.router)
```

**Add tests for analytics endpoints in `tests/test_api.py`:**
```python
def test_analytics_requires_auth(client):
    """Analytics endpoints should require JWT."""
    response = client.get("/analytics/fleet/summary")
    assert response.status_code == 401

def test_analytics_fleet_summary_no_db(client):
    """Fleet summary should return 503 without DB."""
    auth = client.post("/auth/token", json={"username": "admin", "password": "admin123"})
    token = auth.json()["access_token"]
    response = client.get("/analytics/fleet/summary", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 503
```

---

### TASK 5: Admin Route Management CRUD (MEDIUM PRIORITY)

**Goal:** Admin endpoints to add/update/delete routes and stops without direct DB access.

**Create `backend/app/routers/admin.py`:**

```python
"""
Admin CRUD endpoints for route and stop management.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List
from backend.app.auth import verify_token
from backend.app.db.pool import get_pool

logger = logging.getLogger("smart_transit.admin")
router = APIRouter(prefix="/admin", tags=["Admin"])


class StopInput(BaseModel):
    stop_name: str = Field(..., min_length=1)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class RouteInput(BaseModel):
    route_id: str = Field(..., min_length=1)
    route_name: str = Field(..., min_length=1)
    stops: List[StopInput]


def _require_db():
    pool = get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    return pool


@router.get("/routes")
async def list_all_routes(_token: dict = Depends(verify_token)):
    pool = _require_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT route_id, route_name FROM routes ORDER BY route_id")
    return [dict(r) for r in rows]


@router.post("/routes", status_code=201)
async def create_route(route: RouteInput, _token: dict = Depends(verify_token)):
    pool = _require_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO routes (route_id, route_name) VALUES ($1, $2) ON CONFLICT (route_id) DO UPDATE SET route_name = EXCLUDED.route_name",
                route.route_id, route.route_name,
            )
            await conn.execute("DELETE FROM stops WHERE route_id = $1", route.route_id)
            for idx, stop in enumerate(route.stops):
                await conn.execute(
                    "INSERT INTO stops (route_id, stop_name, latitude, longitude, stop_sequence) VALUES ($1, $2, $3, $4, $5)",
                    route.route_id, stop.stop_name, stop.latitude, stop.longitude, idx,
                )
    return {"status": "created", "route_id": route.route_id}


@router.delete("/routes/{route_id}")
async def delete_route(route_id: str, _token: dict = Depends(verify_token)):
    pool = _require_db()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM routes WHERE route_id = $1", route_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Route not found")
    return {"status": "deleted", "route_id": route_id}
```

**Register in `main.py`:**
```python
from backend.app.routers import admin
app.include_router(admin.router)
```

---

### TASK 6: PWA Offline Support (LOW PRIORITY)

**Goal:** Make the frontend installable as a PWA and show cached map data offline.

**1. Create `frontend/manifest.json`:**
```json
{
  "name": "Smart Transit",
  "short_name": "SmartTransit",
  "description": "Real-time intelligent transit navigation",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0f172a",
  "theme_color": "#3b82f6",
  "icons": [
    { "src": "assets/bus-icon.svg", "sizes": "any", "type": "image/svg+xml" }
  ]
}
```

**2. Create `frontend/sw.js` (service worker):**
```javascript
const CACHE_NAME = 'smart-transit-v1';
const STATIC_ASSETS = ['/', '/index.html', '/assets/app.js', '/assets/style.css', '/assets/bus-icon.svg'];

self.addEventListener('install', (event) => {
    event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)));
});

self.addEventListener('fetch', (event) => {
    // Cache-first for static assets, network-first for API calls
    if (event.request.url.includes('/api') || event.request.url.includes('/buses') || event.request.url.includes('/routes')) {
        event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
    } else {
        event.respondWith(caches.match(event.request).then(r => r || fetch(event.request)));
    }
});
```

**3. Register in `frontend/index.html` `<head>`:**
```html
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#3b82f6">
```

**4. Register in `frontend/assets/app.js`:**
```javascript
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
}
```

---

### TASK 7: Professional README & Demo (LOW PRIORITY)

**Goal:** Make the README GitHub-portfolio-worthy.

**Implementation:**
1. Replace ASCII architecture diagram with a proper **Mermaid diagram** in README
2. Add **badges** at top: `![Tests](https://github.com/Devansh-Bansal-AI/Smart-Transit/actions/workflows/ci.yml/badge.svg)`, Python version, License
3. Add a **Features** section with emoji icons
4. Add a **Screenshots** section — run the app, capture screenshots, save to `docs/screenshots/`
5. Add **API Reference** table with all endpoints including the new analytics and admin ones
6. Add **Contributing** section and `LICENSE` file

---

## Priority Execution Order

| # | Task | Priority | Impact | Effort |
|---|---|---|---|---|
| 1 | Frontend WebSocket client | 🔴 Critical | Completes the real-time pipeline | ~40 lines |
| 2 | Serve frontend from FastAPI | 🔴 High | Simplifies deployment to 1 command | ~10 lines |
| 3 | Cloud deployment (Railway) | 🔴 High | Public demo URL | Config files |
| 4 | Historical analytics API | 🟡 Medium | Enterprise-grade data insights | ~100 lines |
| 5 | Admin route CRUD | 🟡 Medium | Self-serve route management | ~80 lines |
| 6 | PWA offline support | 🟢 Low | Installable app, offline maps | ~50 lines |
| 7 | README + demo screenshots | 🟢 Low | Portfolio presentation | Documentation |

---

## Important Notes for Execution

- Python version on user's machine: **3.10** (Windows)
- All `POST /location` requests now require `X-API-Key` header
- All `/stats` and analytics endpoints require `Authorization: Bearer <jwt>` header
- The frontend currently lives at `frontend/` — when served from FastAPI, it maps to `/`
- WebSocket URL must auto-detect `ws://` vs `wss://` for Railway (HTTPS) deployment
- TimescaleDB-specific SQL functions (like `time_bucket`) may not be available on Railway's plain Postgres — use standard `date_trunc` instead
- The `staticfiles` mount MUST be last in `main.py` (it's a catch-all that will swallow other routes if placed first)
