FROM python:3.12.14-slim-trixie@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f AS python
FROM gosom/google-maps-scraper@sha256:e205c02913c5a69c16fc2094b8e5b194a2f655166d2c1126d50548d216e6b1b2

# Both pinned images use Debian 13. Retain the verified browser and its libraries.
COPY --from=python /usr/local/ /usr/local/
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production APP_DB_PATH=/data/backend.sqlite3 \
    BROWSER_RUNTIME=local SCRAPE_OUTPUT_DIR=/data/scrapes DISABLE_TELEMETRY=1
WORKDIR /app
COPY backend/requirements.txt /tmp/requirements.txt
COPY deploy/build_dependencies.py /tmp/build_dependencies.py
# Optional secrets support managed build networks; nothing is stored in a layer.
RUN --mount=type=secret,id=build_proxy --mount=type=secret,id=build_ca,mode=0444 \
    python3 /tmp/build_dependencies.py \
    && rm /tmp/build_dependencies.py /tmp/requirements.txt
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home app \
    && mkdir -p /data/scrapes \
    && chown -R app:app /data
COPY backend/app /app/backend/app
COPY backend/collect_leads.py backend/maps_browser.cjs backend/serve.py backend/healthcheck.py backend/backup.py backend/client_demo.py /app/backend/
# Workspace files may start owner-only; the runtime user needs read access.
RUN chmod a+rx /app && chmod -R a+rX /app/backend
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python3", "/app/backend/healthcheck.py"]
ENTRYPOINT ["python3", "/app/backend/serve.py"]
