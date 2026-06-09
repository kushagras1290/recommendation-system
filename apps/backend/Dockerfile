FROM python:3.11-slim

WORKDIR /app

# System deps for psycopg2 / scipy
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc g++ libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

RUN mkdir -p /app/model_artifacts

ENV PORT=8000
ENV MODEL_DIR=/app/model_artifacts

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
