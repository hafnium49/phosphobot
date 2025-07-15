# PhosphoBot: Rock Paper Scissors Game

This example demonstrates how to play Rock-Paper-Scissors with the PhosphoBot robot using computer vision and automatic video channel detection.

## Prerequisites

- Python 3.7+
- SO-101 robot with PhosphoBot server running on `localhost:80`
- Robot camera connected and accessible via PhosphoBot API
- Required Python packages (install via `pip install -r requirements.txt`)

## How It Works

The application uses MediaPipe to detect hand gestures through the PhosphoBot video stream API and plays an interactive game:

- **Automatic Video Channel Detection**: Scans available video channels (0-9) to find the active camera
- **Live Video Preview**: Shows a 5-second countdown with real-time video feed for gesture positioning
- **Hand Gesture Recognition**: Uses MediaPipe to detect rock, paper, or scissors gestures
- **Robot Interaction**: Robot performs countdown, makes its own gesture, and announces the winner
- **PhosphoBot API Integration**: Direct integration with robot movement and video streaming APIs

## Key Features

- **Dynamic Video Channel Discovery**: Automatically finds the correct video stream channel
- **Interactive Video Preview**: Live camera feed with countdown timer and instructions
- **Real-time Gesture Detection**: MediaPipe hand tracking with gesture classification
- **Robot Animation**: Physical countdown and gesture demonstrations
- **Robust Error Handling**: Graceful handling of connection issues and detection failures

## Installation

1. **Start PhosphoBot Server**: Ensure the robot is powered on and the PhosphoBot server is running on `localhost:80`
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Automatic Camera Detection**: The application will automatically detect available video channels

## API Endpoints Used

- **Robot Connection**: `POST http://localhost:80/move/init` - Initialize robot connection
- **Robot Movement**: `POST http://localhost:80/move/absolute` - Control robot position and gestures
- **Video Stream**: `GET http://localhost/video/{channel}` - MJPEG video stream (auto-detected channel)

## Configuration

The script `rock_paper_scissors.py` contains configurable parameters:

```python
# Robot API Configuration
PI_IP = "127.0.0.1"  # IP address of the robot (default: localhost)
PI_PORT = 80         # Port of the robot's API server
```

## How to Play

1. **Start the Game**:
   ```bash
   python rock_paper_scissors.py
   ```

2. **Game Sequence**:
   - **Robot Initialization**: Connects to PhosphoBot server and initializes robot
   - **Automatic Channel Detection**: Finds available video stream (tests channels 0-9)
   - **Robot Countdown**: Physical countdown with arm movements (3-2-1-0)
   - **Video Preview**: 5-second live camera feed with countdown timer
   - **Gesture Capture**: Make your rock, paper, or scissors gesture during the preview
   - **Robot Response**: Robot chooses its gesture and demonstrates it physically
   - **Winner Announcement**: Game displays both choices and declares the winner

3. **During Video Preview**:
   - Position your hand clearly in front of the camera
   - Make a clear rock, paper, or scissors gesture
   - The countdown timer shows remaining time
   - Press 'q' to quit or wait for automatic capture

## Example Output

```
🚀 PHOSPHOBOT ROCK PAPER SCISSORS
========================================
🎮 Get ready to play Rock Paper Scissors with the robot!

🔄 Initializing robot...
✅ Robot initialized!

🎯 Robot performing countdown...
3
2
1
0

📸 Get ready to make your gesture...
🔍 Searching for available video channels...
  Testing channel 4...
✅ Found working video channel: 4
📹 Using video channel: 4
📺 Showing 5-second video preview...
🖐️ Position your hand in front of the camera and make your gesture!
✅ Frame captured successfully!

🎯 Player chose: rock
🤖 Robot chose: scissors
🤖 Robot making scissors gesture...

🏆 Player wins!

✅ Game finished!
```

## Supported Gestures

- **Rock**: Closed fist (all fingers folded)
- **Paper**: Open hand with all fingers extended
- **Scissors**: Only index and middle fingers extended (victory sign)

