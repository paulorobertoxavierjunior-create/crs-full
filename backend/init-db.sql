-- Criar o usuário se não existir
CREATE USER crs_user WITH PASSWORD 'crs_password' CREATEDB;

-- Criar o banco de dados se não existir
CREATE DATABASE crs_db OWNER crs_user;

-- Conectar ao banco
\c crs_db

-- Aqui você pode adicionar mais comandos SQL se precisar