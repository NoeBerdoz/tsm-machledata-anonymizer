# The backend for Cloud Run (#64). Build and deploy steps: docs/gcp-setup.md.
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
# The project's own dependencies only: no dev, tracking or model groups.
RUN uv sync --locked --no-default-groups --no-cache

# Cloud Run sends requests to every interface of the container, on the port it gives in PORT.
ENV PII_BACKEND_HOST=0.0.0.0
CMD ["/app/.venv/bin/python", "-m", "pii_anonymizer.backend"]
