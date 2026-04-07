# Backend Dockerfile — Python 3.12 / FastAPI / Uvicorn
# Installs all Python dependencies; source code is bind-mounted at runtime
# so uvicorn --reload picks up changes instantly without a rebuild.
#
# Added: 2026-04-03

FROM python:3.12-slim

WORKDIR /workspace

# System deps required by psycopg2-binary, bcrypt, and cryptography
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source (overridden by bind mount in dev)
COPY app/ ./app/
COPY .env.example .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "app"]
