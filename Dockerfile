# Stage 1: Build the review screen web assets
FROM node:20-slim AS web-builder
WORKDIR /app/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 2: Build the wheel and assemble the runtime image
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r zyn && useradd -r -g zyn -m -d /home/zyn zyn

ENV ZYN_HOME=/data
RUN mkdir -p /data && chown -R zyn:zyn /data

WORKDIR /app
COPY pyproject.toml README.md setup.py config.yaml .env.example knowledge.example.md taxonomy_placeholder.yaml ./
COPY rules/ ./rules/
COPY data/synthetic/ ./data/synthetic/
COPY harness/ ./harness/
COPY --from=web-builder /app/web/dist/ ./web/dist/

RUN pip install --no-cache-dir wheel \
    && pip wheel --no-deps -w /dist . \
    && WHEEL=$(ls /dist/*.whl) \
    && pip install --no-cache-dir "$WHEEL[team]" \
    && rm -rf /app/* /dist

USER zyn
WORKDIR /data

EXPOSE 8600

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:8600/api/health || exit 1

CMD ["zyn", "serve", "--team", "--host", "0.0.0.0", "--no-browser"]
