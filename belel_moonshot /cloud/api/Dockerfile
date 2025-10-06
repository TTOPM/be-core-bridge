
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
ENV BELEL_PRESETS_PATH=/app/config_presets.json
EXPOSE 8282
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8282"]
