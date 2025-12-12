# 🚌 Smart-Transit: AI-Powered Public Transport Tracking

**Smart-Transit** is a real-time intelligent public transportation system. It goes beyond simple GPS tracking by integrating **Machine Learning for ETA prediction** and **Computer Vision for Crowd Analysis** inside buses.

---

## 🚀 Key Features

* **📍 Live Vehicle Tracking**: Real-time map visualization of bus locations using Leaflet.js.
* **⏱️ Smart ETA Engine**: Calculates arrival times based on segment-level delays (similar to "Where Is My Train").
* **👥 Crowd Density Analysis**: Uses OpenCV to analyze bus camera feeds and detect passenger density (Green/Orange/Red status).
* **🌐 Microservices Architecture**: Built with **FastAPI**, separating tracking, ETA, and vision logic.
* **📱 Interactive Dashboard**: A responsive web frontend to monitor the fleet and view live stats.

---

## 🛠️ Tech Stack

* **Backend**: Python, FastAPI, Uvicorn
* **Computer Vision**: OpenCV (Haar Cascades)
* **Data Processing**: NumPy, Pydantic
* **Frontend**: HTML5, CSS3, JavaScript, Leaflet.js (OpenStreetMap)
* **Simulation**: Custom Python simulator to mimic real-time bus movement.

---

## 📂 Project Structure

```text
Smart-Transit/
│
├── api/                    # Backend API Gateway
│   ├── main.py             # Entry point (Routes & State Management)
│   └── ...
│
├── services/               # Core Logic Modules
│   ├── tracking.py         # GPS Data Ingestion
│   ├── eta_engine.py       # Smart ETA Calculation Logic
│   └── crowd_detect.py     # OpenCV Crowd Counting
│
├── frontend/               # User Interface
│   ├── index.html          # Dashboard
│   ├── app.js              # Map Logic
│   └── style.css           # Styling
│
├── bus_simulator.py        # Python script to simulate a moving bus
├── requirements.txt        # Python dependencies
└── README.md               # Project Documentation
```
## ⚡ Quick Start Guide

Follow these steps to run the project locally.

---

## 🛠 Prerequisites

Make sure you have the following installed:

- **Python 3.9 or higher**
- **Git**

---

## 📥 Installation

Clone the repository and navigate to the project directory:

```bash
git clone https://github.com/abhinav-atul/Smart-Transit.git
cd Smart-Transit
git checkout abhi_new
Install the required Python libraries:
```
## 📦 Install Dependencies

Install the required Python libraries:

```bash
pip install -r requirements.txt
```

## ▶️ Running the System
You will need three separate terminals to run the complete system.

### 🖥 Terminal 1: Start the Backend API
This starts the FastAPI server which handles all core logic.

```bash
uvicorn api.main:app --reload
Server URL: http://localhost:8000
```

API Docs: http://localhost:8000/docs

### 🚌 Terminal 2: Start the Bus Simulator
This script simulates a bus GPS device and sends location updates every 2 seconds.

```bash
Copy code
python bus_simulator.py
```
Expected logs:

text
Copy code
Bus: STOP_A->STOP_B | Speed: 45km/h | ETA: 12.5 min

### 🌐 Terminal 3: Launch the Frontend
The frontend is a static HTML dashboard.

Navigate to the frontend/ folder

Double-click index.html

Open it in Chrome / Edge / Firefox

## 🧪 Testing Features
### 1️⃣ Live Tracking
Open the frontend dashboard.

A bus icon will move on the map (default: Delhi region).

Click the bus icon to view live details in the sidebar.

### 2️⃣ Smart ETA
Observe the ETA in the sidebar or simulator terminal.

ETA updates dynamically based on simulated bus speed.

### 3️⃣ Crowd Analysis (Camera Simulation)
Since there is no physical bus camera, you can manually send an image to test crowd detection.

Using cURL or Postman:

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/crowd' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@/path/to/your/image.jpg'
```
📸 Upload an image containing faces to see the Crowd Count update on the dashboard.

## 🔮 Future Roadmap
 Integrate PostgreSQL / TimescaleDB for historical data storage

 Implement Redis for caching frequent ETA requests

 Add mobile app integration (Flutter)

 Deploy on AWS / Google Cloud

## 🤝 Contributing
Fork the repository

Create a new branch

```bash
git checkout -b feature-branch
```
Commit your changes

Push to your branch

Open a Pull Request

## 👨‍💻 Author
Abhinav Atul
