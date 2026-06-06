-- Criar o usuário se não existir
CREATE USER crs_user WITH PASSWORD 'crs_password';

-- Criar o banco de dados
CREATE DATABASE crs_db OWNER crs_user;

-- Conectar ao banco e conceder permissões
\c crs_db

-- Conceder todas as permissões ao usuário
GRANT ALL PRIVILEGES ON DATABASE crs_db TO crs_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO crs_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO crs_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO crs_user;