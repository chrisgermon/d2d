#!/bin/bash
# Simple run without virtual environment
# Uses system Python packages

cd "$(dirname "$0")"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
fi

# Create necessary directories
mkdir -p uploads dicom_archive temp

# Check if dependencies are installed
echo "Checking dependencies..."
python3 -c "import fastapi" 2>/dev/null || {
    echo "Installing dependencies..."
    pip3 install --user -r requirements.txt
}

# Run the application
echo "Starting D2D application..."
echo "Access at: http://localhost:8000"
echo "Server IP: http://10.60.60.172:8000"
echo "Press Ctrl+C to stop"
echo ""
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*' --timeout-keep-alive 300
