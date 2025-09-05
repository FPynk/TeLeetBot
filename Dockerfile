# Base runtime
FROM python:3.11-slim

# OS Packages needed at runtime
# install timezone db, sqlite3 cli, tls roots, curl, then cleans apt cache
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata sqlite3 ca-certificates curl &&\
    rm -rf /var/lib/apt/lists/*

# app-level environment
ENV TZ=America/Chicago PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# local timezone for lgos; unbuffered stcdout; no pip cache in layers

# non-root user (matches volume ownership set to UID 10001)
# safer than running as root
RUN useradd -m -u 10001 appuser

# all paths  below are relative to /app inside the container
WORKDIR /app

# install python dependencies first to leverage docker layer caching
# rebuilds only when requirements.txt changes
COPY requirements.txt ./
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# Copy app code
COPY src ./src

# Ensure backups dir exists
RUN mkdir -p /app/backups && chown -R appuser:appuser /app

# drop privileges before running app
USER appuser

# light weight health check
HEALTHCHECK --interval=5m --timeout=5s --start-period=30s --retries=2 \
    CMD sh -c 'getent hosts api.telegram.org >/dev/null 2>&1 && [ -n "$BOT_TOKEN" ] && curl -fsS "https://api.telegram.org/bot${BOT_TOKEN}/getMe" >/dev/null'

# start bot (aiogram long polling)
CMD ["python", "-m", "src.main"]