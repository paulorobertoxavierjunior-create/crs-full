# ============================================================================
# DOCKERFILE - FRONTEND CRS-FULL (PRODUCTION-READY)
# ============================================================================

FROM node:18-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --only=production

COPY . .

# ============================================================================
# PRODUCTION STAGE
# ============================================================================

FROM node:18-alpine

ENV NODE_ENV=production
ENV PORT=3000

WORKDIR /app

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app . .

RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["npm", "start"]