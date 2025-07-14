import cv2
import time
import random
import requests
import numpy as np
import mediapipe as mp  # type: ignore
import threading

# Robot API Configuration
PI_IP = "127.0.0.1"
PI_PORT = 80


class RockPaperScissorsGame:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        # Video stream variables
        self.latest_frame = None
        self.stream_running = False
        
        self.gestures = {
            "rock": self.make_rock_gesture,
            "paper": self.make_paper_gesture,
            "scissors": self.make_scissors_gesture,
        }

    def find_available_video_channel(self):
        """Find the first available video channel."""
        print("🔍 Searching for available video channels...")
        for channel in range(10):  # Check channels 0-9
            try:
                print(f"  Testing channel {channel}...")
                response = requests.get(f"http://localhost/video/{channel}", timeout=3, stream=True)
                if response.status_code == 200:
                    print(f"✅ Found working video channel: {channel}")
                    response.close()  # Close the test connection
                    return channel
                else:
                    print(f"  Channel {channel}: HTTP {response.status_code}")
            except Exception as e:
                print(f"  Channel {channel}: failed ({e})")
                continue
        print("❌ No working video channels found")
        return None

    def capture_frame_from_stream(self):
        """Capture a single frame from PhosphoBot video stream."""
        # Find available video channel
        video_channel = self.find_available_video_channel()
        if video_channel is None:
            print("❌ No video channels found")
            return None
        
        camera_url = f"http://localhost/video/{video_channel}"
        print(f"📹 Using video channel: {video_channel}")
        
        try:
            response = requests.get(camera_url, stream=True, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Video stream error: {response.status_code}")
                return None
            
            print("📸 Capturing frame from video stream...")
            
            # Parse the multipart MJPEG stream to get a frame
            bytes_data = b''
            for chunk in response.iter_content(chunk_size=4096):
                bytes_data += chunk
                
                # Find frame boundaries in MJPEG stream
                start = bytes_data.find(b'\xff\xd8')  # JPEG start marker
                if start == -1:
                    continue
                    
                end = bytes_data.find(b'\xff\xd9', start)  # JPEG end marker
                if end == -1:
                    continue
                    
                # Extract JPEG frame
                jpg_data = bytes_data[start:end+2]
                
                # Convert to OpenCV image
                try:
                    nparr = np.frombuffer(jpg_data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if frame is not None and frame.size > 0:
                        print("✅ Frame captured successfully!")
                        return frame
                except Exception as e:
                    print(f"Frame decode error: {e}")
                    continue
                    
        except requests.RequestException as e:
            print(f"⚠️ Stream connection error: {e}")
            return None
        
        return None

    def call_to_api(self, endpoint: str, data: dict = {}):
        response = requests.post(f"http://{PI_IP}:{PI_PORT}/move/{endpoint}", json=data)
        return response.json()

    def detect_gesture(self, hand_landmarks):
        # Get relevant finger landmarks
        thumb_tip = hand_landmarks.landmark[4]
        index_tip = hand_landmarks.landmark[8]
        middle_tip = hand_landmarks.landmark[12]
        ring_tip = hand_landmarks.landmark[16]
        pinky_tip = hand_landmarks.landmark[20]

        # Get wrist position for reference
        wrist = hand_landmarks.landmark[0]

        # Calculate distances from wrist
        fingers_extended = []
        for tip in [thumb_tip, index_tip, middle_tip, ring_tip, pinky_tip]:
            distance = np.sqrt((tip.x - wrist.x) ** 2 + (tip.y - wrist.y) ** 2)
            fingers_extended.append(distance > 0.2)  # Threshold for extended fingers

        # Determine gesture
        if not any(fingers_extended[1:]):  # All fingers closed
            return "rock"
        elif all(fingers_extended):  # All fingers open
            return "paper"
        elif (
            fingers_extended[1]
            and fingers_extended[2]
            and not fingers_extended[3]
            and not fingers_extended[4]
        ):  # Only index and middle extended
            return "scissors"
        return None

    def make_rock_gesture(self):
        # Move to closed fist position
        self.call_to_api(
            "absolute",
            {"x": 0, "y": 0, "z": 5, "rx": 0, "ry": 0, "rz": 0, "open": 0},
        )

    def make_paper_gesture(self):
        # Move to open hand position
        self.call_to_api(
            "absolute",
            {"x": 0, "y": 0, "z": 5, "rx": 0, "ry": 0, "rz": 0, "open": 1},
        )

    def make_scissors_gesture(self):
        # Move to scissors position
        self.call_to_api(
            "absolute",
            {"x": 0, "y": 0, "z": 5, "rx": 0, "ry": -45, "rz": 0, "open": 0.5},
        )

    def move_up_down(self, times=3):
        for step in range(times + 1):
            self.call_to_api(
                "absolute",
                {"x": 0, "y": 0, "z": 4, "rx": 0, "ry": 0, "rz": 0, "open": 0},
            )
            time.sleep(0.25)
            self.call_to_api(
                "absolute",
                {"x": 0, "y": 0, "z": -4, "rx": 0, "ry": 0, "rz": 0, "open": 0},
            )
            time.sleep(0.25)
            print(times - step)

    def determine_winner(self, player_gesture, robot_gesture):
        if player_gesture == robot_gesture:
            return "Tie!"
        winners = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
        return (
            "Player wins!"
            if winners[player_gesture] == robot_gesture
            else "Robot wins!"
        )

    def play_game(self):
        print("🚀 PHOSPHOBOT ROCK PAPER SCISSORS")
        print("=" * 40)
        print("🎮 Get ready to play Rock Paper Scissors with the robot!")
        print()
        
        print("🔄 Initializing robot...")
        self.call_to_api("init")
        time.sleep(1)
        print("✅ Robot initialized!")

        print("\n🎯 Robot performing countdown...")
        self.move_up_down(times=3)

        print("\n📸 Capturing your gesture...")
        frame = self.capture_frame_from_stream()
        if frame is None:
            print("❌ Failed to capture image from video stream.")
            return

        # Process the frame for hand detection
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            player_gesture = self.detect_gesture(results.multi_hand_landmarks[0])

            if player_gesture:
                robot_gesture = random.choice(["rock", "paper", "scissors"])
                print(f"\n🎯 Player chose: {player_gesture}")
                print(f"🤖 Robot chose: {robot_gesture}")

                print(f"🤖 Robot making {robot_gesture} gesture...")
                self.gestures[robot_gesture]()  # Robot makes its gesture
                
                result = self.determine_winner(player_gesture, robot_gesture)
                print(f"\n🏆 {result}")
                time.sleep(2)
            else:
                print("❌ Gesture not detected. Please try again.")
        else:
            print("❌ No hand detected. Please try again.")

        print("\n✅ Game finished!")
        self.hands.close()


if __name__ == "__main__":
    game = RockPaperScissorsGame()
    game.play_game()
