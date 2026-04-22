import matplotlib
matplotlib.use("Agg")  # Backend para rodar no servidor sem interface gráfica
import matplotlib.pyplot as plt
import io
import base64
import logging
import uvicorn
import seaborn as sns
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Importação dos seus módulos internos
import database
import Analise_primo as ai_engine

# --- CONFIGURAÇÃO INICIAL ---

# 1. Criação do App (APENAS UMA VEZ)
app = FastAPI(title="Primordial DATA", version="2.0")

# 2. Configuração de Arquivos Estáticos e Templates
# Certifique-se de que as pastas 'static' e 'templates' existem no seu projeto
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 3. Estilização dos Gráficos (Branding Mitra Med)
sns.set_context("talk")
sns.set_style("white")
CHART_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#f97316", "#ec4899"]
plt.rcParams['axes.prop_cycle'] = plt.cycler(color=CHART_COLORS[:3])

# 4. Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- MODELOS DE DADOS ---

class RequisicaoChat(BaseModel):
    message: str
    conversa_id: Optional[int] = None  # se None, uma nova conversa será criada


class NovaConversa(BaseModel):
    titulo: Optional[str] = None


class RenomearConversa(BaseModel):
    titulo: str


class ChartDataIn(BaseModel):
    type: str
    title: Optional[str] = ""
    labels: list = []
    values: list = []


class FixarChartIn(BaseModel):
    titulo: Optional[str] = None
    chartData: ChartDataIn


# Garante que as tabelas de histórico existem ao iniciar o app
@app.on_event("startup")
def _startup_chat_schema():
    database.init_chat_schema()

# --- FUNÇÕES AUXILIARES ---

