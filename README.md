# 🚍 Smart Transit System

A real-time intelligent transit navigation system featuring live bus tracking, route optimization, and a modern dashboard. This project uses a **FastAPI** backend, **Vanilla JavaScript** frontend, and **TimescaleDB (PostgreSQL)** for time-series data storage.

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed on your machine:

1. **Python 3.8+** – [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. **Docker Desktop** – Required for the database: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
3. **Git** – To clone the repository

---

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/Smart-Transit.git
cd Smart-Transit
```

---

### 2. Set up the Database (Docker)

We use Docker to run a TimescaleDB instance. Make sure Docker Desktop is running.

```bash
# Start the database container
docker compose up -d
```

> **Note:** If `docker compose` fails, try:
>
> ```bash
> docker-compose up -d
> ```

---

### 3. Install Python Dependencies

Install all required libraries using the provided `requirements.txt` file.

```bash
pip install -r requirements.txt
```

---

### 4. Initialize the Database

#### A. Create Tables

Ensure the database schema is applied. You can use the helper script or run the SQL manually.

```bash
python scripts/setup_tables.py
```

#### B. Load Route Data

Populate the database with stops and routes defined in `simulation/data/config.json`.

```bash
python scripts/init_db_data.py
```

**Expected Output:**

```
✅ Success! Database populated successfully.
```

---

## 🚀 How to Run (3-Terminal Setup)

You need to run three separate processes simultaneously. Open **three terminal windows** in the project root folder.

---

### 🖥️ Terminal 1: Backend API

This server handles GPS pings and serves data to the frontend.

```bash
uvicorn backend.app.main_old:app --reload --port 8000
```

📘 API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 🚌 Terminal 2: Bus Simulator

This script simulates buses moving along the routes and sending GPS coordinates.

```bash
python simulation/bus_simulator.py
```

You should see logs like:

```
📡 Sent ping → BUS-01
```

---

### 🌐 Terminal 3: Frontend Client

Use **Live Server** (VS Code extension) to run the frontend. Since the frontend uses ES6 modules, it must be served via a local web server.

**Steps:**

1. Open the project in **VS Code**
2. Install the **Live Server** extension (by Ritwick Dey)
3. Right-click on `frontend/index.html`
4. Click **"Open with Live Server"**

The application will automatically open in your browser.

---

## 🌍 Access the Application

Open your web browser and visit:

👉 **[http://localhost:5500](http://localhost:5500)**

### Features

* **Finder View:** Search for a stop to find the nearest bus
* **Routes View:** Click a route (e.g., AS-1) to see its path and stops on the map
* **Fleet View:** Monitor real-time statuses of all active buses

---

## 📂 Project Structure

```
Smart-Transit/
├── backend/
│   └── app/
│       ├── main_old.py        # Main API Server
│       └── db/schema.sql     # Database Structure
├── frontend/
│   ├── index.html             # Main User Interface
│   └── assets/                # JS Logic & CSS Styles
├── simulation/
│   ├── bus_simulator.py       # GPS Simulation Script
│   └── data/config.json       # Route & Stop Definitions
├── scripts/
│   ├── setup_tables.py        # Create a Setup Script
│   └── init_db_data.py        # Data Seeding Script
└── docker-compose.yml         # DB Container Configuration
```

---

## 🔧 Troubleshooting

* **Map not loading?**
  Check `frontend/assets/app.js` and ensure the `MAPS_API_KEY` is valid.

* **Error: `relation \"routes\" does not exist`?**
  The database tables were not created. Run the schema creation step in **Installation – Step 4A**.

* **CORS errors in browser console?**
  Ensure the frontend is accessed via `http://localhost:5500` and not by double-clicking the HTML file.

---

✨ *Happy Building!*
