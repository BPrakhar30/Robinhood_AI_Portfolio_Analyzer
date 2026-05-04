# Frontend: Node 20 / Next.js dev server. Source is bind-mounted in dev;
# node_modules and .next live on named volumes (see docker-compose.yml).

FROM node:20-alpine

WORKDIR /workspace

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

RUN addgroup -S appgroup && adduser -S appuser -G appgroup \
    && chown -R appuser:appgroup /workspace
USER appuser

EXPOSE 3000

CMD ["npx", "next", "dev", "--port", "3000", "--hostname", "0.0.0.0"]
