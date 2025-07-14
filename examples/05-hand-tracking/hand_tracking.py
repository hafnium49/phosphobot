import cv2
import requests  # type: ignore
import numpy as np
import mediapipe as mp  # type: ignore
import threading
import time
from io import BytesIO

# TODO: estimate depth using the stero camera


class HandTracker:
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
        
        # Video stream variables
        self.latest_frame = None
        self.stream_running = False
        self.camera_url = "http://localhost:80/video/0"  # Use camera 0 which is available

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
        # Prepare text
        overlay_text = f"X: {x:.3f} Y: {y:.3f} Z: {z:.3f} Open: {open:.2f}"

        # Add background rectangle
        cv2.rectangle(image, (10, 50), (550, 90), (255, 255, 255), -1)

        # Add text
        cv2.putText(
            image, overlay_text, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2
        )

        return image

    def fetch_video_stream(self):
        """Fetch video frames from PhosphoBot API in a separate thread."""
        print("🔗 Connecting to PhosphoBot video stream...")
        
        while self.stream_running:
            try:
                response = requests.get(self.camera_url, stream=True, timeout=10)
                
                if response.status_code != 200:
                    print(f"❌ Video stream error: {response.status_code}")
                    time.sleep(1)
                    continue
                
                print("✅ Video stream connected!")
                
                # Parse the multipart MJPEG stream
                bytes_data = b''
                for chunk in response.iter_content(chunk_size=4096):
                    if not self.stream_running:
                        break
                        
                    bytes_data += chunk
                    
                    # Find frame boundaries in MJPEG stream
                    # Look for --frame boundary or JPEG markers
                    while True:
                        start = bytes_data.find(b'\xff\xd8')  # JPEG start marker
                        if start == -1:
                            break
                            
                        end = bytes_data.find(b'\xff\xd9', start)  # JPEG end marker
                        if end == -1:
                            break
                            
                        # Extract JPEG frame
                        jpg_data = bytes_data[start:end+2]
                        bytes_data = bytes_data[end+2:]
                        
                        # Convert to OpenCV image
                        try:
                            nparr = np.frombuffer(jpg_data, np.uint8)
                            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                            
                            if frame is not None and frame.size > 0:
                                self.latest_frame = frame
                        except Exception as e:
                            print(f"Frame decode error: {e}")
                            continue
                            
                    # Keep only recent data to prevent buffer buildup
                    if len(bytes_data) > 100000:  # 100KB limit
                        bytes_data = bytes_data[-50000:]  # Keep last 50KB
                            
            except requests.RequestException as e:
                if self.stream_running:  # Only print if we're still supposed to be running
                    print(f"⚠️ Stream connection error: {e}")
                    time.sleep(2)
            except Exception as e:
                print(f"❌ Stream processing error: {e}")
                time.sleep(1)

    def track_hand(self):
        """Track hands using PhosphoBot video stream."""
        print("🎯 Starting hand tracking with PhosphoBot video stream...")
        
        # Start video stream in background thread
        self.stream_running = True
        stream_thread = threading.Thread(target=self.fetch_video_stream, daemon=True)
        stream_thread.start()
        
        # Wait for first frame
        print("⏳ Waiting for video frames...")
        timeout = 10
        start_time = time.time()
        while self.latest_frame is None and time.time() - start_time < timeout:
            time.sleep(0.1)
            
        if self.latest_frame is None:
            print("❌ No video frames received. Check if PhosphoBot camera is working.")
            return
            
        print("✅ Video stream ready! Starting hand tracking...")
        print("🎮 Move your hands in front of the robot's camera")
        print("⌨️ Press 'q' to quit")

        try:
            while self.stream_running:
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
                    # Use the first detected hand for control
                    hand_landmarks = results.multi_hand_landmarks[0]
                    
                    # Draw landmarks on the image
                    self.mp_drawing.draw_landmarks(
                        image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
                    )

                    # Extract hand position (using wrist as reference)
                    wrist = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST]

                    # Calculate hand data from first detected hand  
                    hand_data = {
                        "x": (wrist.x - 0.5) * 200,    # Map to -100 to +100 range
                        "y": (0.5 - wrist.y) * 200,    # Map to -100 to +100 range, inverted
                        "z": 50 + (0.5 - wrist.y) * 100,  # Map to 0-100 range with offset
                        "open": self.calculate_hand_open_state(hand_landmarks)
                    }

                    # Send data to robot
                    try:
                        self.add_hand_data_overlay(
                            image,
                            hand_data["x"]/100,  # Display normalized values
                            hand_data["y"]/100,
                            hand_data["z"]/100,
                            hand_data["open"],
                        )

                        # Send movement command to robot
                        response = requests.post(
                            "http://localhost:80/move/absolute",
                            json=hand_data,
                            timeout=0.2,  # Short timeout for responsiveness
                        )
                        
                        # Add debug info
                        debug_text = f"Sending: X={hand_data['x']:.1f} Y={hand_data['y']:.1f} Z={hand_data['z']:.1f}"
                        cv2.putText(image, debug_text, 
                                  (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                        
                        # Add success indicator
                        if response.status_code == 200:
                            cv2.putText(image, "ROBOT FOLLOWING ✓", 
                                      (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                        else:
                            cv2.putText(image, f"Robot Error: {response.status_code}", 
                                      (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                            
                    except requests.RequestException as e:
                        cv2.putText(image, f"Connection Error", 
                                  (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                        print(f"Failed to send data: {e}")
                else:
                    # No hands detected
                    cv2.putText(image, "Show your hand to control robot", 
                              (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

                # Add stream info overlay
                cv2.putText(image, "PhosphoBot Video Stream", 
                          (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                # Display the image
                cv2.imshow("Hand Tracking - PhosphoBot Stream", image)

                # Break loop on 'q' key press
                if cv2.waitKey(5) & 0xFF == ord("q"):
                    break
                    
        except KeyboardInterrupt:
            print("\n🛑 Hand tracking stopped by user")
        except Exception as e:
            print(f"❌ Hand tracking error: {e}")
        finally:
            # Clean up
            self.stream_running = False
            cv2.destroyAllWindows()
            print("✅ Hand tracking stopped")


def main():
    print("🚀 PHOSPHOBOT HAND TRACKING")
    print("=" * 40)
    print("📹 Using PhosphoBot video stream API")
    print()
    
    # Test robot server connection
    print("🔧 Testing robot server connection...")
    try:
        response = requests.post("http://localhost:80/move/init", timeout=5)
        if response.status_code == 200:
            print("✅ Robot server connected successfully")
            print(f"   Response: {response.json()}")
        else:
            print(f"⚠️ Robot server responded with status: {response.status_code}")
    except requests.RequestException as e:
        print(f"❌ Failed to connect to robot server: {e}")
        print("   Make sure PhosphoBot is running on localhost:80")
        return
    
    # Test video stream availability
    print("\n🔧 Testing video stream availability...")
    try:
        response = requests.get("http://localhost:80/video/0", stream=True, timeout=5)
        if response.status_code == 200:
            print("✅ Video stream is available")
        else:
            print(f"❌ Video stream error: {response.status_code}")
            return
    except requests.RequestException as e:
        print(f"❌ Failed to connect to video stream: {e}")
        return

    print("\n🎯 Initializing hand tracker...")
    tracker = HandTracker()
    tracker.track_hand()


if __name__ == "__main__":
    main()
