FROM node:22-slim AS frontend
WORKDIR /app

# Build-time args — override .env.production values when passed via --set-build-env-vars
ARG CLIENT_ID
ARG CLOUD_PROJECT_NUMBER

COPY package.json ./
RUN npm install
COPY index.html index.tsx index.css vite.config.ts tsconfig.json .env.production ./
COPY main_stage.html main_stage.ts main_stage.js main_stage.css ./
COPY internal ./internal
COPY types ./types
COPY public ./public

# If ARGs are provided, overwrite .env.production so Vite picks them up
RUN if [ -n "$CLIENT_ID" ]; then \
      printf "CLIENT_ID=%s\nCLOUD_PROJECT_NUMBER=%s\n" "$CLIENT_ID" "$CLOUD_PROJECT_NUMBER" > .env.production; \
    fi

RUN rm -rf dist && npm run build

FROM python:3.12-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    tar \
    librsvg2-bin \
    && curl -fsSL https://github.com/terrastruct/d2/releases/download/v0.7.1/d2-v0.7.1-linux-amd64.tar.gz \
    -o /tmp/d2.tar.gz && \
    mkdir -p /tmp/d2x && tar -xzf /tmp/d2.tar.gz -C /tmp/d2x && \
    find /tmp/d2x -name d2 -type f -exec install -m755 {} /usr/local/bin/d2 \; && \
    rm -rf /tmp/d2.tar.gz /tmp/d2x && \
    apt-get remove -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Install python dependencies first to cache them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY assets ./assets
COPY app ./app
COPY playbooks ./playbooks
COPY catalog ./catalog
COPY catalogue ./catalogue
COPY main.py .
COPY playbook_generator.py .
COPY --from=frontend /app/dist ./dist

ENV PORT=8080
EXPOSE $PORT
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT --timeout-keep-alive 3600
