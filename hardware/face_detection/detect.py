import cv2
import mediapipe as mp
import numpy as np
from typing import Tuple, Dict, Any
import base64

class FaceValidator:
    """Face detection and crowd analysis for bus occupancy monitoring."""
    
    # Crowd status thresholds (can be adjusted based on bus capacity)
    LOW_THRESHOLD = 10
    MEDIUM_THRESHOLD = 25
    
    def __init__(self, min_detection_confidence=0.5):
        """
        Initialize face detection with MediaPipe.
        
        Args:
            min_detection_confidence: Minimum confidence for face detection (0.0 to 1.0)
        """
        self.mp_face_detection = mp.solutions.face_detection
        self.detector = self.mp_face_detection.FaceDetection(
            model_selection=0, 
            min_detection_confidence=min_detection_confidence
        )
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.close()
        return False
    
    def close(self):
        """Explicitly close the detector and free resources."""
        if hasattr(self, 'detector') and self.detector:
            self.detector.close()
            self.detector = None

    def process_frame(self, frame) -> Tuple[bool, int]:
        """
        Process a single frame for face detection.
        
        Args:
            frame: OpenCV image frame (BGR format)
            
        Returns:
            Tuple of (faces_found: bool, face_count: int)
        """
        # Convert the BGR image to RGB
        frame.flags.writeable = False
        results = self.detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        # Count detections
        if results.detections:
            return True, len(results.detections)
        return False, 0
    
    def analyze_crowd(self, frame) -> Dict[str, Any]:
        """
        Analyze crowd density from camera frame.
        
        Args:
            frame: OpenCV image frame (BGR format)
            
        Returns:
            Dictionary with:
                - face_count: Number of faces detected
                - crowd_status: 'low', 'medium', 'high', or 'unknown'
                - confidence: Detection confidence
        """
        faces_found, face_count = self.process_frame(frame)
        
        # Determine crowd status based on face count
        if face_count == 0:
            crowd_status = "unknown"
            confidence = 0.0
        elif face_count <= self.LOW_THRESHOLD:
            crowd_status = "low"
            confidence = min(0.9, 0.7 + (face_count * 0.02))  # Scale with count
        elif face_count <= self.MEDIUM_THRESHOLD:
            crowd_status = "medium"
            confidence = min(0.95, 0.75 + (face_count * 0.01))
        else:
            crowd_status = "high"
            confidence = 0.95
        
        return {
            "face_count": face_count,
            "crowd_status": crowd_status,
            "confidence": confidence
        }
    
    def process_image_from_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Process image from raw bytes.
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            Dictionary with crowd analysis results
        """
        # Decode image from bytes
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return {
                "face_count": 0,
                "crowd_status": "unknown",
                "confidence": 0.0,
                "error": "Failed to decode image"
            }
        
        return self.analyze_crowd(frame)
    
    def process_image_from_base64(self, base64_string: str) -> Dict[str, Any]:
        """
        Process image from base64 encoded string.
        
        Args:
            base64_string: Base64 encoded image string
            
        Returns:
            Dictionary with crowd analysis results
        """
        try:
            # Remove data URL prefix if present
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            
            # Decode base64 to bytes
            image_bytes = base64.b64decode(base64_string)
            return self.process_image_from_bytes(image_bytes)
        except Exception as e:
            return {
                "face_count": 0,
                "crowd_status": "unknown",
                "confidence": 0.0,
                "error": f"Failed to process base64 image: {str(e)}"
            }
    
    def __del__(self):
        """Cleanup resources - fallback if close() not called explicitly."""
        try:
            self.close()
        except:
            # Silently ignore cleanup errors during garbage collection
            pass