FROM node:18-alpine

WORKDIR /app

# Copiar package.json e package-lock.json PRIMEIRO
COPY package*.json ./

# Instalar dependências
RUN npm install

# Copiar arquivos do frontend
COPY . .

# Expor porta
EXPOSE 3000

# Comando de inicialização
CMD ["npm", "start"]