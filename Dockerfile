# Use Python 3.9 as base image
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    # Install Node.js 20.x (LTS version)
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    # Verify Node.js and npm versions
    && node --version \
    && npm --version \
    # Install AWS CDK globally
    && npm install -g aws-cdk \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements files
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Copy project files
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Default command
CMD ["bash"]