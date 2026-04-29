"""Configurações da aplicação carregadas via variáveis de ambiente."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _components_db_url() -> str | None:
    """Monta URL a partir de variáveis individuais (PG* / DB_*)."""
    user = os.getenv("PGUSER", os.getenv("DB_USER"))
    host = os.getenv("PGHOST", os.getenv("DB_HOST"))
    name = os.getenv("PGDATABASE", os.getenv("DB_NAME"))
    if not (user and host and name):
        return None
    pwd = os.getenv("PGPASSWORD", os.getenv("DB_PASS", ""))
    port = os.getenv("PGPORT", os.getenv("DB_PORT", "5432"))
    return f"postgresql://{user}:{pwd}@{host}:{port}/{name}"


def _primary_db_url() -> str | None:
    """Banco preferencial: PostgreSQL externo do cliente (Primordial)."""
    return os.getenv("PRIMORDIAL_DATABASE_URL")


def _fallback_db_url() -> str | None:
    """Banco de fallback: PostgreSQL gerenciado pelo Replit."""
    return os.getenv("DATABASE_URL") or _components_db_url()


def _build_db_url() -> str:
    """URL ativa: primário se disponível, senão fallback. Não testa conexão."""
    return _primary_db_url() or _fallback_db_url() or "postgresql://postgres@localhost:5432/postgres"


@dataclass(frozen=True)
class Settings:
    # URL ativa (back-compat). O fallback automático em caso de falha de
    # conexão é feito em `app.db.engine` no momento da criação do engine.
    database_url: str = field(default_factory=_build_db_url)
    primary_database_url: str | None = field(default_factory=_primary_db_url)
    fallback_database_url: str | None = field(default_factory=_fallback_db_url)

    groq_api_key: str | None = field(default_factory=lambda: os.getenv("GROQ_API_KEY"))

    # Limites operacionais
    max_patients_context: int = 100
    dashboard_chart_limit: int = 10
    chart_max_points: int = 200
    chart_label_max_len: int = 120
    schema_cache_ttl: int = 60

    # LGPD: colunas que NUNCA podem ir para a IA / contexto
    lgpd_blacklist: tuple[str, ...] = (
        "nome", "cpf", "rg", "telefone", "email", "endereco", "endereço",
        "profissao", "profissão", "naturalidade", "mae", "mãe", "pai",
        "responsavel", "responsável", "observacoes", "observações",
        "anamnese", "prontuario", "prontuário",
    )

    app_title: str = "Primordial Data — Inteligência Clínica"
    app_version: str = "2.2"


settings = Settings()
