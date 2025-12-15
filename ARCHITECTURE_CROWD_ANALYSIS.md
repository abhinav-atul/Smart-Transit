# Face Detection Crowd Analysis - Architecture

## System Overview

The face detection crowd analysis feature integrates seamlessly with the existing Smart Transit system to provide real-time passenger count and crowd density information.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Smart Transit System                          │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐         ┌──────────────┐
│  On-Vehicle      │         │   Backend API    │         │   Frontend   │
│  Camera System   │         │   (FastAPI)      │         │  Dashboard   │
└──────────────────┘         └──────────────────┘         └──────────────┘
        │                             │                            │
        │                             │                            │
        ▼                             ▼                            ▼
┌──────────────────┐         ┌──────────────────┐         ┌──────────────┐
│ Camera Simulator │         │  POST /location  │         │  Fleet View  │
│  (periodic       │────────▶│ POST /crowd-     │◀────────│  Routes View │
│   captures)      │         │      status      │         │  Finder View │
└──────────────────┘         │  GET /buses/live │         └──────────────┘
        │                    └──────────────────┘                 │
        │                             │                           │
        ▼                             ▼                           ▼
┌──────────────────┐         ┌──────────────────┐         ┌──────────────┐
│  Face Detection  │         │   TimescaleDB    │         │ Crowd Status │
│  Module (AI/ML)  │         │  (PostgreSQL)    │         │   Display    │
│  - MediaPipe     │         │                  │         │  - Badges    │
│  - OpenCV        │         │  vehicle_logs:   │         │  - Colors    │
└──────────────────┘         │  - crowd_status  │         │  - Counts    │
                             │  - passenger_    │         └──────────────┘
                             │    count         │
                             └──────────────────┘
