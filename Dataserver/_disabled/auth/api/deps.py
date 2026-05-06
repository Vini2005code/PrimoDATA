"""Dependências comuns das rotas (autenticação)."""
from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status

from app.core.config import settings
from app.core.security import decode_token
from app.services.auth import get_user

COOKIE_NAME = "primordial_session"


def current_user(
    session_cookie: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> dict | None:
    """Retorna o usuário logado ou None. NÃO levanta exceção."""
    if not settings.auth_enabled:
        return {"id": 0, "username": "anonymous"}
    if not session_cookie:
        return None
    payload = decode_token(session_cookie)
    if not payload or not payload.get("sub"):
        return None
    user = get_user(payload["sub"])
    if not user:
        return None
    return {"id": user["id"], "username": user["username"]}


def require_user(user: dict | None = Depends(current_user)) -> dict:
    """Igual a current_user, mas levanta 401 se não autenticado."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado.",
        )
    return user
