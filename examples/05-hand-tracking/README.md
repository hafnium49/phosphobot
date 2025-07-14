# PhosphoBot: Hand Tracking Example

Control your SO-101 robot using hand movements captured through the PhosphoBot video stream API.

## Prerequisites

- Python 3.7+
- SO-101 robot with PhosphoBot server running on `localhost:80`
- Robot camera connected and accessible via PhosphoBot API
- Required Python packages (install via `pip install -r requirements.txt`)

## How It Works

This example uses MediaPipe to track your hand movements through the robot's camera feed and converts them to precise robot movements:

- **Hand Position**: Your hand's X, Y position controls the robot's end-effector position
- **Hand Height**: Your hand's vertical position (Y) maps to the robot's Z-axis (height)
- **Gripper Control**: Hand openness (thumb-to-finger distance) controls the gripper open/close state
- **Real-time Control**: Direct integration with PhosphoBot video stream API for responsive control

## Setup

1. **Start PhosphoBot Server**: Make sure your SO-101 robot is powered on and the PhosphoBot server is running on `localhost:80`
2. **Camera Setup**: Ensure the robot's camera is connected and accessible via `/video/0` endpoint
3. **Install Dependencies**: Create a conda environment and install MediaPipe:
   ```bash
   conda create -n mediapipe-env python=3.11
   conda activate mediapipe-env
   pip install -r requirements.txt
   ```
4. **Initialize Robot**: The script will automatically initialize the robot when started

## Running the Application

1. **Activate Environment** and run the script:
   ```bash
   conda activate mediapipe-env
   python hand_tracking.py
   ```
2. **Video Stream**: The application connects to the robot's camera via PhosphoBot API
3. **Hand Control**: Move your hand in front of the robot's camera to control movement
4. **Visual Feedback**: A window shows the camera feed with hand tracking overlay and robot status
5. **Exit**: Press 'q' to quit the application

## Control Mapping

- **X Position**: Hand left/right → Robot left/right (-100 to +100 cm)
- **Y Position**: Hand forward/back → Robot forward/back (-100 to +100 cm) 
- **Z Position**: Hand up/down → Robot height (0 to 100 cm with 50cm offset)
- **Gripper**: Hand openness → Gripper state (0.0 = closed, 1.0 = open)

## Features

- **Real-time Hand Detection**: Uses MediaPipe for accurate hand landmark detection
- **PhosphoBot Integration**: Direct connection to robot's camera via HTTP API  
- **Responsive Control**: Low-latency movement commands with visual feedback
- **Coordinate Mapping**: Intelligent mapping from hand position to robot workspace
- **Gripper Control**: Natural hand gesture for gripper open/close
- **Error Handling**: Robust connection handling and error recovery

## Troubleshooting

- **"Failed to connect to server"**: Check that PhosphoBot server is running on `localhost:80`
- **"Video stream error"**: Verify robot camera is connected and accessible via `/video/0`
- **Hand not detected**: Ensure good lighting and keep hand within camera frame
- **Robot not responding**: Check robot initialization and movement command status
- **Laggy movement**: Reduce `timeout` value in movement requests or check network connection

## Technical Details

- **Video Stream**: MJPEG stream from PhosphoBot API (`http://localhost:80/video/0`)
- **Hand Detection**: MediaPipe Hands with 70% confidence threshold
- **Movement API**: HTTP POST to `/move/absolute` endpoint with JSON coordinates
- **Coordinate System**: Robot workspace coordinates in centimeters
- **Threading**: Separate thread for video stream processing to maintain responsiveness

## Customization

You can modify the script to change:

- **Coordinate Mapping**: Adjust the scaling factors in the hand position calculation
- **Gripper Sensitivity**: Modify the `calculate_hand_open_state()` function parameters
- **Detection Confidence**: Change `min_detection_confidence` and `min_tracking_confidence` values
- **Movement Range**: Adjust the coordinate mapping ranges for different workspace sizes
- **Camera Source**: Change `camera_url` to use different video endpoints
- **Timeout Values**: Adjust request timeouts for different network conditions

## Dependencies

See `requirements.txt` for complete list:
- `mediapipe` - Hand tracking and pose estimation
- `opencv-python` - Computer vision and image processing  
- `numpy` - Numerical computations
- `requests` - HTTP client for API communication
