FROM python:3.13.4-slim

# Install system dependencies required for pyzbar and opencv
RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    libzbar0 \
    libzbar-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port (Render will set PORT environment variable)
EXPOSE ${PORT:-10000}

# Run the application with proper PORT expansion
CMD gunicorn --bind 0.0.0.0:${PORT:-10000} app:app
