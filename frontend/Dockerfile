FROM node:18-alpine

WORKDIR /app

# Copiar package.json e package-lock.json
COPY package*.json ./

# Instalar dependências (incluindo http-server)
RUN npm install

# Copiar arquivos do frontend
COPY . .

# Expor porta
EXPOSE 3000

# Comando para rodar
CMD ["npm", "start"]