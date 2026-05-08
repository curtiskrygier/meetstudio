FROM node:22-slim AS frontend
WORKDIR /app
COPY package.json ./
RUN npm install
COPY index.html index.tsx index.css vite.config.ts tsconfig.json .env.production ./
COPY internal ./internal
COPY types ./types
COPY public ./public
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
COPY --from=frontend /app/dist ./dist
ENV PORT=8080
EXPOSE $PORT
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT --timeout-keep-alive 3600
