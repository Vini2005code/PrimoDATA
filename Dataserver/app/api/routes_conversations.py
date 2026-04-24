"""CRUD HTTP de conversas."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.schemas.chat import NovaConversa, RenomearConversa
from app.services import conversations

router = APIRouter(
    prefix="/api/conversas",
    tags=["conversas"],
)


@router.get("")
async def listar():
    return JSONResponse({"conversas": conversations.listar_conversas()})


@router.post("")
async def criar(req: NovaConversa):
    cid = conversations.criar_conversa(req.titulo or "Nova conversa")
    if not cid:
        raise HTTPException(status_code=500, detail="Não foi possível criar a conversa.")
    return JSONResponse({"id": cid, "titulo": req.titulo or "Nova conversa"})


@router.get("/{conversa_id}")
async def detalhe(conversa_id: int):
    conv = conversations.get_conversa(conversa_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return JSONResponse(conv)


@router.patch("/{conversa_id}")
async def renomear(conversa_id: int, req: RenomearConversa):
    if not conversations.renomear_conversa(conversa_id, req.titulo):
        raise HTTPException(status_code=500, detail="Falha ao renomear.")
    return JSONResponse({"id": conversa_id, "titulo": req.titulo})


@router.delete("/{conversa_id}")
async def deletar(conversa_id: int):
    if not conversations.deletar_conversa(conversa_id):
        raise HTTPException(status_code=500, detail="Falha ao deletar.")
    return JSONResponse({"ok": True, "id": conversa_id})
