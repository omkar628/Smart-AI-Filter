FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY backend/requirements.docker.txt ./requirements.docker.txt

RUN python -m pip install --upgrade pip && \
    pip install --index-url https://download.pytorch.org/whl/cpu torch==2.13.0 && \
    pip install -r requirements.docker.txt

COPY backend/ .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
