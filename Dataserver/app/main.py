"""Bootstrap da aplicação FastAPI Mitra Med."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import (
    routes_auth,
    routes_chat,
    routes_conversations,
    routes_dashboard,
)
from app.api.deps import current_user
from app.core.config import settings
from app.core.logging_setup import get_logger, setup_logging
from app.db.schema import init_schema
from app.services import patients
from app.services.auth import bootstrap_admin

setup_logging()
logger = get_logger(__name__)

# Resolve paths relativos ao diretório `Dataserver/` para que o app
# funcione independente do CWD em que for chamado.
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TEMPLATES_DIR = os.path.join(_BASE_DIR, "templates")
_STATIC_DIR = os.path.join(_BASE_DIR, "static")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    logger.info("Inicializando schema do banco...")
    try:
        init_schema()
    except Exception as e:
        logger.error(f"Schema NÃO inicializado: {e}")
    if settings.auth_enabled:
        try:
            bootstrap_admin()
        except Exception as e:
            logger.error(f"Bootstrap de admin falhou: {e}")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
    templates = Jinja2Templates(directory=_TEMPLATES_DIR)

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request, user: dict | None = Depends(current_user)):
        if settings.auth_enabled and not user:
            return RedirectResponse(url="/login", status_code=302)
        try:
            metricas = patients.dashboard_metrics()
        except Exception as e:
            logger.error(f"Erro ao carregar dashboard: {e}")
            metricas = {
                "total_pacientes": 0, "media_idade": 0,
                "ativos": 0, "diagnosticos_unicos": 0,
            }
        ctx = dict(metricas)
        ctx["current_user"] = (user or {}).get("username", "")
        return templates.TemplateResponse(
            request=request, name="index.html", context=ctx
        )

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, user: dict | None = Depends(current_user)):
        if user:
            return RedirectResponse(url="/", status_code=302)
        return templates.TemplateResponse(request=request, name="login.html", context={})

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok", "version": settings.app_version}

    app.include_router(routes_auth.router)
    app.include_router(routes_chat.router)
    app.include_router(routes_conversations.router)
    app.include_router(routes_dashboard.router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=5000, reload=True)
