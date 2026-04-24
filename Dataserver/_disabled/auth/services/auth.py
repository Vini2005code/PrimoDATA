"""Gestão de usuários (CRUD mínimo) e bootstrap do admin inicial."""
from __future__ import annotations

from sqlalchemy import text

from app.core.config import settings
from app.core.logging_setup import get_logger
from app.core.security import hash_password, verify_password
from app.db.engine import engine

logger = get_logger(__name__)


def get_user(username: str) -> dict | None:
    if not username:
        return None
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT id, username, password_hash, criado_em "
                    "FROM usuarios WHERE username = :u"
                ),
                {"u": username.lower()},
            ).fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "username": row[1],
                "password_hash": row[2],
                "criado_em": row[3].isoformat() if row[3] else None,
            }
    except Exception as e:
        logger.error(f"Erro ao buscar usuário {username}: {e}")
        return None


def create_user(username: str, password: str) -> int | None:
    try:
        with engine.begin() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO usuarios (username, password_hash) "
                    "VALUES (:u, :p) RETURNING id"
                ),
                {"u": username.lower(), "p": hash_password(password)},
            ).fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"Erro ao criar usuário {username}: {e}")
        return None


def authenticate(username: str, password: str) -> dict | None:
    u = get_user(username)
    if not u:
        return None
    if not verify_password(password, u["password_hash"]):
        return None
    return {"id": u["id"], "username": u["username"]}


def bootstrap_admin() -> None:
    """Garante que pelo menos um usuário admin exista.

    - Se ADMIN_USERNAME/ADMIN_PASSWORD estão setados → cria/atualiza esse user.
    - Caso contrário, e se a tabela está vazia → cria 'admin/admin' com aviso.
    """
    try:
        with engine.connect() as conn:
            total = conn.execute(text("SELECT COUNT(*) FROM usuarios")).scalar() or 0
    except Exception as e:
        logger.error(f"Falha ao contar usuários: {e}")
        return

    user = settings.admin_username
    pwd = settings.admin_password

    if user and pwd:
        existing = get_user(user)
        if not existing:
            create_user(user, pwd)
            logger.info(f"Admin '{user}' criado a partir de variáveis de ambiente.")
        return

    if total == 0:
        create_user("admin", "admin")
        logger.warning(
            "============================================================\n"
            "  USUÁRIO ADMIN PADRÃO criado: admin / admin\n"
            "  Defina ADMIN_USERNAME e ADMIN_PASSWORD em produção\n"
            "  ou troque a senha logando e atualizando o registro.\n"
            "============================================================"
        )
