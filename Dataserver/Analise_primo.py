import os
import json
import logging
from groq import Groq
from dotenv import load_dotenv

# Carrega as chaves do arquivo .env
load_dotenv()

# Configuração do log para vermos o que a IA está "pensando"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializa o cliente da Groq de forma preguiçosa para permitir que o app
# suba mesmo sem a chave configurada (a rota de análise retornará erro amigável).
_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY não configurada. Defina a variável de ambiente para habilitar a IA."
            )
        _client = Groq(api_key=api_key)
    return _client

def planejar_grafico(contexto_clinico, pergunta_medico):
    """
    Motor de Inteligência do Mitra Med. 
    Analisa os dados e decide se responde com texto ou se precisa de um gráfico.
    """
    
    # Prompt otimizado para LGPD e JSON puro
    prompt = f"""
    SISTEMA DE INTELIGÊNCIA CLÍNICA - MITRA MED
    
    [CONTEXTO DOS DADOS]
    {contexto_clinico}

    [PERGUNTA DO MÉDICO]
    {pergunta_medico}

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
      "sugestao": "Um insight clínico preventivo baseado nos dados."
    }}
    """

    try:
        # Chamada para o modelo Llama 3.3
        response = _get_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Você é um Analista de Dados Clínicos especializado em hospitais brasileiros. Responda sempre em JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1, # Temperatura baixa para manter a resposta estruturada e sem "alucinações"
            max_tokens=1000
        )

        texto_ia = response.choices[0].message.content
        logger.info(f"Resposta bruta da IA: {texto_ia}")

        # Extração segura do JSON (caso a IA mande texto extra)
        inicio = texto_ia.find('{')
        fim = texto_ia.rfind('}') + 1
        
        if inicio == -1 or fim == 0:
            raise ValueError("A IA não retornou um JSON válido.")

        dados_limpos = json.loads(texto_ia[inicio:fim])
        
        # Garante que os campos essenciais existam para não quebrar o JavaScript
        return {
            "analise": dados_limpos.get("analise", "Análise processada."),
            "tipo_grafico": dados_limpos.get("tipo_grafico"),
            "titulo": dados_limpos.get("titulo", "Análise Mitra Med"),
            "eixo_x": dados_limpos.get("eixo_x", []),
            "valores": dados_limpos.get("valores", []),
            "sugestao": dados_limpos.get("sugestao", "")
        }

    except Exception as e:
        logger.error(f"Erro no processamento da IA: {e}")
        # Retorno de segurança para o sistema não travar
        return {
            "analise": "Tive uma dificuldade técnica para processar essa análise agora.",
            "tipo_grafico": None,
            "sugestao": "Tente refinar a sua pergunta."
        }

# Se rodar este arquivo sozinho, ele faz um teste rápido
if __name__ == "__main__":
    print("Testando motor de IA...")
    resultado = planejar_grafico("3 pacientes com Gripe, 1 com Dengue", "Qual a situação hoje?")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))