# ── Delta Learn Backend ──────────────────────────────────
# Django 6 + DRF + Gemma AI + Mermaid diagram rendering
# ─────────────────────────────────────────────────────────

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

# System dependencies: Chromium (for mmdc), Node.js (for mmdc), cron, fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
        cron \
        curl \
        gnupg \
        chromium \
        fonts-liberation \
        fonts-noto-color-emoji \
        libgbm1 \
        libnss3 \
        libatk-bridge2.0-0 \
        libx11-xcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libcups2 \
        libdrm2 \
        libdbus-1-3 \
        libasound2 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @mermaid-js/mermaid-cli \
    && apt-get purge -y gnupg \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /root/.npm

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Application code
COPY . .

# Static files
RUN python manage.py collectstatic --noinput 2>/dev/null || true

# Data directory (SQLite + media live here via volume mount)
RUN mkdir -p /app/data

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "delta_learn.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
