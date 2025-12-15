# Face Detection Crowd Analysis Module

This module provides face detection and crowd analysis functionality for the Smart Transit system's on-vehicle camera system.

## Overview

The face detection module analyzes camera images from buses to determine crowd density and passenger count. This information is displayed in real-time on the frontend dashboard.

## Components

### 1. `detect.py` - Face Detection Core Module

The `FaceValidator` class provides face detection and crowd analysis using MediaPipe.

**Features:**
- Face detection with configurable confidence threshold
- Crowd status classification (Low/Medium/High/Unknown)
- Support for processing images from various sources (frames, bytes, base64)
- Automatic resource cleanup

**Crowd Status Thresholds:**
- **Low**: 0-10 faces
- **Medium**: 11-25 faces
- **High**: 26+ faces
- **Unknown**: 0 faces detected

**Usage Example:**
```python
from detect import FaceValidator

# Initialize detector
detector = FaceValidator(min_detection_confidence=0.5)

# Analyze a camera frame
import cv2
frame = cv2.imread('bus_interior.jpg')
result = detector.analyze_crowd(frame)

print(f"Detected {result['face_count']} faces")
print(f"Crowd status: {result['crowd_status']}")
print(f"Confidence: {result['confidence']}")
```

### 2. `camera_simulator.py` - Camera Simulation Script

Simulates periodic camera captures from the on-vehicle camera system for testing and development.

**Features:**
- Periodic image capture at configurable intervals
- Test image generation with simulated passengers
- Optional real camera support
- Automatic crowd analysis and API submission

**Usage:**

```bash
# Run with default settings (BUS-01, 10-second interval, simulated camera)
python hardware/face_detection/camera_simulator.py

# Run with custom bus ID and interval
python hardware/face_detection/camera_simulator.py BUS-02 15

# Run with real camera
python hardware/face_detection/camera_simulator.py BUS-01 10 --camera
```

**Command-line Arguments:**
1. Bus ID (default: BUS-01)
2. Capture interval in seconds (default: 10)
3. `--camera` flag to use real camera instead of simulation

## API Integration

### Endpoint: POST /crowd-status

The camera system sends crowd analysis data to the backend via this endpoint.

**Request Body:**
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

## Frontend Display

The crowd status is displayed in two places:

1. **Fleet View (Authority View)**: Shows crowd status badge and passenger count for each bus
2. **Bus Detail Card (Routes View)**: Displays detailed crowd information for selected bus

**Status Color Coding:**
- 🟢 **Green**: Low crowd (comfortable)
- 🟡 **Yellow**: Medium crowd (moderate)
- 🔴 **Red**: High crowd (full)
- ⚪ **Gray**: Unknown (no data)

## Dependencies

Required Python packages:
- `opencv-python` - Image processing and camera interface
- `mediapipe` - Face detection ML model
- `numpy` - Numerical operations
- `requests` - HTTP client for API communication

Install with:
```bash
pip install opencv-python mediapipe numpy requests
```

## Testing

Run the test script to verify the module:

```bash
python scripts/test_face_detection.py
```

## Production Deployment

For production deployment on actual buses:

1. Install the required dependencies on the on-vehicle computer
2. Connect a camera to the system
3. Configure the camera index in `camera_simulator.py` (default is 0)
4. Set the correct API endpoint URL
5. Run the camera system as a background service:
   ```bash
   python hardware/face_detection/camera_simulator.py <BUS_ID> 10 --camera
   ```

## Notes

- The current implementation uses MediaPipe's face detection model which works well in various lighting conditions
- The thresholds (LOW_THRESHOLD=10, MEDIUM_THRESHOLD=25) can be adjusted based on actual bus capacity
- For privacy, only face counts are transmitted, not actual images
- The system is designed to work with typical bus interior camera positioning
