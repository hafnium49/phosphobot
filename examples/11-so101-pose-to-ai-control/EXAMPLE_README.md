# SO-101 Pose to AI Control

This example demonstrates how to move an SO-101 robot to a specific pose using rule-based control and then seamlessly switch to AI model control for autonomous operation.

## Prerequisites

- SO-101/SO-100 robotic arm connected to your computer
- Phosphobot server running (`phosphobot run`)
- Python 3.10+
- 1-3 cameras for AI model control (optional for pose-only control)

## What this example does

1. **Rule-based Pose Control**: Move robot to precise positions and orientations
2. **AI Model Integration**: Switch to autonomous AI control using ACT, GR00T, or ACT_BBOX models
3. **Seamless Transition**: Demonstrate hybrid manual-to-AI control workflows
4. **Real Model Examples**: Use actual trained models from HuggingFace Hub

## Key Features

- ✅ **Immediate Use**: Pose control works without cameras
- 🧠 **AI Integration**: Full support for modern robotics AI models
- 🎯 **Predefined Poses**: Common positions for different tasks
- 🔄 **Safe Transitions**: Proper torque management and error handling
- 📊 **Real-time Monitoring**: Status checking and feedback

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Test setup
python test_setup.py

# Run interactive demo
python so101_demo.py

# Or use specific pose and AI model
python so101_pose_to_ai_control.py \
  --model-id "LegrandFrederic/Orange-brick-in-black-box" \
  --position 0.25 0.0 0.15
```

## Files Structure

- `so101_pose_to_ai_control.py` - Main script with full functionality
- `so101_demo.py` - Interactive demo with predefined poses  
- `so101_practical_example.py` - Real-world example with trained model
- `test_setup.py` - Setup verification and diagnostics
- `README.md` - Detailed usage documentation
- `QUICK_ANSWER.md` - Quick overview and system status
- `requirements.txt` - Python dependencies

## Answer to "Is it possible?"

**YES!** This example proves that moving SO-101 robots to specific poses and switching to AI model control is not only possible but fully implemented and ready to use.

See `QUICK_ANSWER.md` for a comprehensive answer to the original question.
