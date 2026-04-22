import json
import logging
from groq import Groq
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = Groq(api_key=Config.GROQ_API_KEY)

SYSTEM_PROMPT = """Você é um engenheiro de dados médicos estrito e preciso.
Analise os dados clínicos fornecidos e responda à pergunta do médico.

REGRAS:
1. Use APENAS os dados fornecidos — NUNCA invente
2. Seja preciso nos cálculos (conte, agrupe, calcule)
3. Responda em português brasileiro
4. Respeite LGPD — nunca revele dados pessoais
5. Sempre sugira o melhor tipo de gráfico para a análise

Responda APENAS com o JSON abaixo. Sem blocos de código, sem introduções.

FORMATO EXATO:
{
  "analise": "Sua conclusão médica estruturada.",
  "tipo_grafico": "bar | pie | donut | line | area",
  "titulo": "Título do Gráfico",
  "eixo_x": ["Cat 1", "Cat 2"],
  "valores": [10, 20],
  "sugestao": "Explicação breve de por que este tipo de gráfico é ideal"
}"""


def planejar_grafico(contexto: str, pergunta: str) -> dict:
    """
    Envia contexto clínico + pergunta à IA e retorna plano de gráfico estruturado.
    """
    prompt = f"DADOS CLÍNICOS:\n{contexto}\n\nPERGUNTA DO MÉDICO: {pergunta}"
    
    try:
        response = client.chat.completions.create(
            model=Config.MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=Config.AI_TEMPERATURE,
            max_tokens=2000,
        )
        
        resposta = response.choices[0].message.content.strip()
        
        # Extração robusta do JSON
        inicio = resposta.find("{")
        fim = resposta.rfind("}") + 1
        
        if inicio == -1 or fim <= inicio:
            raise ValueError("Resposta da IA não contém JSON válido")
        
        plano = json.loads(resposta[inicio:fim])
        
        # Validação mínima
        required = ["analise", "tipo_grafico", "titulo", "eixo_x", "valores"]
        for field in required:
            if field not in plano:
                raise ValueError(f"Campo obrigatório ausente: {field}")
        
        if len(plano["eixo_x"]) != len(plano["valores"]):
            raise ValueError("eixo_x e valores devem ter o mesmo tamanho")
        
        return plano
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON inválido da IA: {e}")
        return _fallback("Erro ao interpretar resposta da IA. Tente reformular a pergunta.")
    except Exception as e:
        logger.error(f"Erro no AI Engine: {e}")
        return _fallback(str(e))


def _fallback(msg: str) -> dict:
    """Resposta de fallback para quando a IA falha."""
    return {
        "analise": f"⚠️ {msg}",
        "tipo_grafico": "bar",
        "titulo": "Erro na Análise",
        "eixo_x": ["Sem dados"],
        "valores": [0],
        "sugestao": "Tente reformular sua pergunta.",
    }
