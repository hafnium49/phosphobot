# PhosphoBot: Hand Tracking Example

Control your SO-101 robot using hand movements captured through the PhosphoBot video stream API with automatic video channel detection.

## Prerequisites

- Python 3.7+
- SO-101 robot with PhosphoBot server running on `localhost:80`
- Robot camera connected and accessible via PhosphoBot API
- Required Python packages (install via `pip install -r requirements.txt`)

## How It Works

This example uses MediaPipe to track your hand movements through the robot's camera feed and converts them to precise robot movements:

- **Automatic Video Channel Detection**: Scans available video channels (0-9) to find the active camera
- **Hand Position Tracking**: Your hand's X, Y position controls the robot's end-effector position
- **Height Control**: Your hand's vertical position (Y) maps to the robot's Z-axis (height)
- **Gripper Control**: Hand openness (thumb-to-finger distance) controls the gripper open/close state
- **Real-time Control**: Direct integration with PhosphoBot video stream API for responsive control

## Key Features

- **Dynamic Video Channel Discovery**: Automatically finds the correct video stream channel
- **PhosphoBot API Integration**: Uses the robot's video streaming and movement APIs
- **Real-time Hand Tracking**: Live hand detection with coordinate mapping to robot workspace
- **Robust Error Handling**: Graceful handling of connection issues and stream errors
- **Visual Feedback**: Live camera feed with hand tracking overlay and robot status information

## Setup

1. **Start PhosphoBot Server**: Make sure your SO-101 robot is powered on and the PhosphoBot server is running on `localhost:80`
2. **Install Dependencies**: Create a conda environment and install MediaPipe:
   ```bash
   conda create -n mediapipe-env python=3.11
   conda activate mediapipe-env
   pip install -r requirements.txt
   ```
3. **Automatic Camera Detection**: The application will automatically detect available video channels

## API Endpoints Used

- **Robot Connection**: `POST http://localhost:80/move/init` - Initialize robot connection
- **Robot Movement**: `POST http://localhost:80/move/absolute` - Control robot position with 6DOF
- **Video Stream**: `GET http://localhost/video/{channel}` - MJPEG video stream (auto-detected channel)

## Running the Application

1. **Start the Application**:
   ```bash
   conda activate mediapipe-env
   python hand_tracking.py
   ```

2. **Initialization Process**:
   - Robot server connection verification
   - Automatic video channel detection (tests channels 0-9)
   - MediaPipe hand tracking setup
   - Video stream connection establishment

3. **Operation**:
   - A window displays the live video feed with hand tracking overlay
   - Move your hand in front of the robot's camera to control movement
   - Hand position data and robot coordinates are displayed in real-time
   - The robot responds immediately to hand movements

4. **Exit**: Press 'q' in the video window to exit

## Example Output

```
🚀 PHOSPHOBOT HAND TRACKING
========================================
📹 Using PhosphoBot video stream API

🔧 Testing robot server connection...
✅ Robot server connected successfully
   Response: {'status': 'ok', 'message': None}

🔧 Testing video stream availability...
🔍 Searching for available video channels...
  Testing channel 0...
  Channel 0: HTTP 404
  Testing channel 1...
  Channel 1: HTTP 404
  Testing channel 4...
✅ Found working video channel: 4
✅ Video stream is available on channel 4

🎯 Initializing hand tracker...
✅ Video stream connected!
✅ Video stream ready! Starting hand tracking...
🎮 Move your hands in front of the robot's camera
```

## Control Mapping

- **X Position**: Hand left/right → Robot left/right (-100 to +100 cm)
- **Y Position**: Hand forward/back → Robot forward/back (-100 to +100 cm) 
- **Z Position**: Hand up/down → Robot height (0 to 100 cm with 50cm offset)
- **Gripper**: Hand openness → Gripper state (0.0 = closed, 1.0 = open)

## Features

