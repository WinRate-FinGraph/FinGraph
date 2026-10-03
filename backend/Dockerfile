FROM python:3.11.11-slim-bookworm AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_DEFAULT_TIMEOUT=300
RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc g++ && rm -rf /var/lib/apt/lists/*
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

FROM python:3.11.11-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    ML_ARTIFACT_DIR=/app/ml-artifacts
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 fingraph && useradd --uid 10001 --gid fingraph --create-home --shell /usr/sbin/nologin fingraph
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=fingraph:fingraph app ./app
COPY --chown=fingraph:fingraph alembic ./alembic
COPY --chown=fingraph:fingraph alembic.ini ./alembic.ini
COPY --chown=fingraph:fingraph scripts ./scripts
RUN chmod 0555 /app/scripts/*.sh && mkdir -p /app/ml-artifacts && chown fingraph:fingraph /app/ml-artifacts
USER fingraph
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD ["/app/scripts/healthcheck.sh"]
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
