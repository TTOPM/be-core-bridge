FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN python -m pip install --upgrade pip
# Install minimal runtime dependencies; each Makefile installs more on start.
RUN pip install fastapi uvicorn pydantic httpx rich pyyaml gunicorn
EXPOSE 8000
CMD ["bash","-lc","gunicorn -k uvicorn.workers.UvicornWorker belelvoice.server.app:app --bind 0.0.0.0:8000"]
