FROM python:3.12-slim

# ffmpeg is a system binary; ffmpeg-python is just a wrapper around it
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Dedicated non-root user
RUN useradd -r -u 1000 -s /bin/false myaudible

WORKDIR /app

# Install Python deps before copying source so this layer is cache-friendly
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy and install the package
COPY . .
RUN pip install --no-cache-dir -e .

# Mount points for host-side input/output directories
RUN mkdir -p /input /output && chown myaudible:myaudible /input /output

USER myaudible

ENV PYTHONUNBUFFERED=1

# Watch mode: inotify fires on every file written/moved into /input
CMD ["python", "-m", "myaudible", "-i", "/input", "-o", "/output", "-w"]