```

## Data Flow

### 1. Camera Capture & Analysis

```
┌─────────────┐
│   Camera    │  Captures image every N seconds (configurable)
│   System    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Image     │  Raw camera frame (640x480 RGB)
│   Frame     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│        Face Detection (MediaPipe)           │
│  - Detects faces in frame                   │
│  - Counts number of faces                   │
│  - Returns confidence score                 │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│        Crowd Status Classification          │
│  - Low:     0-10 faces                      │
│  - Medium:  11-25 faces                     │
│  - High:    26+ faces                       │
│  - Unknown: 0 faces (no detection)          │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│  POST /     │  Send to backend API
│  crowd-     │  {vehicle_id, passenger_count, crowd_status}
│  status     │
└─────────────┘
```

### 2. Backend Processing

```
┌──────────────────┐
│  POST /crowd-    │  Receives crowd data
│  status          │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────┐
│  Update Database                     │
│  UPDATE vehicle_logs                 │
│  SET passenger_count = X,            │
│      crowd_status = 'medium'         │
│  WHERE vehicle_id = 'BUS-01'         │
│  AND time = (latest entry)           │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────┐
│  Return Success  │
│  {status, ...}   │
└──────────────────┘
```

### 3. Frontend Display

```
┌──────────────────┐
│  GET /buses/     │  Frontend polls every 2 seconds
│  live            │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────┐
│  Response includes:                  │
│  {                                   │
│    vehicle_id, route_id,             │
│    lat, lng, speed,                  │
│    passenger_count,     ◄── New!    │
│    crowd_status         ◄── New!    │
│  }                                   │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│  Display in UI                       │
│  - Fleet View: Badge + Count         │
│  - Bus Detail Card: Status Section   │
│  - Color coding: Green/Yellow/Red    │
└──────────────────────────────────────┘
```

## Component Details

### Face Detection Module (`detect.py`)

**Class:** `FaceValidator`

**Methods:**
- `__init__(min_detection_confidence)` - Initialize MediaPipe detector
- `process_frame(frame)` - Detect faces in OpenCV frame
- `analyze_crowd(frame)` - Full analysis with crowd classification
- `process_image_from_bytes(bytes)` - Process raw image bytes
- `process_image_from_base64(string)` - Process base64 encoded image

**Returns:**
```python
{
    "face_count": 15,           # Number of faces detected
    "crowd_status": "medium",   # low/medium/high/unknown
    "confidence": 0.85          # Detection confidence
}
```

### Camera Simulator (`camera_simulator.py`)

**Function:** `simulate_camera_system(bus_id, interval, use_real_camera)`

**Process:**
1. Initialize face detector
2. Loop indefinitely:
   - Capture image (real camera or simulated)
   - Analyze crowd using detector
   - Send data to backend API
   - Wait for interval period
   - Repeat

**Command Line:**
```bash
python camera_simulator.py [BUS_ID] [INTERVAL] [--camera]
```

### Backend API Endpoints

#### POST `/crowd-status`
**Request:**
```json
{
  "vehicle_id": "BUS-01",
  "passenger_count": 15,
  "crowd_status": "medium",
  "timestamp": "2024-01-01T12:00:00"
}
```

**Response:**
```json
{
  "status": "success",
  "vehicle": "BUS-01",
  "crowd_status": "medium",
  "passenger_count": 15
}
```

#### GET `/buses/live`
**Response (Extended):**
```json
[
  {
    "vehicle_id": "BUS-01",
    "route_id": "AS-1",
    "lat": 31.6339,
    "lng": 74.8723,
    "speed": 45.5,
    "last_update": "2024-01-01T12:00:00",
    "passenger_count": 15,      // New field
    "crowd_status": "medium"    // New field
  }
]
```

### Database Schema

**Table:** `vehicle_logs`

**New Fields:**
- `passenger_count` (INT) - Number of passengers detected
- `crowd_status` (VARCHAR(20)) - Crowd level: low/medium/high/unknown

**Index:** Time-series index on `time` field (TimescaleDB hypertable)

### Frontend Components

**JavaScript Functions:**
- `getCrowdStatusDisplay(status)` - Maps status to display properties
- `fetchLiveBusData()` - Extended to include crowd data
- `updateAuthorityList(buses)` - Shows crowd badges
- `updateBusDetailCard(busData)` - Displays crowd section

**UI Elements:**
- `#bus-detail-crowd-badge` - Color-coded status badge
- `#bus-detail-passenger-count` - Passenger count display
- Fleet view cards with inline crowd indicators

## Privacy & Security

1. **No Image Storage:** Only face counts are transmitted, not images
2. **No Personal Data:** No facial recognition or identity tracking
3. **Aggregated Data:** Only crowd density metrics stored
4. **Local Processing:** Face detection runs on-vehicle (edge computing)
5. **Encrypted Transport:** API uses HTTPS in production (recommended)

## Performance Characteristics

- **Face Detection:** ~100-500ms per frame
- **API Response:** <100ms
- **Database Update:** <50ms
- **Frontend Refresh:** 2 seconds
- **Camera Capture:** Configurable (default: 10 seconds)
- **Memory Usage:** ~200MB per camera process
- **CPU Usage:** ~10-20% during detection

## Scalability

- **Multiple Buses:** Each bus runs independent camera simulator
- **Load Balancing:** API can handle 100+ concurrent updates
- **Database:** TimescaleDB optimized for time-series data
- **Horizontal Scaling:** Can deploy multiple API instances behind load balancer

## Future Enhancements

1. **Advanced Analytics:**
   - Peak hour analysis
   - Route-based capacity planning
   - Historical trends and predictions

2. **Smart Notifications:**
   - Alert users when buses are too full
   - Suggest alternative routes
   - Capacity-based routing

3. **Improved Detection:**
   - Deep learning models for better accuracy
   - People counting with depth cameras
   - Occlusion handling

4. **Real-time Alerts:**
   - Notify transit authority of overcrowding
   - Automatic dispatch of additional buses
   - Dynamic fare pricing based on demand
