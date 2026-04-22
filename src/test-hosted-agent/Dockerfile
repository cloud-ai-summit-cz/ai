# Minimal Dockerfile for hosted agent test
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Expose port (for local testing)
EXPOSE 8088

# Run the agent
CMD ["python", "main.py"]
