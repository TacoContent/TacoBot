FROM python:3.13-alpine

ARG BRANCH="develop"
ARG BUILD_VERSION="1.0.0-snapshot"
ARG PROJECT_NAME=

ENV PYTHONUNBUFFERED=0
ENV APP_VERSION=${BUILD_VERSION}

LABEL VERSION="${BUILD_VERSION}"
LABEL BRANCH="${BRANCH}"
LABEL PROJECT_NAME="${PROJECT_NAME}"

COPY ./ /app/
RUN \
    apk update && \
    apk add --no-cache git curl build-base tcl tk && \
    mkdir -p /app /data && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/setup/requirements.txt && \
    sed -i "s/APP_VERSION = \"1.0.0-snapshot\"/APP_VERSION = \"${APP_VERSION}\"/g" "/app/bot/lib/settings.py" && \
    sed -i "s/\"version\": \"1.0.0-snapshot\"/\"version\": \"${APP_VERSION}\"/g" "/app/app.manifest" && \
    sed -i "s/version: \"1.0.0-snapshot\"/version: \"${APP_VERSION}\"/g" "/app/.swagger.v1.yaml" && \
    apk del git build-base && \
    rm -rf /app/setup


RUN addgroup -S tacobot && adduser -S tacobot -G tacobot

# Set permissions for /app, /data, and /config
RUN chown -R tacobot:tacobot /app /data && \
    mkdir -p /config && \
    chown -R tacobot:tacobot /config

USER tacobot

VOLUME ["/data"]
VOLUME ["/config"]
WORKDIR /app

# perform health check using both discordhealthcheck and a curl to localhost:8931/healthz
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD discordhealthcheck && curl --fail-with-body --silent --show-error -X GET http://localhost:8931/healthz || exit 1

CMD ["python", "-u", "/app/main.py"]
