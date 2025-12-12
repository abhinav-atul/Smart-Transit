import cv2
import numpy as np

class CrowdAnalyzer:
    def __init__(self):
        # Use standard frontal face detector included in OpenCV
        self.cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.cascade = cv2.CascadeClassifier(self.cascade_path)

    async def analyze(self, image_bytes):
        try:
            # 1. Decode Image
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return 0, "Error", "None"

            # 2. Convert to Grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 3. Detect Faces
            # ScaleFactor 1.1 = 10% reduction per pass
            # MinNeighbors 5 = Higher quality detection threshold
            faces = self.cascade.detectMultiScale(gray, 1.1, 5)
            count = len(faces)

            # 4. Determine Density Level
            if count <= 2:
                level = "GREEN (Empty)"
            elif count <= 8:
                level = "ORANGE (Standing)"
            else:
                level = "RED (Crowded)"

            return count, level, "High"

        except Exception as e:
            print(f"CV Error: {e}")
            return 0, "Processing Error", "Low"

crowd_service = CrowdAnalyzer()