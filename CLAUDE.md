# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Phosphobot is an AI-ready robotics development kit that enables robot teleoperation, dataset recording, training Vision-Language-Action models, and deployment of trained models for robotic control.

## Common Development Commands

### Running the Application
```bash
# Run with PyBullet GUI simulation
phosphobot run --simulation=gui

# Run headless (default)
phosphobot run

# Run with simulated cameras
phosphobot run --simulate-cameras

# Run in chat mode with TUI
phosphobot run --chat

# Development server with hot reload
make local
```

### Testing
```bash
# Run all tests in parallel
make tests

# Run specific test file
cd phosphobot && uv run pytest tests/phosphobot/test_SO100.py

# Run test server for integration testing
make test_server
```

### Code Quality
```bash
# Type checking
make types

# Sort imports
make sort
```

### Frontend Development
```bash
# Development server
cd dashboard && npm run dev

# Production build
cd dashboard && npm run build
```

### Modal GPU Infrastructure
```bash
cd modal

# Deploy models to Modal
make deploy_all        # All models
make deploy_gr00t      # GR00T model specifically

# Run inference
modal run gr00t/app.py::serve --model-id "PLB/GR00T-N1-lego-pickup-mono-2"
```

## High-Level Architecture

### Hardware Abstraction
All robots inherit from `BaseRobot` or `BaseManipulator` in `phosphobot/hardware/base.py`. New robots are added by:
1. Creating a class in `phosphobot/hardware/`
2. Implementing abstract methods from the base class
3. Registering in `robot_name_to_class` dict in `phosphobot/robot.py`
4. Adding URDF file to `phosphobot/resources/urdf/`

The `RobotConnectionManager` in `phosphobot/robot.py` auto-detects connected hardware via serial ports and CAN interfaces.

### Camera Management
The `AllCameras` class in `phosphobot/camera.py` provides a unified interface for USB cameras, RealSense depth cameras, and simulated cameras. Cameras are discovered on startup and initialized on demand with full async support.

### Action Model Architecture
Three-layer design:
- **Client Layer** (`phosphobot/am/`): Model configs, validators, input preparation
- **Server Layer** (`modal/lerobot_modal/`): GPU inference and training on Modal
- **API Layer** (`phosphobot/endpoints/`): FastAPI endpoints

All LeRobot models inherit from the `LeRobot` base class. Supported models: ACT, SmolVLA, π0, GR00T-N1.5.

### Control Signal Pattern
Abstract control loops in `phosphobot/signals/`:
- AI Control (`ai_control.py`)
- Leader-Follower (`leader_follower.py`)
- Teleoperation (`teleoperation.py`)

Signals use async context managers for lifecycle management.

### API Structure
Modular routers in `phosphobot/endpoints/`:
- `control.py`: Robot control (manual, AI, leader-follower)
- `recording.py`: Dataset recording
- `training.py`: Model training jobs
- `camera.py`: Camera control
- WebSocket support for real-time updates

### Dataset Recording
The `Recorder` class in `phosphobot/recorder.py` handles episode recording with support for LeRobot v2.1, LeRobot v2, and JSON formats. Supports various video codecs (AVC1, VP9, FFV1, MJPEG) and direct push to HuggingFace datasets.

## Important Implementation Details

### PyBullet on Apple Silicon
PyBullet doesn't compile on M1/M2/M3/M4 Macs. A patched version exists in `bullet3/` submodule. Requires manual compilation and uncommenting in `pyproject.toml`.

### Port Strategy
Default port 80, falls back to 8020 if in use. Check with `is_port_in_use()` function.

### Frontend Integration
Frontend builds to `phosphobot/resources/dist/` and is served as static files by FastAPI. Dashboard at `/`, API docs at `/docs`.

### Modal Environments
Uses `test` and `production` environments with persistent volumes for model weights to reduce cold starts.

### CAN Bus Support
Scans up to 4 CAN interfaces by default. Can be disabled with `--no-can` flag. Used for robots like AgileX Piper.

## Key Files and Directories

- `phosphobot/main.py`: CLI entrypoint
- `phosphobot/app.py`: FastAPI application
- `phosphobot/robot.py`: Robot detection and management
- `phosphobot/hardware/`: Robot driver implementations
- `phosphobot/am/`: Action model client implementations
- `modal/lerobot_modal/`: LeRobot model server implementations
- `dashboard/src/`: React frontend source
- `phosphobot/tests/`: Test suite

## Adding New Features

### New Robot Support
See instructions in `phosphobot/README.md` Section "Adding a New Robot"

### New LeRobot Model
Follow the guide in `ADDING_LEROBOT_MODELS.md`

### API Endpoints
Add new routers to `phosphobot/endpoints/` and register in `phosphobot/app.py`

## Dependencies

- Python 3.9+ (3.10 recommended)
- Package manager: uv (Astral's fast Python package manager)
- Frontend: Node.js with npm for React dashboard
- GPU: Modal for training and inference