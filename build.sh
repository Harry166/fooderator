#!/bin/bash
# Install system dependencies for zbar
apt-get update && apt-get install -y libzbar0 libzbar-dev || true

# Install Python dependencies
pip install -r requirements.txt
