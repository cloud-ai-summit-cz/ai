FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy all application files
COPY . .

# Install dependencies from pyproject.toml (not editable)
RUN uv pip install --system .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8016

# Run the server
CMD ["python", "main.py"]
