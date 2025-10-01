FROM python:3.11-slim
WORKDIR /app
COPY src/ src/
RUN pip install --no-cache-dir requests jsonschema
ENV PYTHONPATH=/app/src
ENV GROK_SELF_HEAL_INTERVAL_SEC=60
CMD ["python","-m","grok.services.grok_self_heal_service"]
