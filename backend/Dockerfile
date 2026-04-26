FROM python:3.11-slim

WORKDIR /app

# Install system deps needed by some Python drivers (optional/failsafe)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend sources
COPY backend /app

# Set default envs
ENV BACKEND_HOST=0.0.0.0
# Use PORT provided by Railway; fallback to 8000
ENV PORT=8000

EXPOSE 8000

# Use shell form so $PORT is expanded
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
 backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system deps needed by some Python drivers (optional/failsafe)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend sources
COPY backend /app

# Set default envs
ENV BACKEND_HOST=0.0.0.0
# Use PORT provided by Railway; fallback to 8000
ENV PORT=8000

EXPOSE 8000

# Use shell form so $PORT is expanded
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]