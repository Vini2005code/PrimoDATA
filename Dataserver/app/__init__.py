"""Primordial Data — pacote da aplicação FastAPI.

Estrutura:
    core/       configuração, logging
    db/         engine SQLAlchemy + DDL
    services/   regras de negócio (pacientes, conversas, IA, gráficos, PDF)
    api/        rotas HTTP (chat, conversas, dashboard, charts)
    schemas/    modelos Pydantic
"""
