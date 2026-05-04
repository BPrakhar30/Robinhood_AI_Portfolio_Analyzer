# Backend: Python 3.12 / FastAPI / Uvicorn. Source is bind-mounted in dev.

FROM python:3.12-slim

WORKDIR /workspace

# System deps for psycopg2-binary, bcrypt, cryptography.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY .env.example .

RUN groupadd -r appuser && useradd -r -g appuser -d /workspace -s /sbin/nologin appuser \
    && chown -R appuser:appuser /workspace
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
