# BELEL-SING/Dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 espeak-ng git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir fastapi uvicorn[standard] soundfile librosa jiwer transformers TTS torch torchaudio --index-url https://download.pytorch.org/whl/cpu
ENV HF_HOME=/root/.cache/huggingface TRANSFORMERS_CACHE=/root/.cache/huggingface PYTHONUNBUFFERED=1 COQUI_TOS_AGREED=1
EXPOSE 8001
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8001"]
