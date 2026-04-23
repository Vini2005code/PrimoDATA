"""Rotas de autenticação (login / logout / me)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import COOKIE_NAME, current_user
from app.core.config import settings
from app.core.security import create_token
from app.schemas.chat import LoginIn
from app.services.auth import authenticate

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(req: LoginIn, response: Response):
    user = authenticate(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos.",
        )
    token = create_token(subject=user["username"])
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return {"ok": True, "user": user}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
async def me(user: dict | None = Depends(current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    return user
