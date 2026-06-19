# Dockerfile for Hugging Face Spaces
FROM python:3.11.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app_hf.py .
COPY quick_mapper.py .
COPY auto_transcribe_mapper.py .

# Create necessary directories
RUN mkdir -p /tmp/audio_uploads /tmp/audio_outputs

# Expose port for Hugging Face Spaces
EXPOSE 7860

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Run the application
CMD ["python", "app_hf.py"]
