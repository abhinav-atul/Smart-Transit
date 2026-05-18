# Smart Transit System

A real-time intelligent transit navigation system featuring live bus tracking, ML-powered ETA prediction, route optimization, and a modern glassmorphism dashboard.

Built with **FastAPI** backend, **Vanilla JavaScript** frontend, **TimescaleDB** for time-series data, and **scikit-learn** for ML predictions.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│   ┌──────────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│   │  Finder View  │  │  Routes  │  │  Fleet   │  │ Emergency │  │
│   │  (Stop → ETA) │  │  View    │  │  View    │  │    SOS    │  │
│   └──────┬───────┘  └────┬─────┘  └────┬─────┘  └───────────┘  │
│          └───────────────┼──────────────┘                        │
│                    Leaflet Map + OSRM                            │
│                   (Dark/Light Theme)                             │
└────────────────────────┬─────────────────────────────────────────┘
                         │ WebSocket (/ws/buses) + HTTP fallback
                         ▼
┌────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                             │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌───────┐ ┌──────────┐ │
│  │ /location│ │/buses/   │ │/routes │ │ /eta  │ │  /stats  │ │
│  │  (POST)  │ │  live    │ │ (GET)  │ │ (GET) │ │  (GET)   │ │
│  └────┬─────┘ └────┬─────┘ └───┬────┘ └───┬───┘ └────┬─────┘ │
│       │             │           │          │          │        │
│       ▼             ▼           ▼          ▼          ▼        │
│  ┌─────────────────────┐  ┌──────────────────────┐            │
│  │   TimescaleDB Pool  │  │   ML ETA Predictor   │            │
│  │   (asyncpg)         │  │ (GradientBoosting /  │            │
│  │                     │  │  Rule-based fallback)│            │
│  └──────────┬──────────┘  └──────────────────────┘            │
└─────────────┼──────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────┐    ┌─────────────────────────────┐
│  TimescaleDB (Docker)   │    │    Bus Simulator (Python)    │
│  - routes               │    │    - OSRM road paths         │
│  - stops                │◄───│    - Variable speed logic    │
│  - vehicle_logs (TSDB)  │    │    - GPS ping → /location    │
└─────────────────────────┘    └─────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla JS, Leaflet.js, Tailwind CSS, Font Awesome |
| Backend | Python, FastAPI, asyncpg, Pydantic |
| Database | TimescaleDB (PostgreSQL) via Docker |
| ML Engine | scikit-learn (GradientBoostingRegressor), joblib |
| Maps | OSRM (routing), CARTO (tiles) |
| DevOps | Docker, Docker Compose |
| Testing | pytest, httpx, FastAPI TestClient |

---

## Prerequisites

- **Python 3.10+** — [python.org](https://www.python.org/downloads/)
- **Docker Desktop** — [docker.com](https://www.docker.com/products/docker-desktop/)
- **Git**

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/abhinav-atul/Smart-Transit.git
cd Smart-Transit
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your database password and auth secrets
```

### 3. Start Database

```bash
docker compose up -d
```

### 4. Initialize Database

```bash
python scripts/setup_tables.py
python scripts/init_db_data.py
```

### 5. (Optional) Train ML Model

```bash
python ml_engine/dataset_generator.py
python ml_engine/train_model.py
copy eta_model.pkl ml_engine\eta_model.pkl
```

### 6. Run (3 Terminals)

```bash
# Terminal 1: Backend API
uvicorn backend.app.main:app --reload --port 8000

# Terminal 2: Bus Simulator
python simulation/bus_simulator.py

# Terminal 3: Frontend
cd frontend && python -m http.server 5500
```

### Docker Full-Stack (Alternative)

```bash
docker compose up --build
```

Open **[http://localhost:5500](http://localhost:5500)** in your browser.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check with system status |
| `POST` | `/location` | Receive GPS pings from simulator (requires `X-API-Key`) |
| `GET` | `/buses/live` | Latest position of all active buses |
| `GET` | `/routes` | Static routes and stops (nested JSON) |
| `GET` | `/eta` | ML-powered ETA prediction |
| `GET` | `/stats` | Fleet statistics (requires JWT Bearer token) |
| `POST` | `/auth/token` | Issue JWT token for admin endpoints |
| `WS` | `/ws/buses` | Real-time bus position stream |
| `GET` | `/docs` | Interactive Swagger UI |

---

## Features

- **Finder View** — Search stops, find nearest bus with live ETA
- **Routes View** — Click a route to see path, stops, and active buses on map
- **Fleet View** — Monitor real-time status of all active buses
- **ML ETA** — Machine learning powered arrival predictions (with rule-based fallback)
- **Dark/Light Mode** — Seamless theme toggle with themed map tiles
- **Emergency SOS** — One-click emergency broadcast
- **Connection Status** — Live online/offline indicator
- **Skeleton Loading** — Shimmer effects during data fetches

---

## Project Structure

```
Smart-Transit/
├── backend/
│   └── app/
│       ├── main.py              # App factory, lifespan, middleware
│       ├── config.py            # Centralized settings from .env
│       ├── models.py            # Pydantic request/response schemas
│       ├── db/
│       │   ├── pool.py          # Async connection pool management
│       │   └── schema.sql       # Database schema (TimescaleDB)
│       └── routers/
│           ├── health.py        # GET /
│           ├── tracking.py      # POST /location, GET /buses/live
│           ├── routes.py        # GET /routes
│           ├── eta.py           # GET /eta
│           └── stats.py         # GET /stats
├── frontend/
│   ├── index.html               # Main UI
│   └── assets/
│       ├── app.js               # Frontend logic
│       ├── style.css            # Glassmorphism design system
│       └── bus-icon.svg         # Self-hosted bus marker icon
├── ml_engine/
│   ├── predictor.py             # ETA predictor (ML + fallback)
│   ├── train_model.py           # Model training script
│   └── dataset_generator.py     # Synthetic data generator
├── simulation/
│   ├── bus_simulator.py         # GPS simulation with OSRM paths
│   └── data/config.json         # Route & stop definitions
├── scripts/
│   ├── setup_tables.py          # DB schema creation
│   └── init_db_data.py          # Data seeding (idempotent)
├── tests/
│   └── test_api.py              # pytest API integration tests
├── docker-compose.yml           # Full-stack container config
├── Dockerfile                   # Backend container build
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
└── .gitignore
```

---

## Testing

```bash
pytest tests/ -v
```

```
15 passed in 3.18s
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Map not loading | Serve frontend via HTTP (not `file://`). Use Live Server or `python -m http.server` |
| `relation "routes" does not exist` | Run `python scripts/setup_tables.py` then `python scripts/init_db_data.py` |
| CORS errors | Ensure frontend is at the URL configured in `FRONTEND_ORIGIN` in `.env` |
| Database connection refused | Start Docker: `docker compose up -d` |
| No buses on map | Start simulator: `python simulation/bus_simulator.py` |
| ML ETA showing "fallback" | Train the model (see Quick Start step 5) |

---

## License

MIT
