# ============================================================================
# DOCKERFILE - BACKEND CRS-FULL (PRODUCTION-READY)
# ============================================================================

FROM python:3.11-slim

# ============================================================================
# VARIÁVEIS DE AMBIENTE
# ============================================================================

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=main.py
ENV FLASK_ENV=production

# ============================================================================
# SETUP
# ============================================================================

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# DEPENDÊNCIAS PYTHON
# ============================================================================

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================================
# CÓDIGO DA APLICAÇÃO
# ============================================================================

COPY . .

# ============================================================================
# USUÁRIO NÃO-ROOT (SEGURANÇA)
# ============================================================================

RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# ============================================================================
# PORTA & HEALTH CHECK
# ============================================================================

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')" || exit 1

# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "main:app"]