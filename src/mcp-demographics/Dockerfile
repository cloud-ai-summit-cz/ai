FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY *.py ./

# Install dependencies using uv
RUN uv pip install --system -e .

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=8014

EXPOSE 8014

CMD ["python", "main.py"]
