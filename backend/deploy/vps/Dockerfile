# Backend API.
#
# Deliberately small: inference is remote, so this image carries no
# torch. Dependencies are resolved from uv.lock, so the deployed API runs
# exactly what is developed and tested against.
#
# Build from the backend directory:
#     docker build -f deploy/vps/Dockerfile -t ifne-api .

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/service/.venv/bin:$PATH"

WORKDIR /service

# Dependencies first, so editing application code does not re-resolve
# them. --no-dev leaves out the test and deployment tooling.
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project --frozen

COPY app/ ./app/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
