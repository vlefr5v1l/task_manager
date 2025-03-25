FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy the application into the container.
COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock


# Install dependencies using uv with --system flag to make packages доступными globally
RUN uv pip install --system -r pyproject.toml
COPY . /app
EXPOSE 8000

# Run the application using Python directly
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
