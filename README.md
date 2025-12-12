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
⚡ Quick Start Guide
Follow these steps to run the project locally.

1. Prerequisites
Python 3.9 or higher

Git

2. Installation
Clone the repository and navigate to the project folder:

Bash

git clone [https://github.com/abhinav-atul/Smart-Transit.git](https://github.com/abhinav-atul/Smart-Transit.git)
cd Smart-Transit
git checkout abhi_new
Install the required Python libraries:

Bash

pip install -r requirements.txt
3. Running the System
You will need three separate terminals to run the full system.

Terminal 1: Start the Backend API
This starts the FastAPI server which handles all logic.

Bash

uvicorn api.main:app --reload
Server will start at: http://localhost:8000

API Docs available at: http://localhost:8000/docs

Terminal 2: Start the Bus Simulator
This script pretends to be a GPS device on a bus. It sends location updates every 2 seconds.

Bash

python bus_simulator.py
You should see logs like: Bus: STOP_A->STOP_B | Speed: 45km/h | ETA: 12.5 min

Terminal 3: Launch the Frontend
Since the frontend is static HTML, you can simply open the file in your browser.

Navigate to the frontend/ folder.

Double-click index.html to open it in Chrome/Edge/Firefox.

🧪 Testing Features
1. Live Tracking
Open the Frontend Dashboard.

You will see a Bus Icon moving on the map (Delhi region default).

Click the icon to see the sidebar with live details.

2. Smart ETA
Observe the ETA in the sidebar or the simulator terminal.

The ETA adjusts dynamically based on the simulated speed of the bus.

3. Crowd Analysis (Camera Simulation)
To test the crowd detection, you can manually send an image to the API (since we don't have a real physical bus camera connected).

Using Postman or cURL:

Bash

curl -X 'POST' \
  'http://localhost:8000/api/v1/crowd' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@/path/to/your/image.jpg'
Upload an image with faces to see the "Crowd Count" update on the dashboard!

🔮 Future Roadmap
[ ] Connect to PostgreSQL/TimescaleDB for historical data storage.

[ ] Implement Redis for caching frequent ETA requests.

[ ] Add mobile app (Flutter) integration.

[ ] Deploy on AWS/Google Cloud.

🤝 Contributing
Fork the repository.

Create a new branch (git checkout -b feature-branch).

Commit your changes.

Push to the branch.

Open a Pull Request.

Author: Abhinav Atul