# Aloha Lite

This repository provides a minimal web stack for controlling Phosphobot to dispense fluids and capture snapshots when the robot reaches a target pose. The stack is composed of FastAPI services for robot control and vision capture, served behind a Traefik gateway together with a very small front-end.

## Features

- **Robust error handling** with structured responses and timeouts
- **Resource cleanup** to prevent memory leaks
- **Health checks** for all services
- **Environment-based configuration** with secrets support
- **Comprehensive logging** throughout the system
- **CORS support** for cross-origin requests
- **Automatic retry mechanisms** and circuit breakers

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

- `http://localhost:8080/` – web front-end
- `http://localhost:8080/robot/docs` – Robot Service Swagger UI
- `http://localhost:9001/metrics` – Robot Service Prometheus metrics
- `http://localhost:9003/metrics` – Vision Bridge Prometheus metrics
- `http://localhost:9001/` – MinIO Console

The system will automatically create the required S3 bucket and handle service dependencies.

## Production Deployment

For production use:

1. **Update credentials** in `.env` file with secure values
2. **Configure CORS** origins in the FastAPI applications
3. **Set up proper SSL/TLS** termination
4. **Configure monitoring** and alerting for the Prometheus metrics
5. **Set up log aggregation** for centralized logging
6. **Use external database** instead of in-memory storage for tasks

## Testing the Colour Checker

To verify the colour checker detection use the provided script:

```bash
python vision_bridge/tests/test_color_checker.py
```

The script uploads the sample image from `vision_bridge/samples` to the
`/color-checker` endpoint and prints the JSON response.
