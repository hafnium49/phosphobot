FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y curl build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy phosphobot source
COPY . .

# Install phosphobot in development mode
RUN pip install -e .

# Expose ports
EXPOSE 80 5555

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# Start phosphobot server
CMD ["python", "-m", "phosphobot.main", "run", "--host", "0.0.0.0", "--port", "80"]
