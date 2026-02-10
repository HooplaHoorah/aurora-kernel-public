FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements-hackathon.txt .

# Install dependencies
RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install --no-cache-dir -r requirements-hackathon.txt && \
    python3 -m pip install --no-cache-dir uvicorn gunicorn

# Copy application code
COPY src/aurora_kernel/ ./aurora_kernel/

# Expose port
EXPOSE 8080

# Set environment variable for port
ENV PORT=8080
ENV PYTHONPATH=/app

# Start command using python3 -m to ensure it uses the correct path
CMD ["python3", "-m", "uvicorn", "aurora_kernel.api:app", "--host", "0.0.0.0", "--port", "8080"]
