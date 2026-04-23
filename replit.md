# PrimoDATA / Mitra Med

FastAPI + PostgreSQL clinical analytics dashboard with Groq-powered AI ("Mitra Med").

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
      logging_setup.py
    db/
      engine.py                 # SQLAlchemy engine
      schema.py                 # DDL idempotente (init_schema)
    services/
      patients.py               # leitura de `pacientes` + métricas (LGPD-safe)
      conversations.py          # CRUD conversas/mensagens + plano_to_chart_data
      dashboard_charts.py       # CRUD gráficos fixados (limite 10)
      ai_engine.py              # cliente Groq + planejar_grafico
      chart_render.py           # matplotlib base64 (compat)
      pdf_report.py             # gerar_pdf_dashboard + gerar_pdf_chart
    api/
      routes_chat.py            # POST /api/analisar
      routes_conversations.py   # /api/conversas (CRUD)
      routes_dashboard.py       # /api/dashboard/* (charts + PDFs)
    schemas/
      chat.py                   # Pydantic models
  templates/, static/
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

## Running
Workflow `Start application` (sem alteração após o refactor):
`cd Dataserver && python -m uvicorn main:app --host 0.0.0.0 --port 5000`

O `main.py` no topo é apenas um re-export de `app.main:app`.

## Deployment
Configured for `autoscale` com o mesmo comando uvicorn.
