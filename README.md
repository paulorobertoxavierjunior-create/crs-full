# CRS-FULL

Repositório do laboratório. **Em repouso.**

Este código está parado e funcional no Render. Ele não recebe novas
funcionalidades. A evolução da arquitetura acontece no repositório novo,
`crs-core` (privado) — com motor de extração isolado, fila real, relatório
versionado e a Condutora atrás de adaptador de provedor.

## Regra da casa

**Quem mede não fala. Quem fala não mede.**

- **Analista (Elayon 01):** extrai a Trilha Temporal, deriva e compara séries.
  Nunca conversa.
- **Condutora:** recebe texto e relatório, conduz a interação, reflete a
  tonalidade. Nunca vê áudio bruto.
- **Núcleo:** rotas, fila, banco e armazenamento. Não decide nada clínico.

## Estrutura

backend/      Flask + SQLAlchemy + gunicorn
frontend/     entrada, gravação, espera, relatório
docs/         FUNDAMENTOS-CRS.md


## Configuração obrigatória

O serviço **não sobe** sem estas variáveis no painel do Render
(Settings → Environment). Nenhuma tem valor padrão embutido.

| Variável | Obrigatória | Descrição |
|---|---|---|
| `DATABASE_URL` | sim | Postgres. Aceita `postgres://` e `postgresql://`. SQLite não é aceito: o disco do Render é descartável. |
| `SECRET_KEY` | sim | Mínimo 32 caracteres. Assina os tokens JWT. |
| `ALLOWED_ORIGINS` | sim | Origens autorizadas para CORS, separadas por vírgula. Curinga não é aceito. |
| `TOKEN_INTERNO` | não | Se definida, a rota de ingestão passa a exigir o cabeçalho `X-CRS-Token`. |

Gerar um segredo:

python -c "import secrets; print(secrets.token_hex(32))"


O `.env.example` lista todos os nomes de variáveis e **não contém valor
nenhum** — pode ser lido sem risco.

## Rotas

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| GET | `/` | não | índice de endpoints |
| GET | `/health` | não | healthcheck do Render e do Docker |
| POST | `/api/crs/fifo-buffer` | `X-CRS-Token` (se definido) | ingestão de métricas da sessão |
| POST | `/api/auth/registro` | não | cria usuário |
| POST | `/api/auth/login` | não | devolve token JWT (24h) |
| GET | `/api/auth/perfil` | Bearer | dados do usuário |
| GET | `/api/sessoes` | Bearer | lista sessões do usuário |
| GET | `/api/sessoes/<id>` | Bearer | detalhe da sessão |
| POST | `/api/sessoes` | Bearer | cria sessão |
| PUT | `/api/sessoes/<id>` | Bearer | atualiza sessão |
| DELETE | `/api/sessoes/<id>` | Bearer | remove sessão |
| GET | `/api/sessoes/<id>/metricas` | Bearer | métricas da sessão |

## O que foi endurecido nesta versão

| Ponto | Antes | Agora |
|---|---|---|
| Chave secreta | padrão embutido no código | obrigatória, 32+ caracteres |
| Banco | SQLite local | Postgres externo obrigatório |
| CORS | curinga `*` | origens explícitas; `/health` aberto |
| Depuração | `debug=True` | `debug=False` |
| Porta | 5000 fixa | vinda do ambiente |
| Ingestão | aberta | aceita trava por `X-CRS-Token` |
| Tabelas | criadas só fora do gunicorn | criadas na importação |
| Rota de métricas | erro 500 em toda chamada | funcional |

## Limitações conhecidas

- A rota `/api/crs/fifo-buffer` **não é uma fila**. É uma classificação por
  limiar de silêncio. A fila real, com máquina de estados e worker separado,
  pertence ao `crs-core`.
- O vocabulário devolvido pela ingestão ("carga cognitiva") não segue o
  `docs/FUNDAMENTOS-CRS.md`, que define o sistema como **não diagnóstico**.
  Mantido como está para não quebrar o frontend atual; será corrigido no
  repositório novo.
- `backend/models.py` mantém a importação circular `from backend.main import
  db`. Nunca é carregado no Render, então não quebra nada hoje. Marcado para
  revisão.
- As tabelas são criadas por `create_all()`, que só cria o que falta e não
  altera tabela existente. Migrações versionadas (Alembic) ficam para o
  `crs-core`.

## Estado do repositório

- `crs-full` — público. Laboratório. **Parado e estável.**
- `crs-core` — privado. Núcleo novo: motor, fila, relatório e presença.
- `elayon-front` — público. Apenas entrada, gravação, espera e conversa.