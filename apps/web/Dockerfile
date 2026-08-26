FROM node:22-alpine AS builder

WORKDIR /app
RUN corepack enable

COPY package.json ./
RUN pnpm install --frozen-lockfile=false
COPY . ./
RUN pnpm build

FROM node:22-alpine AS runtime

ENV NODE_ENV=production
WORKDIR /app
RUN addgroup -S app && adduser -S app -G app

COPY --from=builder /app ./
USER app
EXPOSE 3000
CMD ["pnpm", "start"]
