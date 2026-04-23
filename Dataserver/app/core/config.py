"""Configurações da aplicação carregadas via variáveis de ambiente."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _build_db_url() -> str:
    """Monta a URL do Postgres preferindo DATABASE_URL (Replit/produção)."""
    direct = os.getenv("DATABASE_URL")
    if direct:
        return direct
    user = os.getenv("PGUSER", os.getenv("DB_USER", "postgres"))
    pwd = os.getenv("PGPASSWORD", os.getenv("DB_PASS", ""))
    host = os.getenv("PGHOST", os.getenv("DB_HOST", "localhost"))
    port = os.getenv("PGPORT", os.getenv("DB_PORT", "5432"))
    name = os.getenv("PGDATABASE", os.getenv("DB_NAME", "postgres"))
    return f"postgresql://{user}:{pwd}@{host}:{port}/{name}"


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=_build_db_url)
    groq_api_key: str | None = field(default_factory=lambda: os.getenv("GROQ_API_KEY"))

    # Limites operacionais
    max_patients_context: int = 100
    dashboard_chart_limit: int = 10

    # LGPD: colunas que NUNCA podem ir para a IA / contexto
    lgpd_blacklist: tuple[str, ...] = (
        "nome", "cpf", "rg", "telefone", "email", "endereco",
    )

    app_title: str = "Mitra Med — Inteligência Clínica"
    app_version: str = "2.1"


settings = Settings()
