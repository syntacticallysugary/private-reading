FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopus-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy packages and worker script (build context is project root)
COPY core/ ./core/
COPY private_reading/ ./private_reading/
COPY worker/worker.py .

# Set environment variables
ENV PYTHONPATH=/app
ENV OCI_CONFIG_PATH=/root/.oci/config

# Run the worker
CMD ["python", "worker.py"]
