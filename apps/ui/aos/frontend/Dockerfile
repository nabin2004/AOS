FROM oven/bun:1.2-alpine AS base

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app

# Copy package files (supports bun.lock, bun.lockb, or package-lock.json)
COPY package.json package-lock.json* bun.lock* ./

# Install dependencies (ignoring dev lifecycle scripts like husky)
RUN if [ -f bun.lock ] || [ -f bun.lockb ]; then \
      bun install --frozen-lockfile --ignore-scripts; \
    else \
      bun install --ignore-scripts; \
    fi


# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build arguments for environment variables. NEXT_PUBLIC_* are inlined into the
# client bundle at build time, and .env.local is dockerignored, so they must be
# passed as build args (see docker-compose.frontend.yml) or the browser bundle
# bakes in stale defaults.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL=ws://localhost:8000
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
ARG NEXT_PUBLIC_SITE_URL=http://localhost:3000
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
ARG NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB=50
ENV NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB=$NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB
ARG NEXT_PUBLIC_OAUTH_PROVIDERS=google
ENV NEXT_PUBLIC_OAUTH_PROVIDERS=$NEXT_PUBLIC_OAUTH_PROVIDERS
ARG NEXT_PUBLIC_RAG_ENABLED=false
ENV NEXT_PUBLIC_RAG_ENABLED=$NEXT_PUBLIC_RAG_ENABLED

# Build the application
ENV NEXT_TELEMETRY_DISABLED=1
RUN bun run build

# Production image
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs -G nodejs

COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs


EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["bun", "server.js"]
