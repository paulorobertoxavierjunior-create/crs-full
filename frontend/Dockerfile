# Use uma imagem base do Nginx, que é leve e eficiente para servir arquivos estáticos.
FROM nginx:alpine

# Copie todos os arquivos da pasta 'frontend' (onde este Dockerfile está)
# para o diretório padrão do Nginx para servir conteúdo estático.
# Isso inclui seus arquivos HTML, CSS, JS e quaisquer outros recursos.
COPY . /usr/share/nginx/html

# O Nginx por padrão já expõe a porta 80.
# Não precisamos de um comando EXPOSE explícito aqui, pois o Nginx já faz isso.

# O Nginx já tem um comando padrão para iniciar o servidor.
# Não precisamos de um CMD explícito aqui, a menos que você queira uma configuração muito específica.