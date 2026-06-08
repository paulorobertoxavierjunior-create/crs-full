# ============================================================================
# DOCKERFILE - FRONTEND CRS-FULL (PRODUCTION-READY)
# ============================================================================

# --- STAGE 1: BUILD THE FRONTEND APPLICATION ---
FROM node:18-alpine AS builder

WORKDIR /app

# Copia os arquivos de configuração do projeto (package.json, package-lock.json)
COPY package.json package-lock.json* ./

# Instala as dependências de desenvolvimento e produção para o build
# Se o seu projeto React/Next/Vue usa 'npm install' para tudo, use apenas 'npm install'
# Se 'npm ci --only=production' não instala as dependências de build, mude para 'npm install'
RUN npm ci

# Copia todo o código fonte do frontend
COPY . .

# Executa o comando de build do seu frontend
# Este comando cria os arquivos estáticos (HTML, CSS, JS) que serão servidos
# Geralmente é 'npm run build' para React/Vue ou 'next build' para Next.js
# VERIFIQUE SEU package.json PARA O COMANDO CORRETO DE BUILD!
RUN npm run build

# --- STAGE 2: SERVE THE BUILT FRONTEND APPLICATION ---
# Usaremos uma imagem Nginx leve para servir os arquivos estáticos gerados no estágio 'builder'
FROM nginx:alpine

# Define o diretório de trabalho dentro do contêiner
WORKDIR /usr/share/nginx/html

# Remove a configuração padrão do Nginx para evitar conflitos
RUN rm /etc/nginx/conf.d/default.conf

# Copia uma configuração Nginx personalizada (se você tiver uma)
# Se não tiver, o Nginx servirá os arquivos estáticos por padrão.
# Se precisar de uma configuração específica, crie um arquivo 'nginx.conf' na pasta 'frontend'
# e adicione: COPY ./frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Copia os arquivos estáticos (gerados pelo 'npm run build') do estágio 'builder'
# para o diretório de serviço do Nginx.
# O caminho '/app/build' ou '/app/dist' depende de onde seu 'npm run build' salva os arquivos.
# VERIFIQUE ONDE SEU COMANDO DE BUILD SALVA OS ARQUIVOS!
# Exemplo para React: /app/build
# Exemplo para Next.js: /app/.next/static (e talvez outros arquivos)
# Exemplo para Vue: /app/dist
COPY --from=builder /app/build /usr/share/nginx/html

# Expõe a porta 80, que é a porta padrão do Nginx
EXPOSE 80

# Comando para iniciar o Nginx
CMD ["nginx", "-g", "daemon off;"]