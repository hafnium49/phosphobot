# SO-101 Pose to AI Control

This directory contains scripts for moving an SO-101 robot to specific poses and switching to AI model control.

## Files

- `so101_pose_to_ai_control.py` - Main script for pose control and AI switching
- `so101_demo.py` - Interactive demo with predefined poses and AI models
- `so101_practical_example.py` - Real-world example with actual trained models
- `requirements.txt` - Python dependencies

## Prerequisites

1. **PhosphoBot Server Running**:
   ```bash
   phosphobot run
   ```

2. **SO-101 Robot Connected**: Make sure your SO-101 robot is properly connected and recognized by the system.

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start

### 1. Check Robot Status

First, verify your robot is connected:

```bash
curl http://localhost:80/status
```

### 2. Run Interactive Demo

For a guided experience with predefined poses:

```bash
python so101_demo.py
```

### 3. Basic Usage

Move robot to a specific pose and start AI control:

```bash
python so101_pose_to_ai_control.py \
  --robot-id 0 \
  --model-type ACT \
  --model-id "your-username/your-model" \
  --position 0.25 0.0 0.15 \
  --orientation 0 0 0
```

## Command Line Options

### Required Parameters

- `--model-id`: HuggingFace model ID (e.g., "username/robot-model")

### Robot Control

- `--robot-id`: Robot ID (default: 0)
- `--server-url`: PhosphoBot server URL (default: "http://localhost:80")

### Pose Parameters

- `--position`: Target position [x, y, z] in meters (default: [0.25, 0.0, 0.15])
- `--orientation`: Target orientation [rx, ry, rz] in degrees (default: [0, 0, 0])
- `--gripper-open`: Open gripper at target pose

### AI Model Parameters

- `--model-type`: AI model type (`ACT`, `ACT_BBOX`, `gr00t`) (default: ACT)
- `--prompt`: Task prompt for the AI model
- `--camera-id`: Camera ID (required for ACT_BBOX models)

### Control Flow

- `--skip-pose`: Skip pose movement, go directly to AI control

## Usage Examples

### Example 1: Home Position + ACT Model

```bash
python so101_pose_to_ai_control.py \
  --robot-id 0 \
  --model-type ACT \
  --model-id "your-username/household-tasks-model" \
  --position 0.25 0.0 0.15 \
  --prompt "Organize objects on the table"
```

### Example 2: Object Detection + ACT_BBOX

```bash
python so101_pose_to_ai_control.py \
  --robot-id 0 \
  --model-type ACT_BBOX \
  --model-id "your-username/object-manipulation-model" \
  --position 0.35 0.0 0.05 \
  --orientation 0 45 0 \
  --gripper-open \
  --camera-id 0 \
  --prompt "Pick up the red object"
```

### Example 3: GR00T Model with Custom Pose

```bash
python so101_pose_to_ai_control.py \
  --robot-id 0 \
  --model-type gr00t \
  --model-id "nvidia/gr00t-base-model" \
  --position 0.30 0.1 0.20 \
  --orientation 0 -15 10 \
  --prompt "Follow natural language instructions"
```

### Example 4: Skip Pose Movement

If the robot is already in the desired position:

```bash
python so101_pose_to_ai_control.py \
  --robot-id 0 \
  --model-type ACT \
  --model-id "your-username/your-model" \
  --skip-pose \
  --prompt "Continue the current task"
```

## Common Poses

The demo script includes several predefined poses:

- **Home**: `[0.25, 0.0, 0.15]` - Neutral position
- **Pickup Ready**: `[0.35, 0.0, 0.05]` - Ready to pick objects from table
- **Observation**: `[0.20, 0.0, 0.25]` - Good for camera observation
- **Manipulation**: `[0.30, 0.1, 0.12]` - Fine manipulation tasks

## AI Model Types

### ACT (Action Chunking Transformer)
- Best for: Manipulation tasks, household activities
- Requires: RGB camera feed
- Example models: Manipulation, cleaning, organizing tasks

### ACT_BBOX (ACT with Bounding Box Detection)  
- Best for: Object-specific manipulation
- Requires: RGB camera feed + camera ID specification
- Features: Object detection and targeting

### GR00T (NVIDIA's General Robot Foundation Model)
- Best for: Natural language instruction following
- Requires: Multi-modal input (camera + language)
- Features: Advanced reasoning and planning

## Safety Considerations

1. **Workspace Limits**: The script includes workspace validation
2. **Position Tolerance**: Default tolerance is 1cm for position, 5° for orientation
3. **Emergency Stop**: Press Ctrl+C to stop AI control
4. **Torque Control**: Torque is automatically managed

## Troubleshooting

### Robot Not Found
```bash
# Check robot connection
curl http://localhost:80/status

# Check robot initialization
curl -X POST http://localhost:80/move/init -H "Content-Type: application/json" -d '{"robot_id": 0}'
```

### AI Model Errors
- Verify model ID exists on HuggingFace
- Check camera connections for vision-based models
- Ensure model type matches your actual model

### Movement Errors
- Check workspace limits (robot has movement boundaries)
- Verify position values are reachable
- Enable torque before movement

### Connection Issues
```bash
# Restart phosphobot server
phosphobot run

# Check server logs
tail -f ~/.phosphobot/logs/phosphobot.log
```

## API Endpoints Used

- `GET /status` - Robot status and health
- `POST /move/init` - Initialize robot connection
- `GET /pose` - Get current robot pose
- `POST /move/absolute` - Move to absolute position
- `POST /torque/toggle` - Enable/disable robot torque
- `POST /ai/start` - Start AI model control
- `POST /ai/stop` - Stop AI control

## Advanced Usage

### Custom Camera Mapping

For multi-camera setups with ACT models:

```python
cameras_keys_mapping = {
    "wrist_camera": 0,
    "overhead_camera": 1,
    "side_camera": 2
}
```

### Sequential Poses

Move through multiple poses before AI control:

```python
poses = [
    ([0.25, 0.0, 0.15], [0, 0, 0]),    # Home
    ([0.35, 0.0, 0.05], [0, 45, 0]),  # Pickup ready
]

for position, orientation in poses:
    controller.move_to_pose(robot_id, position, orientation)
    time.sleep(2)
```

## Integration with Other Examples

This script can be combined with:
- Voice commands (example 03)
- Hand tracking (example 05)
- Wave back (example 06)
- Rock paper scissors (example 07)
- Computer vision pipelines
- Custom AI models

## Model Development

To train your own models for SO-101:

1. Use the existing ACT/GR00T frameworks in `phosphobot/phosphobot/am/`
2. Collect demonstration data using the teleoperation system
3. Train models using the provided training scripts
4. Deploy models via HuggingFace Hub or local inference servers

---

**Note**: Replace `"your-username/your-model"` with actual HuggingFace model IDs. Make sure models are compatible with the SO-101 robot's action space and camera configuration.
