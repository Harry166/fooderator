FROM python:3.13.4-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libzbar0 \
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
EXPOSE 5000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app"]
