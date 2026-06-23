# Use an official Python slim base image (supports aarch64 out-of-the-box)
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for OpenCV, PyTorch, and compiling lap
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file
COPY requirements.txt /app/requirements.txt

# Install python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the python scripts
COPY main_tracking.py /app/main_tracking.py
COPY yolo_detector.py /app/yolo_detector.py
COPY association.py /app/association.py
COPY event_detector.py /app/event_detector.py
COPY evidence_collector.py /app/evidence_collector.py

# Copy YOLO model weights if they exist in the build context
COPY yolov8n.pt* yolov8s.pt* /app/

# Expose a volume for the violation records (snapshots and clips)
VOLUME /app/Violations

# Set entrypoint to run in headless mode
ENTRYPOINT ["python", "main_tracking.py", "--headless"]
CMD ["--camera", "0", "--model", "yolov8s.pt"]
