# `_disabled/` — código guardado para reativação futura

Esta pasta NÃO é importada pelo aplicativo. É um cofre de arquivos
prontos para serem religados quando for o momento certo.

## `_disabled/auth/` — sistema de login JWT (desativado em 24/04/2026)

Estrutura espelha o pacote `app/`:

```
_disabled/auth/
├── api/
│   ├── routes_auth.py    → ia para app/api/  (rotas /api/auth/login|logout|me)
│   └── deps.py           → ia para app/api/  (current_user, require_user)
├── services/
│   └── auth.py           → ia para app/services/  (CRUD usuários, bootstrap_admin)
├── core/
│   └── security.py       → ia para app/core/  (bcrypt + PyJWT)
└── templates/
    └── login.html        → ia para templates/
```

### Para REATIVAR

1. Mova cada arquivo de volta para o caminho-espelho dentro de `Dataserver/app/`
   (ou `Dataserver/templates/` para o `login.html`).
2. Em `Dataserver/app/main.py`:
   - Reimporte `routes_auth`, `current_user`, `bootstrap_admin`.
   - Adicione `bootstrap_admin()` ao `lifespan`.
   - Reinclua a rota `GET /login` e o redirect em `GET /` para usuários não autenticados.
   - Reinclua `app.include_router(routes_auth.router)`.
3. Em `routes_chat.py`, `routes_conversations.py`, `routes_dashboard.py`:
   - Reimporte `require_user` e adicione `Depends(require_user)` (router-level
     ou por endpoint).
4. Defina os secrets em produção: `JWT_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`,
   `COOKIE_SECURE=true`.

A tabela `usuarios` no banco continua sendo criada idempotentemente por
`db/schema.py` — não precisa de migração ao reativar.

Os settings de auth (`auth_enabled`, `jwt_*`, `admin_*`, `cookie_secure`) seguem
declarados em `app/core/config.py`, então `Settings` já aceita esses valores.
