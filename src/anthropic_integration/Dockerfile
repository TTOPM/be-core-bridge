# Belel × Anthropic Integration CLI
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir fastapi uvicorn nacl opentelemetry-sdk opentelemetry-exporter-otlp
COPY . .
ENV PYTHONPATH=/app
CMD ["python", "-m", "src.cli", "Demo run via Docker"]
