FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY backend/requirements.txt ./requirements.txt

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose port (FastAPI server port)
EXPOSE 8000

# Run the agent
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
