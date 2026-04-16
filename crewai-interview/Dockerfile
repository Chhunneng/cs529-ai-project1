FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Default: Redis queue consumer (docker-compose service crewai-interview-worker).
# Optional local HTTP API for debugging: uvicorn app.main:app --host 0.0.0.0 --port 9000
CMD ["python", "-m", "app.crewai_queue_consumer"]
