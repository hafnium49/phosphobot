#!/usr/bin/env python3
"""
Modified hand tracking script that uses the robot's camera API
instead of direct camera access
"""

import cv2
import requests
import numpy as np
import mediapipe as mp
import time
from threading import Thread
import io

class RobotCameraHandTracker:
    def __init__(self, camera_url="http://localhost:80/video/0"):
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
        self.camera_url = camera_url
        self.latest_frame = None
        self.running = False
        
    def fetch_camera_frames(self):
        """Fetch frames from robot camera API in a separate thread"""
        try:
            print(f"🔗 Connecting to camera stream: {self.camera_url}")
            response = requests.get(self.camera_url, stream=True, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Camera stream error: {response.status_code}")
                return
                
            print("✅ Camera stream connected!")
            
            # Parse multipart stream
            boundary = None
            for line in response.iter_lines():
                if not self.running:
                    break
                    
                line = line.decode('utf-8', errors='ignore')
                
                if line.startswith('--frame'):
                    boundary = line
                elif line.startswith('Content-Type: image/jpeg'):
                    # Next should be the image data
                    continue
                elif line == '':
                    # Empty line indicates start of image data
                    # Read until next boundary
                    img_data = b''
                    while self.running:
                        chunk = response.raw.read(1024)
                        if not chunk:
                            break
                        if b'--frame' in chunk:
                            # Find where the boundary starts
                            boundary_pos = chunk.find(b'--frame')
                            img_data += chunk[:boundary_pos]
                            break
                        img_data += chunk
                    
                    if img_data:
                        # Convert to OpenCV image
                        nparr = np.frombuffer(img_data, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            self.latest_frame = frame
                            
        except Exception as e:
            print(f"❌ Camera fetch error: {e}")

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

    def track_hand(self):
        """Track hands using robot camera API"""
        print("🎯 Starting hand tracking with robot camera...")
        
        # Start camera feed in background thread
        self.running = True
        camera_thread = Thread(target=self.fetch_camera_frames, daemon=True)
        camera_thread.start()
        
        # Wait for first frame
        print("⏳ Waiting for camera frames...")
        timeout = 10
        start_time = time.time()
        while self.latest_frame is None and time.time() - start_time < timeout:
            time.sleep(0.1)
            
        if self.latest_frame is None:
            print("❌ No camera frames received within timeout")
            return
            
        print("✅ Camera frames received! Starting hand tracking...")
        
        try:
            while self.running:
                if self.latest_frame is None:
                    time.sleep(0.01)
                    continue
                    
                # Work with current frame
                image = self.latest_frame.copy()
                
                # Flip the image horizontally for natural interaction
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
                        except requests.RequestException as e:
                            print(f"Failed to send data: {e}")
                    else:
                        # Add status overlay
                        cv2.putText(image, "Waiting for hand detection...", 
                                  (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

                # Add frame info
                cv2.putText(image, "Robot Camera Hand Tracking", 
                          (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                # Display the image
                cv2.imshow("Robot Hand Tracking", image)

                # Break loop on 'q' key press
                if cv2.waitKey(5) & 0xFF == ord("q"):
                    break
                    
        except KeyboardInterrupt:
            print("\\n🛑 Hand tracking stopped by user")
        except Exception as e:
            print(f"❌ Hand tracking error: {e}")
        finally:
            self.running = False
            cv2.destroyAllWindows()


def main():
    print("🚀 ROBOT CAMERA HAND TRACKING")
    print("=" * 40)
    
    # Test server connection
    try:
        response = requests.post("http://localhost:80/move/init", timeout=5)
        print(f"✅ Robot server connected: {response.json()}")
    except requests.RequestException as e:
        print(f"❌ Failed to connect to robot server: {e}")
        return

    # Test camera availability
    try:
        response = requests.get("http://localhost:80/video/0", stream=True, timeout=5)
        if response.status_code == 200:
            print("✅ Robot camera stream available")
        else:
            print(f"❌ Camera stream error: {response.status_code}")
            return
    except requests.RequestException as e:
        print(f"❌ Failed to connect to camera: {e}")
        return

    print("\\n🎯 Starting hand tracking...")
    print("📹 Using robot's camera API instead of direct access")
    print("🎮 Move your hands in front of the camera to control the robot")
    print("⌨️  Press 'q' to quit")
    print()

    tracker = RobotCameraHandTracker()
    tracker.track_hand()


if __name__ == "__main__":
    main()
