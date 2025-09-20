FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app
# Root-level modules used by the app (DB models, utils)
COPY db.py models.py db_utils.py sql_utils.py ./
# Helper scripts (optional)
COPY scripts ./scripts
# Seed database if present (optional; app can also create tables on startup)
COPY data.db ./

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
