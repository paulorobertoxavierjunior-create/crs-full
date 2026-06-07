# ============================================================================
# CRS-FULL — AUTO-ANÁLISE DO SISTEMA
# ============================================================================

Write-Host "🔊 CRS-FULL — CHECK GERAL DO SISTEMA" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# 1. VERIFICAR ESTRUTURA DE PASTAS
# ============================================================================

Write-Host "📁 VERIFICANDO ESTRUTURA DE PASTAS..." -ForegroundColor Yellow

$pastas = @(
    "backend",
    "frontend",
    "backend/venv",
    "backend/__pycache__"
)

foreach ($pasta in $pastas) {
    if (Test-Path $pasta) {
        Write-Host "  ✅ $pasta — OK" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $pasta — NÃO ENCONTRADA" -ForegroundColor Red
    }
}

Write-Host ""

# ============================================================================
# 2. VERIFICAR ARQUIVOS CRÍTICOS
# ============================================================================

Write-Host "📄 VERIFICANDO ARQUIVOS CRÍTICOS..." -ForegroundColor Yellow

$arquivos = @(
    "backend/main.py",
    "backend/.env",
    "backend/requirements.txt",
    "frontend/index.html",
    "frontend/dashboard.html",
    "frontend/gravacao.html",
    "frontend/relatorio.html",
    "frontend/chat.html",
    "docker-compose.yml",
    ".gitignore"
)

foreach ($arquivo in $arquivos) {
    if (Test-Path $arquivo) {
        $tamanho = (Get-Item $arquivo).Length
        Write-Host "  ✅ $arquivo — OK ($tamanho bytes)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $arquivo — NÃO ENCONTRADO" -ForegroundColor Red
    }
}

Write-Host ""

# ============================================================================
# 3. VERIFICAR PYTHON
# ============================================================================

Write-Host "🐍 VERIFICANDO PYTHON..." -ForegroundColor Yellow

try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✅ Python instalado: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Python NÃO INSTALADO" -ForegroundColor Red
}

Write-Host ""

# ============================================================================
# 4. VERIFICAR DEPENDÊNCIAS
# ============================================================================

Write-Host "📦 VERIFICANDO DEPENDÊNCIAS..." -ForegroundColor Yellow

if (Test-Path "backend/requirements.txt") {
    $deps = @(
        "flask",
        "flask-cors",
        "flask-sqlalchemy",
        "pyjwt",
        "werkzeug"
    )
    
    foreach ($dep in $deps) {
        try {
            $check = python -m pip show $dep 2>&1
            if ($check) {
                Write-Host "  ✅ $dep — INSTALADO" -ForegroundColor Green
            } else {
                Write-Host "  ⚠️  $dep — NÃO INSTALADO (execute: pip install -r requirements.txt)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  ⚠️  $dep — NÃO INSTALADO" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  ❌ requirements.txt NÃO ENCONTRADO" -ForegroundColor Red
}

Write-Host ""

# ============================================================================
# 5. VERIFICAR PORTAS
# ============================================================================

Write-Host "🔌 VERIFICANDO PORTAS..." -ForegroundColor Yellow

$portas = @(
    @{porta = 5000; servico = "Backend (Flask)"},
    @{porta = 3000; servico = "Frontend (Node)"},
    @{porta = 5432; servico = "PostgreSQL"}
)

foreach ($item in $portas) {
    $porta = $item.porta
    $servico = $item.servico
    
    try {
        $conexao = Test-NetConnection -ComputerName localhost -Port $porta -WarningAction SilentlyContinue
        if ($conexao.TcpTestSucceeded) {
            Write-Host "  ⚠️  Porta $porta ($servico) — EM USO" -ForegroundColor Yellow
        } else {
            Write-Host "  ✅ Porta $porta ($servico) — DISPONÍVEL" -ForegroundColor Green
        }
    } catch {
        Write-Host "  ✅ Porta $porta ($servico) — DISPONÍVEL" -ForegroundColor Green
    }
}

Write-Host ""

# ============================================================================
# 6. VERIFICAR .env
# ============================================================================

Write-Host "🔐 VERIFICANDO .env..." -ForegroundColor Yellow

if (Test-Path "backend/.env") {
    $envContent = Get-Content "backend/.env"
    $keys = @(
        "DATABASE_URL",
        "SECRET_KEY",
        "JWT_EXPIRATION_HOURS",
        "FLASK_ENV",
        "DEBUG"
    )
    
    foreach ($key in $keys) {
        if ($envContent -match $key) {
            Write-Host "  ✅ $key — CONFIGURADO" -ForegroundColor Green
        } else {
            Write-Host "  ❌ $key — NÃO CONFIGURADO" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  ❌ .env NÃO ENCONTRADO" -ForegroundColor Red
}

Write-Host ""

# ============================================================================
# 7. RESUMO FINAL
# ============================================================================

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "✅ CHECK CONCLUÍDO!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "🚀 PRÓXIMOS PASSOS:" -ForegroundColor Cyan
Write-Host "  1. cd backend"
Write-Host "  2. python -m venv venv"
Write-Host "  3. .\venv\Scripts\Activate"
Write-Host "  4. pip install -r requirements.txt"
Write-Host "  5. python main.py"
Write-Host ""