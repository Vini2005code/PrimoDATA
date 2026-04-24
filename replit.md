# Primordial Data

FastAPI + PostgreSQL clinical analytics dashboard with Groq-powered AI ("Primordial Data").

## Stack
- Python 3.12, FastAPI, Uvicorn
- PostgreSQL (Replit-managed; uses `DATABASE_URL`)
- SQLAlchemy 2, Pandas, Matplotlib, Seaborn
- Groq SDK (llama-3.3) — requires `GROQ_API_KEY` secret
- ReportLab (PDF), Pydantic v2
- Frontend: server-rendered Jinja2 + Chart.js (CDN) + vanilla JS/CSS

## Layout (refatorado v2.1)
```
Dataserver/
  main.py                       # shim: from app.main import app
  requirements.txt
  app/
    main.py                     # FastAPI factory + lifespan
    core/
      config.py                 # Settings (env-driven, immutable)
      cache.py                  # ttl_cache decorator
      logging_setup.py
    db/
      engine.py                 # SQLAlchemy engine
      schema.py                 # DDL idempotente (init_schema)
    services/
      patients.py               # leitura de `pacientes` + métricas (LGPD-safe; schema cache 60s)
      conversations.py          # CRUD conversas/mensagens + plano_to_chart_data
      dashboard_charts.py       # CRUD gráficos fixados (limite 10)
      ai_engine.py              # cliente Groq + planejar_grafico (PII mask + audit log)
      chart_render.py           # matplotlib base64 (compat)
      pdf_report.py             # gerar_pdf_dashboard + gerar_pdf_chart (rodam em threadpool)
    api/
      routes_chat.py            # POST /api/analisar
      routes_conversations.py   # /api/conversas (CRUD)
      routes_dashboard.py       # /api/dashboard/* (charts + PDFs)
    schemas/
      chat.py                   # Pydantic models (ChartDataIn validado)
  templates/                    # index.html (logo: /static/img/logo.png)
  static/
    style.css
    img/logo.png                # logo oficial PrimoDATA
  _disabled/                    # NÃO importado pelo app — cofre p/ reativação
    README.md
    auth/                       # sistema JWT desativado em 24/04/2026
      api/{routes_auth.py, deps.py}
      services/auth.py
      core/security.py
      templates/login.html
```

## Endpoints
- `GET  /` — dashboard inicial
- `GET  /healthz`
- `POST /api/analisar` — chat com IA, persiste e devolve chartData
- `GET/POST/PATCH/DELETE /api/conversas[/{id}]`
- `GET/POST/DELETE /api/dashboard/charts[/{id}]` — gráficos fixados (máx 10)
- `GET  /api/dashboard/export-pdf` — PDF consolidado
- `GET  /api/dashboard/charts/{id}/export-pdf` — PDF de gráfico fixado
- `POST /api/dashboard/charts/export-pdf` — PDF de gráfico individual (chat)
- `GET  /api/reports/meta` — campos seguros, group_by, formatos, mês corrente
- `POST /api/reports/preview` — relatório do mês atual em JSON
- `POST /api/reports/export?format=csv|json|xml|pdf` — download do relatório

## Aba "Relatórios Primordial" (adicionada em 24/04/2026)
- Escopo SEMPRE = mês corrente (`date_trunc('month', CURRENT_DATE)`).
- 3 modos de dado: `bruto` (linhas), `agregado` (GROUP BY count), `metrica` (KPIs).
- Filtros opcionais: `status`, `convenio` (IN parametrizado).
- Hard-cap servidor: 1000 linhas (Pydantic ge=1, le=1000).
- LGPD em camada dupla: whitelist de campos (`sanitize.allowed_fields()`) + rejeição
  explícita 422 se algum campo da blacklist for solicitado, com log no canal
  `primordial.lgpd.audit`. Blacklist vem de `settings.lgpd_blacklist` (CPF, RG,
  nome, telefone, email, endereço, prontuário, etc — todos bloqueados).
- 4 exporters: CSV (BOM UTF-8), JSON (ensure_ascii=False), XML (ElementTree),
  PDF (reusa estilos de `pdf_report.py`, roda em `run_in_threadpool`).
- Auth ainda DESATIVADA (igual ao restante). Para reativar: adicionar
  `dependencies=[Depends(require_user)]` no `APIRouter` de `routes_reports.py`.
- Arquivos novos:
  - `app/schemas/reports.py`
  - `app/services/reports/{__init__,sanitize,query}.py`
  - `app/services/exporters/{__init__,csv,json,xml,pdf}_exporter.py`
  - `app/api/routes_reports.py`

## Running
Workflow `Start application` (sem alteração após o refactor):
`cd Dataserver && python -m uvicorn main:app --host 0.0.0.0 --port 5000`

O `main.py` no topo é apenas um re-export de `app.main:app`.

## Deployment
Configured for `autoscale` com o mesmo comando uvicorn.