def gerar_imagem_grafico(plano: dict) -> str:
    """
    Gera um gráfico usando Matplotlib e retorna como uma string Base64.
    Utilizado como fallback ou para envio de imagem estática.
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#f8fafc")
    
    tipo = plano.get("tipo_grafico", "bar")
    eixo_x = plano.get("eixo_x", [])
    valores = plano.get("valores", [])
    colors = CHART_COLORS[: len(eixo_x)] if len(eixo_x) > 0 else CHART_COLORS
    
    try:
        if tipo == "pie":
            ax.pie(valores, labels=eixo_x, autopct="%1.1f%%", startangle=90, colors=colors)
        elif tipo == "donut":
            ax.pie(valores, labels=eixo_x, autopct="%1.1f%%", startangle=90, colors=colors, pctdistance=0.85)
            ax.add_artist(plt.Circle((0, 0), 0.70, fc="#f8fafc"))
        elif tipo == "line":
            ax.plot(eixo_x, valores, marker="o", color=CHART_COLORS[0], linewidth=2)
            ax.fill_between(eixo_x, valores, alpha=0.1, color=CHART_COLORS[0])
        else:  # bar (padrão)
            bars = ax.bar(eixo_x, valores, color=colors)
            ax.bar_label(bars, padding=3, fontweight="bold")
        
        ax.set_title(plano.get("titulo", "Análise Clínica"), fontsize=14, fontweight="bold", pad=15)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)
        return img_b64
    except Exception as e:
        logger.error(f"Erro ao gerar imagem: {e}")
        return ""

# --- ROTAS DO SERVIDOR ---

@app.get("/")
async def home(request: Request):
    """Renderiza a interface principal com as métricas do banco."""
    try:
        # 1. Busca os dados no banco
        metricas = database.get_metricas_dashboard()
        
        # 2. A NOVA FORMA: request e context separados
        # O erro "TypeError: cannot use 'tuple'..." acontece porque o Starlette 0.27+
        # exige que o 'request' seja passado como argumento nomeado.
        return templates.TemplateResponse(
            request=request,           # Argumento obrigatório nas versões novas
            name="index.html",         # Nome do arquivo
            context=metricas           # O dicionário com seus dados (total_pacientes, etc)
        )
    except Exception as e:
        logger.error(f"Erro ao carregar home: {e}")
        # Fallback de segurança caso o banco falhe
        return templates.TemplateResponse(
            request=request, 
            name="index.html", 
            context={"total_pacientes": 0, "media_idade": 0, "ativos": 0, "diagnosticos_unicos": 0}
        )
@app.post("/api/analisar")
async def api_analisar(req: RequisicaoChat):
    """
    Rota principal de inteligência.
    Recebe a pergunta, consulta o banco, pede a decisão para a IA, persiste a
    troca no histórico (tabelas conversas/mensagens) e retorna JSON.
    """
    try:
        logger.info(f"Processando pergunta: {req.message}")

        # 0. Garante a existência de uma conversa para persistir o histórico
        conversa_id = req.conversa_id
        if not conversa_id:
            titulo_inicial = (req.message or "Nova conversa").strip()[:60] or "Nova conversa"
            conversa_id = database.criar_conversa(titulo_inicial)

        # 1. Persiste a mensagem do usuário
        if conversa_id:
            database.adicionar_mensagem(conversa_id, "user", req.message)

        # 2. Busca dados no Postgres (Anonimizados via LGPD no database.py)
        contexto = database.get_contexto_clinico_completo()

        # 3. Chama a IA (Analise_primo.py) para decidir a resposta e o gráfico
        plano = ai_engine.planejar_grafico(contexto, req.message)

        # 4. Lógica de Gráfico: Decide se gera a imagem (Base64) ou envia apenas dados
        url_imagem = None
        if plano.get("tipo_grafico") and plano.get("tipo_grafico") != "null":
            url_imagem = gerar_imagem_grafico(plano)

        # 5. Persiste a resposta do assistente (já no formato chartData do frontend)
        chart_data = database._plano_para_chart_data(plano)
        if conversa_id:
            database.adicionar_mensagem(
                conversa_id,
                "assistant",
                plano.get("analise", "Análise concluída."),
                chart_data=chart_data,
                sugestao=plano.get("sugestao"),
            )

        # 6. Retorno padronizado para o JavaScript (script.js) + conversa_id
        return JSONResponse({
            "conversa_id": conversa_id,
            "analise": plano.get("analise", "Análise concluída."),
            "tipo_grafico": plano.get("tipo_grafico"),
            "titulo": plano.get("titulo"),
            "eixo_x": plano.get("eixo_x"),
            "valores": plano.get("valores"),
            "chart": url_imagem,  # Imagem Base64
            "chartData": chart_data,
            "sugestao": plano.get("sugestao"),
        })

    except Exception as e:
        logger.error(f"Erro na rota de análise: {e}")
        return JSONResponse({
            "analise": f"⚠️ Desculpe, ocorreu um erro técnico: {str(e)}",
            "tipo_grafico": None
        }, status_code=500)


# --- ROTAS DE HISTÓRICO (CRUD de conversas/mensagens) ---

@app.get("/api/conversas")
async def api_listar_conversas():
    """Lista as conversas salvas (sem mensagens)."""
    return JSONResponse({"conversas": database.listar_conversas()})


@app.post("/api/conversas")
async def api_criar_conversa(req: NovaConversa):
    """Cria uma nova conversa vazia."""
    cid = database.criar_conversa(req.titulo or "Nova conversa")
    if not cid:
        raise HTTPException(status_code=500, detail="Não foi possível criar a conversa.")
    return JSONResponse({"id": cid, "titulo": req.titulo or "Nova conversa"})


@app.get("/api/conversas/{conversa_id}")
async def api_get_conversa(conversa_id: int):
    """Retorna uma conversa com todas as mensagens (formato pronto para o frontend)."""
    conv = database.get_conversa(conversa_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return JSONResponse(conv)


@app.patch("/api/conversas/{conversa_id}")
async def api_renomear_conversa(conversa_id: int, req: RenomearConversa):
    """Renomeia uma conversa existente."""
    if not database.renomear_conversa(conversa_id, req.titulo):
        raise HTTPException(status_code=500, detail="Falha ao renomear.")
    return JSONResponse({"id": conversa_id, "titulo": req.titulo})


@app.delete("/api/conversas/{conversa_id}")
async def api_deletar_conversa(conversa_id: int):
    """Remove uma conversa e todas as suas mensagens."""
    if not database.deletar_conversa(conversa_id):
        raise HTTPException(status_code=500, detail="Falha ao deletar.")
    return JSONResponse({"ok": True, "id": conversa_id})

# --- ROTAS DO DASHBOARD (gráficos fixados, máx. 10) ---

@app.get("/api/dashboard/charts")
async def api_listar_dashboard_charts():
    return JSONResponse({
        "charts": database.listar_dashboard_charts(),
        "limite": database.DASHBOARD_CHART_LIMIT,
    })


@app.post("/api/dashboard/charts")
async def api_fixar_dashboard_chart(req: FixarChartIn):
    cd = req.chartData.model_dump()
    titulo = req.titulo or cd.get("title") or "Gráfico"
    res = database.adicionar_dashboard_chart(titulo, cd)
    if not res["ok"]:
        raise HTTPException(status_code=400, detail=res["erro"] or "Falha ao fixar gráfico.")
    return JSONResponse({"id": res["id"], "titulo": titulo})


@app.delete("/api/dashboard/charts/{chart_id}")
async def api_deletar_dashboard_chart(chart_id: int):
    if not database.deletar_dashboard_chart(chart_id):
        raise HTTPException(status_code=500, detail="Falha ao remover gráfico.")
    return JSONResponse({"ok": True, "id": chart_id})


# --- EXECUÇÃO ---

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)