"""Entrypoint compatível com o workflow `uvicorn main:app`.

A aplicação real vive em `app/main.py`. Este arquivo apenas reexporta
para preservar compatibilidade com o workflow do Replit e com o deploy
sem alterar o comando configurado.
"""
from app.main import app  # noqa: F401

__all__ = ["app"]
