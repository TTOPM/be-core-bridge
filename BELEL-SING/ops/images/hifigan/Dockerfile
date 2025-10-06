
FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn numpy soundfile requests
COPY server.py /app/server.py
COPY /plugins /_plugins
COPY /weights /_weights
EXPOSE 8612
CMD ["uvicorn","server:app","--host","0.0.0.0","--port","8612"]