## Robot Gesture Demonstrations

- **Rock**: Gripper closed, neutral position
- **Paper**: Gripper open, neutral position  
- **Scissors**: Gripper half-open, tilted position (ry=-45°)

## Troubleshooting

### Video Stream Issues
- **No video channels found**: Verify PhosphoBot server is running and camera is connected
- **404 errors on video channels**: The camera may be on a different channel - the app will auto-detect
- **Stream connection errors**: Check network connectivity to the robot

### Gesture Detection Issues
- **Gesture not recognized**: Ensure good lighting and hold your hand clearly in the camera view
- **No hand detected**: Position your hand within the camera frame during the 5-second preview
- **Inconsistent detection**: Make clear, distinct gestures and avoid partial hand visibility

### Robot Control Issues
- **Robot init fails**: Verify PhosphoBot server is accessible at `localhost:80`
- **Movement errors**: Check if the robot is properly calibrated and has sufficient power
- **Game cancelled**: User pressed 'q' during video preview

### Performance Tips
- Ensure good lighting for optimal gesture detection
- Make clear, exaggerated gestures for better recognition
- Keep your hand steady during the capture moment
- Avoid background motion that might interfere with detection

## Technical Details

### Video Stream Processing
- **Format**: MJPEG stream with automatic frame boundary detection
- **Channel Detection**: Tests GET requests to channels 0-9 to find active camera
- **Live Preview**: Real-time video feed with overlay countdown and instructions
- **Frame Capture**: Single frame extraction for gesture analysis
- **Error Recovery**: Automatic reconnection on stream failures

### Gesture Recognition
- **MediaPipe Configuration**:
  - `static_image_mode=False` for video processing
  - `max_num_hands=1` for single hand detection
  - `min_detection_confidence=0.7` for reliable detection
  - `min_tracking_confidence=0.7` for stable tracking
- **Gesture Algorithm**: Finger extension analysis based on landmark distances
- **Classification Logic**: Specific patterns for rock (closed), paper (open), scissors (two fingers)

### Robot Integration
- **Physical Countdown**: 3-2-1-0 sequence with vertical arm movements
- **Gesture Demonstration**: Robot performs its chosen gesture with appropriate positioning
- **Movement Commands**: Uses absolute positioning with 6DOF control
- **Game Logic**: Random choice generation and winner determination

## How It Works

The application uses advanced computer vision and robotics integration:

- **PhosphoBot Video API**: MJPEG stream processing with automatic channel detection
- **MediaPipe Hand Tracking**: Real-time hand landmark detection and gesture classification
- **Robot Control API**: HTTP POST requests for movement commands and gesture demonstration
- **Interactive Game Logic**: Random choice generation and winner determination algorithms
- **Live Video Preview**: Real-time camera feed with countdown overlay and user instructions

## Customization

### Gesture Detection Sensitivity
Adjust MediaPipe parameters for different conditions:
```python
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,                    # Number of hands to detect
    min_detection_confidence=0.7,       # Detection threshold (0.0-1.0)
    min_tracking_confidence=0.7         # Tracking threshold (0.0-1.0)
)
```

### Video Preview Duration
Modify the preview time for gesture positioning:
```python
frame = self.show_video_preview_and_capture(preview_time=5)  # Seconds
```

### Robot Gesture Positions
Customize robot gesture demonstrations:
```python
def make_rock_gesture(self):
    self.call_to_api("absolute", {
        "x": 0, "y": 0, "z": 5,           # Position coordinates
        "rx": 0, "ry": 0, "rz": 0,        # Rotation angles
        "open": 0                         # Gripper state (0=closed, 1=open)
    })
```

### Gesture Recognition Logic
Modify the finger extension detection:
```python
fingers_extended.append(distance > 0.2)  # Threshold for extended fingers
```

## Dependencies

See `requirements.txt` for complete list:
- `mediapipe` - Hand tracking and pose estimation
- `opencv-python` - Computer vision and video processing
- `numpy` - Numerical computations for gesture analysis
- `requests` - HTTP client for PhosphoBot API communication
