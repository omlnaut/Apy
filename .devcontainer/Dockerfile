FROM python:3.12-slim

WORKDIR /workspace

RUN apt update && apt install -y git && rm -rf /var/lib/apt/lists/*

COPY requirements requirements
RUN pip install --no-cache-dir -r requirements/requirements.txt