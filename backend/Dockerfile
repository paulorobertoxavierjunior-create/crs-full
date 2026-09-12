# ============================================================================
# CRS-FULL — Imagem do backend
# ============================================================================
# Build enxuto, sem compilador, sem root na execução.
# A porta NÃO é fixa: o Render injeta PORT e o gunicorn obedece.
# ============================================================================

FROM python:3.12-slim

# --- Ambiente ---------------------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# --- Dependências -----------------------------------------------------------
# Copiado sozinho para aproveitar o cache de camada: mudar código não
# reinstala bibliotecas a cada deploy.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Código -----------------------------------------------------------------
COPY . .

# --- Usuário sem privilégio ------------------------------------------------
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

# --- Porta ------------------------------------------------------------------
# Documentação da porta padrão. Em produção vale o $PORT do Render.
EXPOSE 5000

# --- Healthcheck ------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\"PORT\",\"5000\")}/health', timeout=4)" || exit 1

# --- Arranque ---------------------------------------------------------------
# 2 workers: cada worker abre conexões próprias no Postgres, e o plano do
# Render tem teto de conexões. Estourar o teto derruba o serviço.
# timeout 120: o boot frio cria tabelas e pode demorar.
CMD gunicorn main:app \
    --bind 0.0.0.0:${PORT:-5000} \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -