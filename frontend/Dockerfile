# Frontend Dockerfile — Node 20 / Next.js 16 dev server
# Installs npm dependencies inside the image; source code is bind-mounted
# at runtime so Next.js hot-reload reflects changes without a rebuild.
#
# node_modules and .next are protected by anonymous volumes in docker-compose
# to avoid conflicts between host and container dependencies.
#
# Added: 2026-04-03

FROM node:20-alpine

WORKDIR /workspace

COPY package.json package-lock.json ./
RUN npm ci

# Copy source (overridden by bind mount in dev)
COPY . .

EXPOSE 3000

CMD ["npx", "next", "dev", "--port", "3000", "--hostname", "0.0.0.0"]
