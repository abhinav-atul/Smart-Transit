#!/usr/bin/env python3
"""
Test script for face detection crowd analysis module
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'hardware', 'face_detection'))

import cv2
import numpy as np
from detect import FaceValidator

def test_face_detection():
    """Test the face detection module with a generated test image."""
    print("🧪 Testing Face Detection Module\n")
    
    # Initialize detector
    detector = FaceValidator()
    print("✓ FaceValidator initialized successfully")
    
    # Test 1: Generate test image with simulated faces
    print("\n📝 Test 1: Processing test image...")
    height, width = 480, 640
    test_image = np.random.randint(50, 150, (height, width, 3), dtype=np.uint8)
    
    # Add some simple shapes to simulate faces
    for i in range(15):
        x = np.random.randint(50, width - 100)
        y = np.random.randint(50, height - 100)
        cv2.circle(test_image, (x, y), 25, (200, 180, 170), -1)
    
    result = detector.analyze_crowd(test_image)
    print(f"  Result: {result}")
    print(f"  ✓ Face count: {result['face_count']}")
    print(f"  ✓ Crowd status: {result['crowd_status']}")
    print(f"  ✓ Confidence: {result['confidence']:.2f}")
    
    # Test 2: Process from bytes
    print("\n📝 Test 2: Processing image from bytes...")
    _, buffer = cv2.imencode('.jpg', test_image)
    image_bytes = buffer.tobytes()
    
    result2 = detector.process_image_from_bytes(image_bytes)
    print(f"  Result: {result2}")
    print(f"  ✓ Successfully processed from bytes")
    
    # Test 3: Test crowd status thresholds
    print("\n📝 Test 3: Testing crowd status thresholds...")
    
    # Low crowd (0-10 faces)
    print(f"  Low threshold: ≤{detector.LOW_THRESHOLD} faces")
    print(f"  Medium threshold: ≤{detector.MEDIUM_THRESHOLD} faces")
    print(f"  High threshold: >{detector.MEDIUM_THRESHOLD} faces")
    
    # Test empty image
    empty_image = np.zeros((480, 640, 3), dtype=np.uint8)
    result3 = detector.analyze_crowd(empty_image)
    print(f"\n  Empty image: {result3['crowd_status']} ({result3['face_count']} faces)")
    assert result3['crowd_status'] == 'unknown', "Empty image should be 'unknown'"
    print("  ✓ Empty image test passed")
    
    print("\n✅ All tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_face_detection()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
