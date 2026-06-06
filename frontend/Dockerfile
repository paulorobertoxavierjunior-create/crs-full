FROM node:18-alpine

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install -g http-server && npm install

COPY . .

EXPOSE 3000

CMD ["http-server", "-p", "3000", "-c-1"]