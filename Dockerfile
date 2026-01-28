FROM python:3.11-slim

# Install system dependencies
# python3-gdcm provides GDCM library for JPEG Lossless DICOM decompression
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libmagic1 \
    python3-gdcm \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p uploads dicom_archive temp

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
