# PhosphoBot: Wave Back Example

This example demonstrates a robot that waves back when it detects a hand using the PhosphoBot video stream API.

## Prerequisites

- Python 3.6+
- PhosphoBot server running on the robot
- MediaPipe for hand detection
- Required Python packages (install via `pip install -r requirements.txt`)

## How It Works

The application uses MediaPipe for hand detection through the PhosphoBot video stream API:

1. **Automatic Video Channel Detection**: Scans available video channels (0-9) to find the active camera
2. **Real-time Hand Tracking**: Uses MediaPipe to detect hands in the video stream
3. **Robot Wave Motion**: When a hand is detected, the robot performs a waving motion
4. **Cooldown Protection**: A 3-second cooldown prevents excessive waving

## Key Features

- **Dynamic Video Channel Discovery**: Automatically finds the correct video stream channel
- **PhosphoBot API Integration**: Uses the robot's video streaming and movement APIs
- **Real-time Processing**: Live hand detection with visual feedback
- **Robust Error Handling**: Graceful handling of connection issues and stream errors

## Configuration

The script `wave_hand.py` contains configurable parameters:

```python
PI_IP: str = "127.0.0.1"  # IP address of the robot (default: localhost)
PI_PORT: int = 80         # Port of the robot's API server
WAVE_COOLDOWN = 3         # Seconds between wave motions
```

## API Endpoints Used

- **Robot Movement**: `POST http://localhost:80/move/init` - Initialize robot
- **Robot Movement**: `POST http://localhost:80/move/absolute` - Control robot position
- **Video Stream**: `GET http://localhost/video/{channel}` - MJPEG video stream (auto-detected channel)

## Wave Motion Details

The robot performs a waving motion with these characteristics:
- **Position**: x=0, z=30 (elevated position)
- **Rotation**: rx=-90° (arm extended)
- **Wave Pattern**: y-axis oscillation between +20 and -20
- **Gripper Action**: Opens and closes during wave
- **Duration**: 2 cycles of 5 points each, 0.3s per movement

## Setup

1. **Start PhosphoBot Server**: Ensure the robot is powered on and the PhosphoBot server is running
2. **Install Dependencies**: 
   ```bash
   pip install -r requirements.txt
   ```
3. **Verify Camera Access**: The application will automatically detect available video channels

## Running the Application

1. **Start the Application**:
   ```bash
   python wave_hand.py
   ```

2. **Initialization Process**:
   - Robot initialization and MediaPipe setup
   - Automatic video channel detection (tests channels 0-9)
   - Video stream connection establishment

3. **Operation**:
   - A window displays the live video feed with status overlay
   - Wave your hand in front of the camera to trigger the robot
   - The robot will wave back and show "Hand detected! Robot waving..." message
   - Wait for the 3-second cooldown before the next wave

4. **Exit**: Press Ctrl+C in the terminal or 'q' in the video window to exit

## Example Output

```
🚀 PHOSPHOBOT WAVE BACK EXAMPLE
========================================
📹 Using PhosphoBot video stream API
👋 Wave your hand in front of the camera and the robot will wave back!

🔄 Initializing robot...
✅ Robot initialized successfully: {'status': 'ok', 'message': None}
🎥 Starting video stream...
🔍 Searching for available video channels...
  Testing channel 0...
  Channel 0: HTTP 404
  Testing channel 1...
  Channel 1: HTTP 404
  Testing channel 4...
✅ Found working video channel: 4
📹 Using video channel: 4
✅ Video stream ready!
🎮 Wave your hand to make the robot wave back
⌨️ Press Ctrl+C to exit
```

## Troubleshooting

### Video Stream Issues
- **No video channels found**: Verify PhosphoBot server is running and camera is connected
- **404 errors on video channels**: The camera may be on a different channel - the app will auto-detect
- **Stream connection errors**: Check network connectivity to the robot

### Hand Detection Issues
- **Robot doesn't wave**: Ensure your hand is clearly visible and well-lit in the camera frame
- **Frequent false triggers**: Adjust lighting or MediaPipe detection confidence
- **No detection**: Check if MediaPipe is properly installed and TensorFlow Lite is working

### Robot Control Issues
- **Robot init fails**: Verify the robot server is accessible at the configured IP/port
- **Movement errors**: Check if the robot is properly calibrated and has sufficient power

### Performance Tips
- Ensure good lighting for optimal hand detection
- Keep hand movements clear and deliberate
- Avoid background motion that might trigger false detections

## Technical Details

### Video Stream Processing
- **Format**: MJPEG stream with frame boundary detection
- **Parsing**: Real-time JPEG frame extraction from multipart stream
- **Buffer Management**: Automatic cleanup to prevent memory buildup
- **Error Recovery**: Automatic reconnection on stream failures

### Hand Detection
- **MediaPipe Configuration**:
  - `static_image_mode=False` for video processing
  - `max_num_hands=1` for single hand detection
  - `min_detection_confidence=0.7` for reliable detection
- **Frame Processing**: RGB conversion and horizontal flip for natural interaction
- **Coordinate Mapping**: Direct landmark detection without coordinate transformation

### Robot Integration
- **Movement API**: Uses absolute positioning with 6DOF control (x, y, z, rx, ry, rz)
- **Gripper Control**: Synchronized open/close during wave motion
- **Safety Features**: Cooldown timer prevents excessive movement commands

## Customization

### Wave Motion Pattern
Modify the `wave_motion()` function to change the wave behavior:
```python
def wave_motion():
    points = 5  # Number of wave points
    for _ in range(2):  # Number of wave cycles
        for i in range(points):
            call_to_api("absolute", {
                "x": 0,                    # Forward/backward position
                "y": 20 * (-1) ** i,      # Side-to-side wave amplitude
                "z": 30,                   # Height of wave
                "rx": -90, "ry": 0, "rz": 0,  # Arm orientation
                "open": i % 2 == 0,       # Gripper open/close pattern
            })
            time.sleep(0.3)  # Speed of wave motion
```

### Detection Sensitivity
Adjust MediaPipe hand detection parameters:
```python
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,                    # Maximum hands to detect
    min_detection_confidence=0.7,       # Detection threshold (0.0-1.0)
    min_tracking_confidence=0.5         # Tracking threshold (0.0-1.0)
)
```

### Timing Configuration
- `WAVE_COOLDOWN`: Seconds between wave triggers (default: 3)
- `timeout` in video stream: Connection timeout for channel detection
- `time.sleep(0.3)`: Delay between wave motion points

### Video Channel Range
Modify the channel detection range:
```python
for channel in range(10):  # Check channels 0-9 (modify as needed)
```
