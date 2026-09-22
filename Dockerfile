FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend HAWKERBRIDGE_BIND=0.0.0.0 PORT=8080
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --system hawkerbridge \
    && useradd --system --gid hawkerbridge --home /app hawkerbridge
COPY backend ./backend
COPY scripts/start_app.py ./scripts/start_app.py
COPY data/processed ./data/processed
COPY frontend/dist ./frontend/dist
RUN chmod -R a+rX /app
USER hawkerbridge
EXPOSE 8080
CMD ["python", "scripts/start_app.py"]
