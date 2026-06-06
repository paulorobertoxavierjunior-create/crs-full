FROM node:18-alpine

WORKDIR /app

# Copiar package.json e package-lock.json
COPY package*.json ./

# Instalar dependências
RUN npm install

# Copiar arquivos do frontend
COPY . .

# Build (se necessário)
RUN npm run build 2>/dev/null || true

# Expor porta
EXPOSE 3000

# Comando de inicialização
CMD ["npm", "start"]