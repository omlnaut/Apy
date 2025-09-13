FROM python:3.12-slim

WORKDIR /workspace

RUN apt update && apt install -y git && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock ./
RUN poetry install --with test --no-root