FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies from backend/requirements.txt
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code into /app
COPY backend/ .

# Expose FastAPI port
EXPOSE 8000

# Run uvicorn application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
