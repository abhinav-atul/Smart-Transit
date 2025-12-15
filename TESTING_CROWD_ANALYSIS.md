# Testing the Face Detection Crowd Analysis Feature

This guide explains how to test the face detection crowd analysis feature end-to-end.

## Prerequisites

1. **Docker** - Running TimescaleDB instance
2. **Python 3.8+** - With required dependencies installed
3. **Backend API** - Running on port 8000
4. **Frontend** - Served via Live Server on port 5500

## Installation Steps

### 1. Start the Database

```bash
docker compose up -d
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize/Migrate Database

For new installations:
```bash
python scripts/setup_tables.py
python scripts/init_db_data.py
```

For existing installations (add crowd_status column):
```bash
python scripts/migrate_crowd_status.py
```

## Testing Process

### Step 1: Test the Face Detection Module

Verify the face detection module works correctly:

```bash
python scripts/test_face_detection.py
```

Expected output:
```
🧪 Testing Face Detection Module

✓ FaceValidator initialized successfully

📝 Test 1: Processing test image...
  ✓ Face count: X
  ✓ Crowd status: low/medium/high
  ✓ Confidence: 0.XX

📝 Test 2: Processing image from bytes...
  ✓ Successfully processed from bytes

📝 Test 3: Testing crowd status thresholds...
  ✓ Empty image test passed

✅ All tests passed!
```

### Step 2: Start the Backend API

Open Terminal 1 and run:

```bash
uvicorn backend.app.main_old:app --reload --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
✅ Database connection established.
```

Verify API is running by visiting: http://localhost:8000/docs

### Step 3: Start the Bus Simulator

Open Terminal 2 and run:

```bash
python simulation/bus_simulator.py
```

Expected output:
```
🚌 Initializing Bus Simulation with Variable Speeds...
📍 Processing Route: ...
🚀 Simulation Started!
📡 Sent ping → BUS-01
```

### Step 4: Start the Camera Simulator

Open Terminal 3 and run:

```bash
python hardware/face_detection/camera_simulator.py BUS-01 10
```

Expected output:
```
🎥 Camera Simulator Started
   Bus ID: BUS-01
   Capture Interval: 10s
   Camera Mode: Simulated
   Press Ctrl+C to stop

📸 Capture #1 at HH:MM:SS
   Generated test image (simulated faces: ~15)
   Detected faces: 0
   Crowd status: UNKNOWN
   Confidence: 0.00
✅ Crowd data sent: BUS-01 - unknown (0 people)
```

Note: The simulated test images don't contain actual faces recognizable by MediaPipe, so it will show 0 faces. For real testing, use the `--camera` flag with an actual camera.

### Step 5: Open the Frontend

1. Open the project in VS Code
2. Install the "Live Server" extension
3. Right-click on `frontend/index.html`
4. Select "Open with Live Server"
5. Browser should open at: http://localhost:5500

### Step 6: Verify Frontend Display

#### In Fleet View (Authority View):

1. Click the "Fleet" tab in the navigation
2. You should see all active buses listed
3. Each bus should display:
   - Bus ID
   - Speed
   - Crowd status badge (color-coded)
   - Passenger count

#### In Routes View:

1. Click the "Routes" tab
2. Select a route (e.g., AS-1)
3. Click on a bus marker on the map
4. The "Selected Vehicle" card should show:
   - Bus ID
   - Speed
   - Next Stop
   - ETA
   - **Crowd Status** (new section)
   - Passenger count

#### Expected Crowd Status Display:

- 🟢 **Green badge** with "✓ Low" - 0-10 passengers
- 🟡 **Yellow badge** with "⚠ Medium" - 11-25 passengers
- 🔴 **Red badge** with "✕ Full" - 26+ passengers
- ⚪ **Gray badge** with "? Unknown" - No data available

## Manual API Testing

You can also test the API endpoints directly using curl or Postman:

### Test Crowd Status Endpoint

```bash
curl -X POST http://localhost:8000/crowd-status \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "BUS-01",
    "passenger_count": 15,
    "crowd_status": "medium",
    "timestamp": "2024-01-01T12:00:00"
  }'
```

Expected response:
```json
{
  "status": "success",
  "vehicle": "BUS-01",
  "crowd_status": "medium",
  "passenger_count": 15
}
```

### Verify Live Bus Data Includes Crowd Status

```bash
curl http://localhost:8000/buses/live
```

Expected response (should include crowd_status and passenger_count):
```json
[
  {
    "vehicle_id": "BUS-01",
    "route_id": "AS-1",
    "lat": 31.6339,
    "lng": 74.8723,
    "speed": 45.5,
    "last_update": "2024-01-01T12:00:00",
    "passenger_count": 15,
    "crowd_status": "medium"
  }
]
```

## Testing with Real Camera

If you have a webcam or camera connected:

```bash
python hardware/face_detection/camera_simulator.py BUS-01 10 --camera
```

The system will:
1. Capture images from your camera every 10 seconds
2. Detect actual faces using MediaPipe
3. Calculate crowd status
4. Send data to the backend
5. Display results in the frontend

## Troubleshooting

### Camera Simulator Shows 0 Faces

This is expected when using simulated images. The generated test images don't contain actual faces. Use `--camera` flag with a real camera for face detection.

### Database Connection Error

Make sure Docker container is running:
```bash
docker ps
docker compose up -d
```

### API Not Receiving Data

Check that:
1. Backend API is running on port 8000
2. The API_BASE_URL in camera_simulator.py points to the correct address
3. No firewall is blocking the connection

### Frontend Not Showing Crowd Status

1. Check browser console for errors (F12)
2. Verify API response includes crowd_status and passenger_count fields
3. Clear browser cache and reload
4. Make sure you're using the latest version of frontend/assets/app.js

## Expected End-to-End Flow

1. **Bus Simulator** → Sends GPS location to `/location` endpoint
2. **Camera Simulator** → Captures image → Detects faces → Sends crowd data to `/crowd-status` endpoint
3. **Backend** → Stores crowd data in database → Updates vehicle_logs table
4. **Frontend** → Fetches live bus data from `/buses/live` → Displays crowd status with color-coded badges

## Performance Notes

- Camera captures run on a configurable interval (default: 10 seconds)
- Face detection takes approximately 100-500ms per frame
- Database updates are immediate
- Frontend refreshes every 2 seconds
- No images are stored or transmitted (only face counts for privacy)
