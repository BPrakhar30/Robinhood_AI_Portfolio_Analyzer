# Frontend: production Next.js image. docker-compose overrides CMD for dev.

FROM node:20-alpine AS deps

WORKDIR /workspace

COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder

WORKDIR /workspace
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /workspace/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /workspace
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /workspace/package.json ./package.json
COPY --from=builder /workspace/node_modules ./node_modules
COPY --from=builder /workspace/.next ./.next
COPY --from=builder /workspace/public ./public

RUN addgroup -S appgroup && adduser -S appuser -G appgroup \
    && chown -R appuser:appgroup /workspace
USER appuser

EXPOSE 3000

CMD ["npx", "next", "start", "--port", "3000", "--hostname", "0.0.0.0"]
