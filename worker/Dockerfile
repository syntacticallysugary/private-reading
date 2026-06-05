FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopus-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY private_reading/ ./private_reading/
COPY worker/worker.py .

RUN useradd -m -u 1000 worker && mkdir -p /home/worker/.oci && chown -R worker:worker /app /home/worker

ENV PYTHONPATH=/app
ENV OCI_CONFIG_PATH=/home/worker/.oci/config

USER worker

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD pgrep -f worker.py || exit 1

CMD ["python", "worker.py"]
