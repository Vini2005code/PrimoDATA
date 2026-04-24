"""Rotas de análise/chat com a IA."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.logging_setup import get_logger
from app.schemas.chat import RequisicaoChat
from app.services import ai_engine, conversations, patients
from app.services.chart_render import gerar_imagem_grafico

logger = get_logger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/api/analisar")
async def api_analisar(req: RequisicaoChat):
    """Recebe pergunta → consulta banco → IA decide (texto ou texto+gráfico)
    → persiste no histórico → devolve resposta padronizada.
    """
    try:
        logger.info(f"Pergunta: {req.message[:120]}")

        # 1. Garante uma conversa
        conversa_id = req.conversa_id
        if not conversa_id:
            titulo_inicial = (req.message or "Nova conversa").strip()[:60] or "Nova conversa"
            conversa_id = conversations.criar_conversa(titulo_inicial)

        if conversa_id:
            conversations.adicionar_mensagem(conversa_id, "user", req.message)

        # 2. Contexto anonimizado + IA
        contexto = patients.get_clinical_context()
        plano = ai_engine.planejar_grafico(contexto, req.message)

        # 3. Imagem inline (compat) + chartData estruturado
        url_imagem = None
        tipo = plano.get("tipo_grafico")
        if tipo and tipo != "null":
            url_imagem = gerar_imagem_grafico(plano)
        chart_data = conversations.plano_to_chart_data(plano)

        # 4. Persiste resposta do assistente
        if conversa_id:
            conversations.adicionar_mensagem(
                conversa_id,
                "assistant",
                plano.get("analise", "Análise concluída."),
                chart_data=chart_data,
                sugestao=plano.get("sugestao"),
            )

        # 5. Resposta padronizada (novo schema + legados)
        return JSONResponse({
            "conversa_id": conversa_id,
            "analise": plano.get("analise", "Análise concluída."),
            "title": plano.get("titulo"),
            "type": tipo if tipo and tipo != "null" else None,
            "labels": plano.get("eixo_x") or [],
            "values": plano.get("valores") or [],
            "suggested_insight": plano.get("suggested_insight") or plano.get("sugestao"),
            # Legado:
            "tipo_grafico": tipo,
            "titulo": plano.get("titulo"),
            "eixo_x": plano.get("eixo_x"),
            "valores": plano.get("valores"),
            "chart": url_imagem,
            "chartData": chart_data,
            "sugestao": plano.get("sugestao"),
        })

    except Exception as e:
        logger.error(f"Erro em /api/analisar: {e}")
        return JSONResponse(
            {
                "analise": f"⚠️ Desculpe, ocorreu um erro técnico: {e}",
                "tipo_grafico": None,
            },
            status_code=500,
        )