- **Automatic Video Channel Detection**: Finds working video stream without manual configuration
- **Real-time Hand Detection**: Uses MediaPipe for accurate hand landmark detection with TensorFlow Lite
- **PhosphoBot Integration**: Direct connection to robot's camera and movement APIs via HTTP
- **Responsive Control**: Low-latency movement commands with visual feedback overlay
- **Intelligent Coordinate Mapping**: Maps hand position to robot workspace coordinates
- **Natural Gripper Control**: Hand gesture recognition for gripper open/close
- **Robust Error Handling**: Automatic connection recovery and stream error management
- **Multi-threaded Processing**: Separate video stream thread for optimal performance

## Troubleshooting

### Connection Issues
- **"Failed to connect to server"**: Check that PhosphoBot server is running on `localhost:80`
- **"No working video channels found"**: Verify robot camera is connected and PhosphoBot server has camera access
- **Robot initialization fails**: Check robot power and PhosphoBot server status

### Video Stream Issues
- **404 errors on video channels**: The camera may be on a different channel - the app will auto-detect
- **Stream connection errors**: Check network connectivity to the robot
- **No video frames received**: Verify camera hardware connection

### Hand Tracking Issues
- **Hand not detected**: Ensure good lighting and keep hand within camera frame
- **Laggy movement**: Check network latency or adjust MediaPipe confidence thresholds
- **Inaccurate tracking**: Improve lighting conditions or adjust detection parameters

### Robot Control Issues
- **Robot not responding**: Check robot initialization status and movement API responses
- **Erratic movements**: Verify coordinate mapping ranges and hand tracking stability

## Technical Details

### Video Stream Processing
- **Format**: MJPEG stream with automatic frame boundary detection
- **Channel Detection**: Tests GET requests to channels 0-9 to find active camera
- **Parsing**: Real-time JPEG frame extraction from multipart HTTP stream
- **Buffer Management**: Automatic cleanup to prevent memory buildup
- **Error Recovery**: Automatic reconnection on stream failures

### Hand Detection Configuration
- **MediaPipe Setup**:
  - `static_image_mode=False` for video processing
  - `max_num_hands=2` for dual hand detection
  - `min_detection_confidence=0.7` for reliable detection
  - `min_tracking_confidence=0.7` for stable tracking
- **Coordinate Processing**: Hand landmarks converted to robot workspace coordinates
- **Gripper Algorithm**: Thumb-to-index distance calculation for open/close state

### Robot Integration
- **Movement API**: Uses absolute positioning with 6DOF control (x, y, z, rx, ry, rz)
- **Coordinate System**: Robot workspace coordinates in centimeters
- **Real-time Updates**: Continuous movement commands based on hand position
- **Safety Features**: Coordinate range limiting and error handling

## Customization

### Coordinate Mapping
Modify the hand position to robot coordinate conversion:
```python
# In the HandTracker class, adjust these mappings:
robot_x = (hand_x - 0.5) * 200  # X range: -100 to +100 cm
robot_y = (hand_y - 0.5) * 200  # Y range: -100 to +100 cm  
robot_z = hand_z * 100 + 50     # Z range: 50 to 150 cm
```

### Hand Detection Sensitivity
Adjust MediaPipe parameters for different conditions:
```python
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,                    # Number of hands to detect
    min_detection_confidence=0.7,       # Detection threshold (0.0-1.0)
    min_tracking_confidence=0.7         # Tracking threshold (0.0-1.0)
)
```

### Gripper Control
Modify the hand openness calculation:
```python
def calculate_hand_open_state(self, hand_landmarks):
    # Adjust the sensitivity multiplier and threshold
    openess = 1 - max(0, min(1, 1 - distance * 3))  # Sensitivity: *3
    return 0 if openess < 0.25 else openess          # Threshold: 0.25
```

### Video Channel Detection
Customize the channel search range:
```python
def find_available_video_channel(self):
    for channel in range(10):  # Check channels 0-9 (modify as needed)
        # Test each channel...
```

### Movement Timing
Adjust the control loop timing:
```python
if cv2.waitKey(5) & 0xFF == ord("q"):  # 5ms delay (modify for responsiveness)
```

## Dependencies

See `requirements.txt` for complete list:
- `mediapipe` - Hand tracking and pose estimation
- `opencv-python` - Computer vision and image processing  
- `numpy` - Numerical computations
- `requests` - HTTP client for API communication
