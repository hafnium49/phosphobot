# Aloha Lite

This repository provides a complete robotics stack for controlling Phosphobot to dispense fluids and capture snapshots when the robot reaches a target pose. The stack includes the full phosphobot system with FastAPI services for robot control and vision capture, served behind a Traefik gateway with a web front-end.

## Features

- **Complete Phosphobot Integration** - Full phosphobot system included as a git subtree
- **Robust error handling** with structured responses and timeouts
- **Resource cleanup** to prevent memory leaks
- **Health checks** for all services
- **Environment-based configuration** with secrets support
- **Comprehensive logging** throughout the system
- **CORS support** for cross-origin requests
- **Automatic retry mechanisms** and circuit breakers
- **Real-time robot control** via ZMQ messaging
- **Vision capture and analysis** with color checker detection

## Architecture

The system consists of:

1. **Phosphobot Core** - Robot control system with ZMQ state publishing
2. **Robot Service** - FastAPI service for dispense operations
3. **Vision Bridge** - Image capture and processing service
4. **Frontend** - Web interface for robot control
5. **MinIO** - S3-compatible object storage for images
6. **Traefik** - API gateway and load balancer

## Running locally

1. Copy the environment configuration:
```bash
cp .env.example .env
# Edit .env with your specific configuration
```

2. Start the services:
```bash
docker-compose up --build -d
```

Once started you can access:

- `http://localhost:8080/` – web front-end for dispense operations
- `http://localhost:80/` – phosphobot dashboard and robot control
- `http://localhost:8080/robot/docs` – Robot Service Swagger UI
- `http://localhost:9001/metrics` – Robot Service Prometheus metrics
- `http://localhost:9003/metrics` – Vision Bridge Prometheus metrics
- `http://localhost:9001/` – MinIO Console

The system will automatically create the required S3 bucket and handle service dependencies.

## Robot Configuration

The system supports multiple robot types via the `ROBOT_TYPE` environment variable:
- `simulator` - Virtual robot for testing (default)
- `so100` - SO-100 physical robot
- `so101` - SO-101 physical robot
- `wx250` - WX-250 robot arm

## Production Deployment

For production use:

1. **Update credentials** in `.env` file with secure values
2. **Configure robot type** appropriate for your hardware
3. **Configure CORS** origins in the FastAPI applications
4. **Set up proper SSL/TLS** termination
5. **Configure monitoring** and alerting for the Prometheus metrics
6. **Set up log aggregation** for centralized logging
7. **Use external database** instead of in-memory storage for tasks

## Git Subtree Management

The phosphobot repository is included as a git subtree. To update it:

```bash
# Pull latest changes from phosphobot
git subtree pull --prefix=phosphobot https://github.com/hafnium49/phosphobot.git main --squash

# Push changes back to phosphobot (if you have write access)
git subtree push --prefix=phosphobot https://github.com/hafnium49/phosphobot.git main
```

## Testing the Colour Checker

To verify the colour checker detection use the provided script:

```bash
python vision_bridge/tests/test_color_checker.py
```

The script uploads the sample image from `vision_bridge/samples` to the
`/color-checker` endpoint and prints the JSON response.
