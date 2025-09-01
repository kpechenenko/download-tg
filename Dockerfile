FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
  gcc \
  libffi-dev \
  libssl-dev \
  && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
  # pip install --no-cache-dir -r requirements.txt
  pip install --no-cache-dir -r requirements.txt

RUN python -m venv venv \
  source venv/bin/activate

# Copy application code
COPY . .

# Create necessary directories inside container
RUN mkdir -p sessions downloads logs

# Create non-root user
RUN useradd -m -u 1000 appuser && \
  chown -R appuser:appuser /app

USER appuser

