# syntax=docker/dockerfile:1
#
# Frontend image (Vite). Build context: `frontend/`.
#
#   docker build -f infra/docker/frontend.Dockerfile --target dev frontend
#
# There is only a `dev` stage: in production the frontend is a static build
# (`npm run build` -> `dist/`) served from a CDN (ADR 012, decided in F7),
# so it needs no image of its own. If one is ever needed, add a `build` stage
# and a `prod` stage that serves `dist/` with a static file server.

FROM node:22-bookworm-slim AS dev
WORKDIR /app
# Dependency layer: only rebuilt when package.json or the lockfile change.
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
