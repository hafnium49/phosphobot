import cv2
import sys
import time
import signal
import requests
import mediapipe as mp  # type: ignore
import numpy as np
import threading
from io import BytesIO

# Configurations
PI_IP: str = "127.0.0.1"
PI_PORT: int = 80

# Initialize MediaPipe Hand tracking
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7
)

# Video stream variables
latest_frame = None
stream_running = False


# Handle Ctrl+C to exit the program gracefully
def signal_handler(sig, frame):
    global stream_running
    print("\nExiting gracefully...")
    stream_running = False
    cv2.destroyAllWindows()
    hands.close()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def fetch_video_stream():
    """Fetch video frames from PhosphoBot API in a separate thread."""
    global latest_frame, stream_running
    camera_url = "http://localhost:80/video/0"
    
    while stream_running:
        try:
            response = requests.get(camera_url, stream=True, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Video stream error: {response.status_code}")
                time.sleep(1)
                continue
            
            # Parse the multipart MJPEG stream
            bytes_data = b''
            for chunk in response.iter_content(chunk_size=4096):
                if not stream_running:
                    break
                    
                bytes_data += chunk
                
                # Find frame boundaries in MJPEG stream
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
                            latest_frame = frame
                    except Exception as e:
                        continue
                        
                # Keep only recent data to prevent buffer buildup
                if len(bytes_data) > 100000:  # 100KB limit
                    bytes_data = bytes_data[-50000:]  # Keep last 50KB
                        
        except requests.RequestException as e:
            if stream_running:
                print(f"⚠️ Stream connection error: {e}")
                time.sleep(2)
        except Exception as e:
            print(f"❌ Stream processing error: {e}")
            time.sleep(1)


# Function to call the API
def call_to_api(endpoint: str, data: dict = {}):
    response = requests.post(f"http://{PI_IP}:{PI_PORT}/move/{endpoint}", json=data)
    return response.json()


def wave_motion():
    print("👋 Waving back!")
    points = 5
    for _ in range(2):
        for i in range(points):
            call_to_api(
                "absolute",
                {
                    "x": 0,
                    "y": 20 * (-1) ** i,  # Increased wave amplitude
                    "z": 30,              # Higher position
                    "rx": -90,
                    "ry": 0,
                    "rz": 0,
                    "open": i % 2 == 0,
                },
            )
            time.sleep(0.3)  # Slightly slower for better visibility


print("🚀 PHOSPHOBOT WAVE BACK EXAMPLE")
print("=" * 40)
print("📹 Using PhosphoBot video stream API")
print("👋 Wave your hand in front of the camera and the robot will wave back!")
print()

# Initialize robot
try:
    response = call_to_api("init")
    print("✅ Robot initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize robot: {e}")
    sys.exit(1)

# Start video stream
stream_running = True
stream_thread = threading.Thread(target=fetch_video_stream, daemon=True)
stream_thread.start()

# Wait for first frame
print("⏳ Waiting for video stream...")
timeout = 10
start_time = time.time()
while latest_frame is None and time.time() - start_time < timeout:
    time.sleep(0.1)

if latest_frame is None:
    print("❌ No video frames received. Check if PhosphoBot camera is working.")
    sys.exit(1)

print("✅ Video stream ready!")
print("🎮 Wave your hand to make the robot wave back")
print("⌨️ Press Ctrl+C to exit")

last_wave_time: float = 0
WAVE_COOLDOWN = 3

try:
    while stream_running:
        if latest_frame is None:
            time.sleep(0.01)
            continue
            
        # Work with current frame
        image = latest_frame.copy()
        
        # Flip the image horizontally for natural interaction
        image = cv2.flip(image, 1)

        results = hands.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

        current_time = time.time()
        if (
            results.multi_hand_landmarks
            and current_time - last_wave_time > WAVE_COOLDOWN
        ):
            wave_motion()
            last_wave_time = current_time

        # Add status overlay
        if results.multi_hand_landmarks:
            cv2.putText(image, "Hand detected! Robot waving...", 
                       (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            cv2.putText(image, "Wave your hand to make robot wave back", 
                       (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        # Add stream info
        cv2.putText(image, "PhosphoBot Wave Back", 
                   (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        cv2.imshow("Wave Back - PhosphoBot Stream", image)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("\nExiting gracefully...")
finally:
    stream_running = False
    cv2.destroyAllWindows()
    hands.close()
