FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    python -m venv /opt/venv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PATH="/opt/venv/bin:$PATH"

RUN groupadd -r botuser && useradd -r -g botuser botuser && \
    mkdir -p /app/logs && \
    chown -R botuser:botuser /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=botuser:botuser . /app/

USER botuser

HEALTHCHECK --interval=60s --timeout=10s --retries=3 --start-period=30s \
  CMD python -c "from src.utils import health_check; exit(0 if health_check() else 1)"

CMD ["python", "run.py"]