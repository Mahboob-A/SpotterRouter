# -----------------------------------------------------------------------------
# Stage 1: Base runtime environment
# -----------------------------------------------------------------------------
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    HOME="/home/appuser"

WORKDIR /app

# Install system C spatial libraries and runtime tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        binutils \
        gdal-bin \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
        postgresql-client \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged system user and group
RUN groupadd -r -g 1000 appgroup \
    && useradd -r -u 1000 -g appgroup -d /home/appuser -m -s /sbin/nologin appuser \
    && mkdir -p /home/appuser/.uszipcode /app/staticfiles \
    && chown -R appuser:appgroup /home/appuser /app

# -----------------------------------------------------------------------------
# Stage 2: Dependencies builder
# -----------------------------------------------------------------------------
FROM base AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv

# Install Python packages into isolated virtualenv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra dev

# Pre-cache uszipcode static SQLite database in builder
RUN python -c "from uszipcode import SearchEngine; SearchEngine()" \
    && if [ -d /root/.uszipcode ]; then cp -r /root/.uszipcode/* /home/appuser/.uszipcode/ 2>/dev/null || true; fi \
    && chown -R appuser:appgroup /home/appuser/.uszipcode

# -----------------------------------------------------------------------------
# Stage 3: Development target (for local engineering and tests)
# -----------------------------------------------------------------------------
FROM base AS development

# Copy dependencies and pre-cached geocoding data from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /home/appuser/.uszipcode /home/appuser/.uszipcode

# Copy complete project source code and operational scripts
COPY --chown=appuser:appgroup . .
RUN chmod +x /app/infra/scripts/*.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/infra/scripts/entrypoint.sh"]
CMD ["/app/infra/scripts/start-backend-dev.sh"]

# -----------------------------------------------------------------------------
# Stage 4: Production target (immutable, hardened, static assets collected)
# -----------------------------------------------------------------------------
FROM base AS production

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /home/appuser/.uszipcode /home/appuser/.uszipcode

# Copy complete project source code
COPY --chown=appuser:appgroup . .
RUN chmod +x /app/infra/scripts/*.sh

# Run collectstatic at build time
RUN DJANGO_SECRET_KEY=build-dummy-key \
    DATABASE_URL=sqlite:///tmp/build.sqlite3 \
    python manage.py collectstatic --noinput

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/infra/scripts/entrypoint.sh"]
CMD ["/app/infra/scripts/start-backend-prod.sh"]
