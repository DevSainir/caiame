FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml ./
RUN uv pip install --system --no-cache .

COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
COPY scripts ./scripts

EXPOSE 8000

# --proxy-headers with an explicit allow list is what makes request.client.host the real
# client behind Nginx. Without it every visitor shares one bucket in the rate limiter;
# trusting X-Forwarded-For from anyone would let an attacker forge a fresh bucket per try.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
