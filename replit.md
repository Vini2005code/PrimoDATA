# PrimoDATA

FastAPI + PostgreSQL clinical analytics dashboard with Groq-powered AI ("Mitra Med").

## Stack
- Python 3.12, FastAPI, Uvicorn
- PostgreSQL (Replit-managed; uses `DATABASE_URL`)
- SQLAlchemy, Pandas, Matplotlib, Seaborn
- Groq SDK (llama-3.3) — requires `GROQ_API_KEY` secret
- Frontend: server-rendered Jinja2 template + static JS/CSS

## Layout
- `Dataserver/` — main application
  - `main.py` — FastAPI app (entrypoint)
  - `database.py` — SQLAlchemy queries on `pacientes` table
  - `Analise_primo.py` — Groq AI engine (lazy client init)
  - `config.py` — reads `DATABASE_URL` / PG* env vars with fallback
  - `templates/`, `static/`
- `java-core/`, `legacy/` — auxiliary code, not run

## Running
Workflow `Start application` runs:
`cd Dataserver && uvicorn main:app --host 0.0.0.0 --port 5000`

## Database
A `pacientes` table is auto-created and seeded with sample anonymized rows
(columns: id, nome, idade, sexo, diagnostico, convenio, status, data_admissao).

## Deployment
Configured for `autoscale` with the same uvicorn command.
