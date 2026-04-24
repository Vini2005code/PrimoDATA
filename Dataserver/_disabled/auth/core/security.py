"""Hash de senhas + emissão/validação de JWT."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.logging_setup import get_logger

logger = get_logger(__name__)

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Se JWT_SECRET não foi definido, gera um secret efêmero (sessões caem em
# cada restart). Em produção SEMPRE definir via env.
_SECRET = settings.jwt_secret or secrets.token_urlsafe(48)
if not settings.jwt_secret:
    logger.warning(
        "JWT_SECRET ausente — usando secret efêmero. "
        "Defina a variável de ambiente JWT_SECRET em produção."
    )

_ALGO = "HS256"


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd.verify(plain, hashed)
    except Exception:
        return False


def create_token(subject: str, expires_minutes: int | None = None) -> str:
    exp_min = expires_minutes or settings.jwt_expire_minutes
    payload = {
        "sub": subject,
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=exp_min),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGO)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _SECRET, algorithms=[_ALGO])
    except jwt.PyJWTError as e:
        logger.debug(f"Token inválido: {e}")
        return None
