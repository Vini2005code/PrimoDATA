"""Motor de IA — interface única com a Groq.

Mantém um cliente lazy (a app sobe sem chave; só falha quando alguém chama).
"""
from __future__ import annotations

import json

from groq import Groq

from app.core.config import settings
from app.core.logging_setup import get_logger

logger = get_logger(__name__)

_client: Groq | None = None
_MODEL = "llama-3.3-70b-versatile"


def _get_client() -> Groq:
    global _client
    if _client is None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY não configurada. Defina a variável de ambiente "
                "para habilitar a IA."
            )
        _client = Groq(api_key=settings.groq_api_key)
    return _client


_PROMPT_TEMPLATE = """SISTEMA DE INTELIGÊNCIA CLÍNICA - MITRA MED

[CONTEXTO DOS DADOS]
{contexto}

[PERGUNTA DO MÉDICO]
{pergunta}

[DIRETRIZES DE SEGURANÇA (LGPD)]
1. Nunca exponha CPFs ou dados sensíveis brutos se não for estritamente necessário.
2. Agregue dados sempre que possível (ex: "5 pacientes" em vez de listar nomes).

[REGRAS DE DECISÃO DE GRÁFICO]
- Responda 'tipo_grafico': null se a pergunta for sobre um paciente específico ou puramente textual.
- Use 'bar' para comparações entre categorias.
- Use 'pie' ou 'donut' para proporções e distribuições (ex: % de convênios).
- Use 'line' apenas se houver datas ou evolução temporal clara.

[FORMATO OBRIGATÓRIO DE RESPOSTA]
Responda APENAS o objeto JSON abaixo, sem textos antes ou depois:
{{
  "analise": "Sua conclusão clínica ou resposta direta.",
  "tipo_grafico": "bar | pie | line | donut | null",
  "titulo": "Título curto do gráfico",
  "eixo_x": ["Legenda A", "Legenda B"],
  "valores": [10, 20],
  "sugestao": "Um insight clínico preventivo baseado nos dados.",
  "suggested_insight": "Recomendação acionável curta para o médico (1 frase)."
}}
"""


def planejar_grafico(contexto_clinico: str, pergunta_medico: str) -> dict:
    """Decide se a resposta é texto puro ou texto + gráfico."""
    prompt = _PROMPT_TEMPLATE.format(
        contexto=contexto_clinico, pergunta=pergunta_medico
    )

    try:
        response = _get_client().chat.completions.create(
            model=_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um Analista de Dados Clínicos especializado em "
                        "hospitais brasileiros. Responda sempre em JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1000,
        )

        texto = response.choices[0].message.content or ""
        logger.info(f"Resposta bruta da IA: {texto[:200]}...")

        ini, fim = texto.find("{"), texto.rfind("}") + 1
        if ini == -1 or fim == 0:
            raise ValueError("A IA não retornou JSON válido.")

        data = json.loads(texto[ini:fim])
        return {
            "analise": data.get("analise", "Análise processada."),
            "tipo_grafico": data.get("tipo_grafico"),
            "titulo": data.get("titulo", "Análise Mitra Med"),
            "eixo_x": data.get("eixo_x", []),
            "valores": data.get("valores", []),
            "sugestao": data.get("sugestao", ""),
            "suggested_insight": data.get("suggested_insight")
            or data.get("sugestao", ""),
        }
    except Exception as e:
        logger.error(f"Erro no processamento da IA: {e}")
        return {
            "analise": "Tive uma dificuldade técnica para processar essa análise agora.",
            "tipo_grafico": None,
            "titulo": "",
            "eixo_x": [],
            "valores": [],
            "sugestao": "Tente refinar a sua pergunta.",
            "suggested_insight": "",
        }
