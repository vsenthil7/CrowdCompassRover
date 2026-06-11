# syntax=docker/dockerfile:1.6
# Build the Vite SPA, then serve the static bundle via nginx.

# ---- Stage 1: build ---------------------------------------------------------
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --prefer-offline --no-audit --no-fund
COPY . .
# Optional API key baked into the SPA so the Ops console can authenticate (RBAC stays enforced).
ARG VITE_API_KEY=""
ENV VITE_API_KEY=$VITE_API_KEY
RUN npm run build

# ---- Stage 2: serve ---------------------------------------------------------
FROM nginx:1.27-alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1
