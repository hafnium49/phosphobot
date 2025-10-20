# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Phosphobot is a robotics middleware platform for controlling robots, recording datasets, and training/using Vision Language Action (VLA) models. It supports multiple robots (SO-100, SO-101, WX-250, AgileX Piper, Unitree Go2) with teleoperation via keyboard, leader arm, or Meta Quest VR.

## Development Commands

### Running the Server

```bash
# Development mode with GUI simulation (localhost:8080)
make local

# Development mode - backend only with headless simulation
cd phosphobot && uv run phosphobot run --simulation=headless

# Frontend development (separate terminal)
cd dashboard && npm run dev

# Production mode (builds frontend + runs headless)
make prod

# Run without telemetry
make prod_no_telemetry

# Only simulation mode (no real hardware)
phosphobot run --only-simulation
```

### Testing

```bash
# Run all unit tests in parallel
uv run pytest tests/phosphobot/ -n 5

# Run API integration tests (requires test server)
make test_server  # In one terminal
uv run pytest tests/api/  # In another terminal

# Type checking
uv run mypy phosphobot
```

### Building

```bash
# Build React frontend
make build_frontend

# Create standalone executable
make build_pyinstaller

# Full build (frontend + backend)
make
```

### Cleanup

```bash
make stop       # Stop Python/uv processes
make stop_hard  # Force kill ports 80, 8020, 8080
```

## Architecture Overview

### Core Components Architecture

The system follows a layered architecture with clear separation between hardware, control, and API layers:

```
FastAPI App (app.py)
    ↓
Routers (endpoints/)
    ↓
Singleton Managers:
- RobotConnectionManager (robot.py) - Auto-detects and manages robot connections
- AllCameras (camera.py) - Unified multi-camera interface
- Recorder (recorder.py) - Dataset recording in LeRobot format
- PyBullet Sim (sim.py) - Physics simulation
    ↓
Hardware Abstraction (hardware/)
- BaseRobot/BaseManipulator - Abstract interfaces
- Concrete implementations (SO100Hardware, PiperHardware, etc.)
```

### Dependency Injection Pattern

FastAPI endpoints use dependency injection for singleton resources:

```python
# In endpoints, always use these patterns:
rcm = Depends(get_rcm)           # RobotConnectionManager
cameras = Depends(get_all_cameras)  # AllCameras
recorder = Depends(get_recorder)    # Recorder
sim = Depends(get_sim)              # PyBullet simulation
```

### Frontend-Backend Communication

- **REST API**: Standard CRUD operations
- **WebSocket**: Real-time robot control at `/api/control/ws`
- **Interactive docs**: Available at `/docs` (Swagger UI)
- **Frontend build**: Served statically from `/` when built

## Key Development Patterns

### Adding New Robot Support

1. Create class in `phosphobot/hardware/` inheriting from `BaseRobot` or `BaseManipulator`
2. Implement abstract methods: `connect()`, `disconnect()`, `move()`, `get_state()`
3. Add URDF file to `phosphobot/resources/urdf/`
4. Register in `RobotConnectionManager.robot_name_to_class` dict

### Adding New AI Models

1. Implement in `phosphobot/am/` inheriting from `BaseActionModel`
2. Support HuggingFace model loading via `from_pretrained()`
3. Implement `step()` method for inference

### Configuration System

- User config: `~/.phospho/config.yaml`
- Loaded via Pydantic `Configuration` class in `configs.py`
- Runtime overrides via CLI flags take precedence

### Port Fallback Strategy

Server attempts ports in order: 80 → 8020-8039. If port 80 fails, automatically tries next available port.

### Dataset Formats

- **LeRobot v2.1** (default): HuggingFace-compatible format
- **JSON**: Simple format for debugging
- Episodes stored in `~/.phospho/datasets/` by default

### Testing Strategy

- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test full API flows with simulated hardware
- **Test server**: Run `make test_server` for headless testing environment

### Async Patterns

- Heavy use of `async`/`await` throughout
- FastAPI native async support
- Use `asyncio.create_task()` for concurrent operations
- WebSocket handlers must be async

### Telemetry

- PostHog analytics (20% sampling on non-critical requests)
- Sentry error reporting
- Can be disabled with `--no-telemetry` flag or `make prod_no_telemetry`

### Modal Cloud Training

Training infrastructure in `modal/` directory:
- Serverless GPU training via Modal.com
- Automatic dataset download from HuggingFace
- Model upload back to HuggingFace after training