FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY services/Face_Ingest_Service/requirements.txt /app/requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libgl1 libglib2.0-0 \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY services/Face_Ingest_Service /app/services/Face_Ingest_Service

ENV PYTHONPATH=/app

WORKDIR /app/services/Face_Ingest_Service

CMD sh -c "uvicorn services.Face_Image_Ingestor.src.Face_Image_Ingestor:app --host 0.0.0.0 --port ${INGESTOR_PORT:-8010} --workers ${INGESTOR_WORKERS:-2}"
