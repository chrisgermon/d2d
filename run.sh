#!/bin/bash
# Run Documents to DICOM application

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv --system-site-packages
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/.installed" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    touch venv/.installed
fi

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
fi

# Run the application
echo "Starting D2D application..."
echo "Access at: http://localhost:8000"
echo "Press Ctrl+C to stop"
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
