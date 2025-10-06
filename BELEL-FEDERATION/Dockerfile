# BELEL-FEDERATION/Dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir fastapi uvicorn[standard] requests
ENV PYTHONUNBUFFERED=1
EXPOSE 8002
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8002"]
