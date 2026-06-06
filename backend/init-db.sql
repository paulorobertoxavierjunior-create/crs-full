-- Criar usuário se não existir
DO
$$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'crs_user') THEN
        CREATE USER crs_user WITH PASSWORD 'crs_password' CREATEDB;
    END IF;
END
$$;

-- Garantir permissões
ALTER USER crs_user CREATEDB;

-- Criar banco de dados se não existir
SELECT 'CREATE DATABASE crs_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'crs_db')\gexec

-- Conceder permissões
GRANT ALL PRIVILEGES ON DATABASE crs_db TO crs_user;