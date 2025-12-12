# Smart-transit

---
 
# 🚌 Smart-Transit
> A real-time public transit tracking system featuring live bus locations, dynamic routing, and an interactive "Liquid Glass" UI.

**Smart-Transit** is a full-stack prototype that simulates and visualizes a smart public transportation network. It uses **Python** to simulate bus movements along real-world geographic paths (using Google Maps Directions API) and updates a **Firebase** backend in real-time. The frontend consumes this data to display live bus markers, calculate ETXs (Estimated Time of Arrival), and show route paths on an interactive map.

---

## 🌟 Key Features

* **📍 Real-Time Fleet Tracking**: Watch buses move live on the map with smooth updates.
* **AQ Route Visualization**: View color-coded route paths (polylines) overlaid on the map.
* **DO ETA Calculator**: Select a start and end stop to instantly find the nearest bus and its arrival time.
* **🌓 Dynamic Theming**: Toggle between Light and Dark modes with custom map styles.
* **🆘 Emergency SOS**: A built-in SOS alert system for passenger safety.
* **📱 Responsive UI**: A "Liquid Glass" design ensuring the app looks great on desktop and mobile.
* **🤖 Backend Simulation**: A Python script that generates realistic bus traffic patterns based on real road networks.

---

## 🛠️ Tech Stack

### Frontend
* **HTML5 & CSS3**: Custom "Liquid Glass" styling and animations.
* **Tailwind CSS**: For rapid, responsive layout design.
* **JavaScript (ES6+)**: Core application logic.
* **Google Maps JavaScript API**: Map rendering, directions, and distance matrices.
* **Firebase SDK (Web)**: Authentication and Firestore real-time listeners.

### Backend / Simulation
* **Python**: Core logic for the bus simulator.
* **Firebase Admin SDK**: For secure server-side writing to the database.
* **Google Maps Python Client**: To fetch accurate road geometries for simulation paths.
* **Geopy**: For geodesic distance calculations (detecting stop arrivals).

---

## 🚀 Getting Started

Follow these steps to set up the project locally.

### Prerequisites
1.  **Node.js & NPM** (for package management).
2.  **Python 3.x** (for the simulator).
3.  A **Google Cloud Project** with the *Maps JavaScript API* and *Directions API* enabled.
4.  A **Firebase Project** with Firestore enabled.

### Step 1: Clone & Install Dependencies
Clone the repository and install the Python dependencies for the simulator.

```bash
# Clone the project
git clone [https://github.com/your-username/smart-transit.git](https://github.com/your-username/smart-transit.git)
cd smart-transit

# Install Python requirements (creates a virtual environment recommended)
pip install firebase-admin googlemaps geopy