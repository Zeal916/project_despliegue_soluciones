FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY docker/requirements.txt .
RUN pip install -r requirements.txt
COPY src ./src
COPY app ./app
