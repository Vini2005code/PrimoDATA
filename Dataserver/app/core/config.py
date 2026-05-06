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


def _bool_env(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=_build_db_url)
    groq_api_key: str | None = field(default_factory=lambda: os.getenv("GROQ_API_KEY"))

    # Limites operacionais
    # Usado pelo get_clinical_context() ao montar o contexto clínico para a IA.
    max_patients_context: int = 1000
    dashboard_chart_limit: int = 10

    # Usado por schemas/chat.py para validar tamanho de labels/values.
    # Também limita payload de pontos que chegam ao frontend/PDF.
    chart_max_points: int = 1000
    chart_label_max_len: int = 120
    schema_cache_ttl: int = 60

    # LGPD: colunas que NUNCA podem ir para a IA / contexto
    lgpd_blacklist: tuple[str, ...] = (
        "nome", "cpf", "rg", "telefone", "email", "endereco", "endereço",
        "profissao", "profissão", "naturalidade", "mae", "mãe", "pai",
        "responsavel", "responsável", "observacoes", "observações",
        "anamnese", "prontuario", "prontuário",
    )

    # Autenticação
    auth_enabled: bool = field(default_factory=lambda: _bool_env("AUTH_ENABLED", True))
    jwt_secret: str | None = field(default_factory=lambda: os.getenv("JWT_SECRET"))
    jwt_expire_minutes: int = field(
        default_factory=lambda: int(os.getenv("JWT_EXPIRE_MINUTES", "720"))
    )
    cookie_secure: bool = field(default_factory=lambda: _bool_env("COOKIE_SECURE", False))
    admin_username: str | None = field(default_factory=lambda: os.getenv("ADMIN_USERNAME"))
    admin_password: str | None = field(default_factory=lambda: os.getenv("ADMIN_PASSWORD"))

    app_title: str = "Mitra Med — Inteligência Clínica"
    app_version: str = "2.2"


settings = Settings()
