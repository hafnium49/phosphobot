#!/usr/bin/env python3
"""
Hand tracking script that handles camera access conflicts gracefully
"""

import cv2
import requests
import numpy as np
import mediapipe as mp
import os
import sys

class RobustHandTracker:
    def __init__(self):
        # MediaPipe hand tracking setup
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        self.left_hand_z = 0

    def calculate_hand_open_state(self, hand_landmarks):
        """Calculate hand open state based on thumb and finger tip distances."""
        thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
        index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]

        openess = 1 - max(
            0,
            min(
                1,
                1
                - np.sqrt(
                    (thumb_tip.x - index_tip.x) ** 2
                    + (thumb_tip.y - index_tip.y) ** 2
                    + (thumb_tip.z - index_tip.z) ** 2
                )
                * 3,
            ),
        )

        return 0 if openess < 0.25 else openess

    def add_hand_data_overlay(self, image, x, y, z, open):
        """Add overlay with hand tracking data."""
        overlay_text = f"X: {x:.3f} Y: {y:.3f} Z: {z:.3f} Open: {open:.2f}"
        cv2.rectangle(image, (10, 30), (550, 70), (255, 255, 255), -1)
        cv2.putText(
            image, overlay_text, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2
        )
        return image

    def try_multiple_camera_sources(self):
        """Try different camera access methods"""
        print("🔍 Searching for available camera sources...")
        
        # Method 1: Try different camera indices
        for camera_id in range(5):  # Try cameras 0-4
            print(f"   📷 Trying camera index {camera_id}...")
            cap = cv2.VideoCapture(camera_id)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"   ✅ Found working camera at index {camera_id}")
                    return cap
                cap.release()
        
        # Method 2: Try different backends
        backends = [
            (cv2.CAP_V4L2, "V4L2"),
            (cv2.CAP_GSTREAMER, "GStreamer"),
            (cv2.CAP_FFMPEG, "FFmpeg")
        ]
        
        for backend_id, backend_name in backends:
            print(f"   🔧 Trying {backend_name} backend...")
            for camera_id in range(2):
                try:
                    cap = cv2.VideoCapture(camera_id, backend_id)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            print(f"   ✅ Success with {backend_name} backend on camera {camera_id}")
                            return cap
                    cap.release()
                except:
                    continue
        
        print("   ❌ No accessible camera found")
        return None

    def track_hand(self):
        """Open video capture and continuously track hand position."""
        print("🚀 Starting Enhanced Hand Tracking...")
        print("=" * 50)
        
        # Test server connection first
        try:
            response = requests.post("http://localhost:80/move/init", timeout=2)
            print(f"✅ Robot server connected: {response.json()}")
        except requests.RequestException as e:
            print(f"⚠️ Robot server connection failed: {e}")
            print("   Continuing in demo mode (no robot commands will be sent)")
        
        # Try to get camera access
        cap = self.try_multiple_camera_sources()
        
        if cap is None:
            print("\n❌ CAMERA ACCESS SOLUTION:")
            print("   The camera is currently in use by the phosphobot process.")
            print("   Options:")
            print("   1. Stop the phosphobot process: sudo pkill phosphobot")
            print("   2. Use the robot's web interface for hand tracking")
            print("   3. Connect an additional USB camera")
            print("\n   Running in DEMO MODE with synthetic data...")
            self.demo_mode()
            return
            
        print(f"✅ Camera successfully opened!")
        print("🎮 Move your hands in front of the camera")
        print("⌨️ Press 'q' to quit")
        
        try:
            while cap.isOpened():
                success, image = cap.read()
                if not success:
                    print("Ignoring empty camera frame.")
                    continue

                # Flip the image horizontally
                image = cv2.flip(image, 1)

                # Convert the BGR image to RGB
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

                # Process the image and find hands
                results = self.hands.process(image_rgb)

                # Reset left hand z
                self.left_hand_z = 0

                # Draw hand landmarks and send position
                if results.multi_hand_landmarks:
                    hand_data = {"rx": 0, "ry": 0, "rz": 0}

                    for hand_index, hand_landmarks in enumerate(results.multi_hand_landmarks):
                        # Draw landmarks on the image
                        self.mp_drawing.draw_landmarks(
                            image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
                        )

                        # Extract hand position (using wrist as reference)
                        wrist = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST]

                        # Identify hand side (uses handedness if available)
                        if results.multi_handedness:
                            handedness = results.multi_handedness[hand_index]
                            if handedness.classification[0].label == "Left":
                                hand_data["x"] = -wrist.y + 0.65
                            else:
                                hand_data["y"] = 0 - wrist.x + 0.525
                                hand_data["z"] = 0 - wrist.y + 0.65
                                hand_data["open"] = self.calculate_hand_open_state(hand_landmarks)

                    # Send data to endpoint
                    if all(key in hand_data for key in ["x", "y", "z", "open"]):
                        try:
                            self.add_hand_data_overlay(
                                image,
                                hand_data["x"],
                                hand_data["y"],
                                hand_data["z"],
                                hand_data["open"],
                            )

                            requests.post(
                                "http://localhost:80/move/absolute",
                                json={
                                    **hand_data,
                                    "x": hand_data["x"] * 100,
                                    "y": hand_data["y"] * 100,
                                    "z": hand_data["z"] * 100,
                                },
                                timeout=0.2,
                            )
                        except requests.RequestException:
                            # Silently continue if server not available
                            pass
                    else:
                        cv2.putText(image, "Show both hands for control", 
                                  (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

                # Display the image
                cv2.imshow("Hand Tracking", image)

                # Break loop on 'q' key press
                if cv2.waitKey(5) & 0xFF == ord("q"):
                    break

        except Exception as e:
            print(f"❌ Error during hand tracking: {e}")
        finally:
            # Clean up
            if cap:
                cap.release()
            cv2.destroyAllWindows()

    def demo_mode(self):
        """Run in demo mode without camera"""
        print("\n🎭 DEMO MODE: Simulating hand tracking...")
        
        # Create a demo window
        demo_image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        try:
            for i in range(50):  # 50 demo frames
                demo_image.fill(0)
                
                # Add demo text
                cv2.putText(demo_image, "HAND TRACKING DEMO MODE", 
                          (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(demo_image, "Camera in use by robot process", 
                          (120, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                cv2.putText(demo_image, f"Demo frame: {i+1}/50", 
                          (200, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(demo_image, "Press 'q' to quit", 
                          (220, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
                
                # Show demo window
                cv2.imshow("Hand Tracking Demo", demo_image)
                
                if cv2.waitKey(100) & 0xFF == ord("q"):
                    break
                    
        except Exception as e:
            print(f"Demo mode error: {e}")
        finally:
            cv2.destroyAllWindows()
            print("✅ Demo completed")


def main():
    print("🎯 ROBUST HAND TRACKING SYSTEM")
    print("=" * 40)
    
    # Suppress some OpenCV warnings
    os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
    
    tracker = RobustHandTracker()
    tracker.track_hand()


if __name__ == "__main__":
    main()
