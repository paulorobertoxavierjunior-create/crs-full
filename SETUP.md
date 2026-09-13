# SETUP — Elayon Platform (Setor 1: Configuração de Segurança)

Esse guia te leva do zero até ter o backend rodando localmente com Supabase conectado e todas as IA catalogadas.

---

## 📋 O que você vai precisar

- Conta **Supabase** (grátis em supabase.com)
- **Python 3.9+** instalado
- **Git** instalado
- Uma chave de IA gratuita (Gemini recomendado, tem tier grátis bom)
- **Postgres** localmente OU usar Supabase como banco remoto (mais fácil)

---

## 🚀 PASSO 1: Clonar e Preparar Ambiente Local

```bash
git clone https://github.com/paulorobertoxavierjunior-create/crs-full.git
cd crs-full
python -m venv venv

# No macOS/Linux:
source venv/bin/activate

# No Windows:
venv\Scripts\activate

pip install -r requirements.txt