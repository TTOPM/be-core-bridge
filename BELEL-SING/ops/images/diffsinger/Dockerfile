
FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn numpy soundfile huggingface_hub onnxruntime requests
COPY server.py /app/server.py
COPY /plugins /_plugins
COPY /weights /_weights
EXPOSE 8611
CMD ["uvicorn","server:app","--host","0.0.0.0","--port","8611"]
