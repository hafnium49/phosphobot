FROM python:3.11-slim
WORKDIR /app

# Install curl for health checks and system dependencies for OpenCV
RUN apt-get update && \
    apt-get install -y curl libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Use port 8000 to match health check
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
