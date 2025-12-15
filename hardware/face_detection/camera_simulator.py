"""
Camera Simulator for Bus Crowd Monitoring
Simulates periodic camera captures from on-vehicle camera system
"""

import cv2
import numpy as np
import requests
import time
import base64
from datetime import datetime
from detect import FaceValidator

# Configuration
API_BASE_URL = "http://localhost:8000"
CAPTURE_INTERVAL = 10  # seconds between captures
BUS_ID = "BUS-01"  # Default bus ID (can be passed as argument)


def generate_test_image(num_faces=15):
    """
    Generate a test image with simulated faces for testing.
    In production, this would capture from actual camera.
    
    Args:
        num_faces: Number of faces to simulate (for testing)
        
    Returns:
        OpenCV image frame
    """
    # Create a blank image (simulating bus interior)
    height, width = 480, 640
    img = np.random.randint(50, 150, (height, width, 3), dtype=np.uint8)
    
    # Add some rectangles to simulate seated passengers
    for i in range(num_faces):
        x = np.random.randint(50, width - 100)
        y = np.random.randint(50, height - 100)
        cv2.rectangle(img, (x, y), (x + 80, y + 100), (100, 100, 150), -1)
        # Add a circle for head
        cv2.circle(img, (x + 40, y + 30), 25, (200, 180, 170), -1)
    
    return img


def capture_from_camera(camera_index=0):
    """
    Capture image from actual camera device.
    
    Args:
        camera_index: Camera device index (0 for default camera)
        
    Returns:
        OpenCV image frame or None if capture fails
    """
    try:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print(f"⚠️  Could not open camera {camera_index}")
            return None
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            return frame
        else:
            print("⚠️  Failed to capture frame from camera")
            return None
    except Exception as e:
        print(f"⚠️  Camera error: {e}")
        return None


def encode_image_to_base64(frame):
    """
    Encode OpenCV image frame to base64 string.
    
    Args:
        frame: OpenCV image frame
        
    Returns:
        Base64 encoded string
    """
    _, buffer = cv2.imencode('.jpg', frame)
    image_base64 = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{image_base64}"


def send_crowd_data(bus_id, face_count, crowd_status):
    """
    Send crowd analysis data to backend API.
    
    Args:
        bus_id: Bus identifier
        face_count: Number of faces detected
        crowd_status: Crowd level (low/medium/high)
    """
    try:
        endpoint = f"{API_BASE_URL}/crowd-status"
        payload = {
            "vehicle_id": bus_id,
            "passenger_count": face_count,
            "crowd_status": crowd_status,
            "timestamp": datetime.now().isoformat()
        }
        
        response = requests.post(endpoint, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"✅ Crowd data sent: {bus_id} - {crowd_status} ({face_count} people)")
        else:
            print(f"⚠️  API error: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send data: {e}")


def simulate_camera_system(bus_id=BUS_ID, interval=CAPTURE_INTERVAL, use_real_camera=False):
    """
    Main simulation loop for camera system.
    
    Args:
        bus_id: Bus identifier
        interval: Seconds between captures
        use_real_camera: If True, attempt to use real camera; otherwise use test images
    """
    print(f"🎥 Camera Simulator Started")
    print(f"   Bus ID: {bus_id}")
    print(f"   Capture Interval: {interval}s")
    print(f"   Camera Mode: {'Real' if use_real_camera else 'Simulated'}")
    print(f"   Press Ctrl+C to stop\n")
    
    # Initialize face detector
    detector = FaceValidator()
    
    capture_count = 0
    
    try:
        while True:
            capture_count += 1
            print(f"\n📸 Capture #{capture_count} at {datetime.now().strftime('%H:%M:%S')}")
            
            # Capture image
            if use_real_camera:
                frame = capture_from_camera()
                if frame is None:
                    print("   Falling back to test image...")
                    # Simulate varying crowd levels
                    num_faces = np.random.randint(5, 35)
                    frame = generate_test_image(num_faces)
            else:
                # Simulate varying crowd levels
                num_faces = np.random.randint(5, 35)
                frame = generate_test_image(num_faces)
                print(f"   Generated test image (simulated faces: ~{num_faces})")
            
            # Analyze crowd
            result = detector.analyze_crowd(frame)
            
            print(f"   Detected faces: {result['face_count']}")
            print(f"   Crowd status: {result['crowd_status'].upper()}")
            print(f"   Confidence: {result['confidence']:.2f}")
            
            # Send data to backend
            send_crowd_data(bus_id, result['face_count'], result['crowd_status'])
            
            # Wait for next capture
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Camera simulator stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        print("👋 Shutting down...")


if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    bus_id = sys.argv[1] if len(sys.argv) > 1 else BUS_ID
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else CAPTURE_INTERVAL
    use_camera = "--camera" in sys.argv
    
    simulate_camera_system(bus_id, interval, use_camera)
