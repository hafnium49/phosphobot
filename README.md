# Aloha Lite

This repository provides a minimal web stack for controlling Phosphobot to dispense fluids and capture snapshots when the robot reaches a target pose. The stack is composed of FastAPI services for robot control and vision capture, served behind a Traefik gateway together with a very small front-end.

## Running locally

```bash
docker-compose up --build -d
```

Once started you can access:

- `http://localhost:8080/` – web front-end
- `http://localhost:9000/docs` – Robot Service Swagger UI
- `http://localhost:9001/metrics` – Prometheus metrics

Create the `snapshots` bucket in object storage after the services start:

```bash
docker exec -it $(docker compose ps -q vision-bridge) \
  aws --endpoint-url http://minio:9000 s3 mb s3://snapshots
```

## Testing the Colour Checker

To verify the colour checker detection use the provided script:

```bash
python vision_bridge/tests/test_color_checker.py
```

The script uploads the sample image from `vision_bridge/samples` to the
`/color-checker` endpoint and prints the JSON response.
