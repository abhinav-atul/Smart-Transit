import cv2
import mediapipe as mp

class FaceValidator:
    def __init__(self):
        self.mp_face_detection = mp.solutions.face_detection
        self.detector = self.mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)

    def process_frame(self, frame):
        # Convert the BGR image to RGB
        frame.flags.writeable = False
        results = self.detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        # Draw detections
        if results.detections:
            return True, len(results.detections) # Valid face found
        return False, 0