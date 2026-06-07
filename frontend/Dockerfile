# ============================================================================
# DOCKERFILE - FRONTEND CRS-FULL (PRODUCTION-READY)
# ============================================================================

FROM node:18-alpine AS builder

# ============================================================================
# BUILD STAGE
# ============================================================================

WORKDIR /app

# Copiar arquivos
COPY package.json package-lock.json* ./

# Instalar dependências
RUN npm ci --only=production

# Copiar código
COPY . .

# ============================================================================
# PRODUCTION STAGE
# ============================================================================

FROM node:18-alpine

ENV NODE_ENV=production
ENV PORT=3000

WORKDIR /app

# Copiar node_modules do builder
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app . .

# ============================================================================
# USUÁRIO NÃO-ROOT (SEGURANÇA)
# ============================================================================

RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

USER nextjs

# ============================================================================
# PORTA & HEALTH CHECK
# ============================================================================

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

CMD ["npm", "start"]