import json
import pandas as pd
from sqlalchemy import text, inspect
from sqlalchemy.dialects.postgresql import JSONB
import logging
from config import engine, Config

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_contexto_clinico_completo() -> str:
    """
    Extrai dados clínicos do banco de forma dinâmica e anonimizada (LGPD).
    Identifica as colunas existentes e filtra as sensíveis.
    """
    try:
        with engine.connect() as conn:
            inspector = inspect(engine)
            # 1. Descobre as colunas que realmente existem na tabela
            columns_info = inspector.get_columns("pacientes")
            all_columns = [c["name"] for c in columns_info]
            
            # 2. Filtro LGPD automático baseado na blacklist do config.py
            safe_cols = [c for c in all_columns if c.lower() not in [item.lower() for item in Config.LGPD_BLACKLIST]]
            
            if not safe_cols:
                return "Aviso: Nenhuma coluna segura para LGPD foi encontrada."
            
            # 3. Busca os dados limitados para o contexto da IA
            query = text(f"SELECT {', '.join(safe_cols)} FROM pacientes LIMIT :limit")
            df = pd.read_sql(query, conn, params={"limit": Config.MAX_PATIENTS_CONTEXT})
            
            if df.empty:
                return "O banco de dados está conectado, mas a tabela 'pacientes' está vazia."
            
            # 4. Gera um resumo estatístico das colunas numéricas que sobraram
            resumo = f"--- RESUMO DO BANCO (Total: {len(df)} registros analisados) ---\n"
            for col in df.select_dtypes(include=["int64", "float64"]).columns:
                resumo += f"Métrica de {col}: média={df[col].mean():.1f}, min={df[col].min()}, max={df[col].max()}\n"
            
            return f"{resumo}\nLISTA DE DADOS (Anonimizados):\n{df.to_string(index=False)}"
            
    except Exception as e:
        logger.error(f"Erro na extração dinâmica: {e}")
        return "Erro técnico: Não foi possível ler a estrutura do banco de dados."

def get_total_pacientes() -> int:
    """Conta o total absoluto de registros."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM pacientes")).fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"Erro ao contar pacientes: {e}")
        return 0

def get_metricas_dashboard() -> dict:
    """
    Lê o esquema da tabela e gera métricas apenas para as colunas que existirem.
    Evita o erro 'UndefinedColumn'.
    """
    try:
        with engine.connect() as conn:
            inspector = inspect(engine)
            colunas_reais = [c["name"].lower() for c in inspector.get_columns("pacientes")]
            
            # Construção dinâmica da query
            query_parts = ["COUNT(*) as total"]
            
            # Tenta calcular idade se a coluna existir
            if 'idade' in colunas_reais:
                query_parts.append("AVG(idade) as media_idade")
            else:
                query_parts.append("0 as media_idade")
                
            # Tenta contar diagnósticos se a coluna existir
            if 'diagnostico' in colunas_reais:
                query_parts.append("COUNT(DISTINCT diagnostico) as diagnosticos_unicos")
            else:
                query_parts.append("0 as diagnosticos_unicos")

            # Tenta filtrar por status se a coluna existir
            if 'status' in colunas_reais:
                query_parts.append("COUNT(CASE WHEN status = 'ativo' THEN 1 END) as ativos")
                query_parts.append("COUNT(CASE WHEN status = 'alta' THEN 1 END) as altas")
            else:
                query_parts.append("0 as ativos")
                query_parts.append("0 as altas")

            final_query = text(f"SELECT {', '.join(query_parts)} FROM pacientes")
            row = conn.execute(final_query).fetchone()
            
            return {
                "total_pacientes": row[0] if row else 0,
                "media_idade": round(row[1], 1) if row and row[1] else 0,
                "diagnosticos_unicos": row[2] if row and row[2] else 0,
                "ativos": row[3] if row and row[3] else 0,
                "altas": row[4] if row and row[4] else 0,
                "colunas_detectadas": colunas_reais # Útil para a IA saber o que pode perguntar
            }
    except Exception as e:
        logger.error(f"Erro ao mapear métricas: {e}")
        return {
            "total_pacientes": "Erro",
            "media_idade": 0,
            "diagnosticos_unicos": 0,
            "ativos": 0,
            "altas": 0
        }


# =============================================================================
# PERSISTÊNCIA DE CONVERSAS (Histórico do Chat)
# =============================================================================
#
# Estrutura espelha o que o frontend (script.js) já consome:
#   message = { role, content, hasChart, chartData: { type, title, labels, values } }
#
# Tabelas:
#   conversas (id, titulo, criada_em, atualizada_em)
#   mensagens (id, conversa_id, role, content, has_chart, chart_data JSONB,
#              sugestao, criada_em)
# =============================================================================

DDL_CHAT = """
CREATE TABLE IF NOT EXISTS conversas (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(200) NOT NULL DEFAULT 'Nova conversa',
    criada_em TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizada_em TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mensagens (
    id SERIAL PRIMARY KEY,
    conversa_id INTEGER NOT NULL REFERENCES conversas(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user','assistant')),
    content TEXT NOT NULL DEFAULT '',
    has_chart BOOLEAN NOT NULL DEFAULT FALSE,
    chart_data JSONB,
    sugestao TEXT,
    criada_em TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mensagens_conversa
    ON mensagens (conversa_id, criada_em);

CREATE TABLE IF NOT EXISTS dashboard_charts (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(200) NOT NULL DEFAULT 'Gráfico',
    chart_data JSONB NOT NULL,
    posicao INTEGER NOT NULL DEFAULT 0,
    criada_em TIMESTAMP NOT NULL DEFAULT NOW()
);
"""

DASHBOARD_CHART_LIMIT = 10


def init_chat_schema() -> None:
    """Cria as tabelas de histórico se ainda não existirem (idempotente)."""
    try:
        with engine.begin() as conn:
            for stmt in [s.strip() for s in DDL_CHAT.split(";") if s.strip()]:
                conn.execute(text(stmt))
    except Exception as e:
        logger.error(f"Erro ao inicializar schema de chat: {e}")


def _plano_para_chart_data(plano: dict) -> dict | None:
    """Converte o 'plano' devolvido pela IA no formato chartData usado pelo frontend.

    plano = { tipo_grafico, titulo, eixo_x, valores, ... }
    chartData = { type, title, labels, values }
    """
    if not plano:
        return None
    tipo = plano.get("tipo_grafico")
    if not tipo or tipo == "null":
        return None
    return {
        "type": tipo,
        "title": plano.get("titulo") or "",
        "labels": plano.get("eixo_x") or [],
        "values": plano.get("valores") or [],
    }


def criar_conversa(titulo: str = "Nova conversa") -> int | None:
    """Cria uma nova conversa e devolve o id."""
    try:
        with engine.begin() as conn:
            row = conn.execute(
                text("INSERT INTO conversas (titulo) VALUES (:t) RETURNING id"),
                {"t": (titulo or "Nova conversa")[:200]},
            ).fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"Erro ao criar conversa: {e}")
        return None


def renomear_conversa(conversa_id: int, titulo: str) -> bool:
    """Atualiza o título de uma conversa."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE conversas SET titulo = :t, atualizada_em = NOW() "
                    "WHERE id = :id"
                ),
                {"t": (titulo or "")[:200], "id": conversa_id},
            )
            return True
    except Exception as e:
        logger.error(f"Erro ao renomear conversa {conversa_id}: {e}")
        return False


def deletar_conversa(conversa_id: int) -> bool:
    """Remove uma conversa (e suas mensagens via ON DELETE CASCADE)."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM conversas WHERE id = :id"),
                {"id": conversa_id},
            )
            return True
    except Exception as e:
        logger.error(f"Erro ao deletar conversa {conversa_id}: {e}")
        return False


def listar_conversas(limite: int = 100) -> list[dict]:
    """Lista as conversas mais recentes (sem mensagens)."""
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, titulo, criada_em, atualizada_em "
                    "FROM conversas ORDER BY atualizada_em DESC LIMIT :l"
                ),
                {"l": limite},
            ).fetchall()
            return [
                {
                    "id": r[0],
                    "titulo": r[1],
                    "criada_em": r[2].isoformat() if r[2] else None,
                    "atualizada_em": r[3].isoformat() if r[3] else None,
                }
                for r in rows
            ]
    except Exception as e:
        logger.error(f"Erro ao listar conversas: {e}")
        return []


def get_conversa(conversa_id: int) -> dict | None:
    """Retorna uma conversa com todas as mensagens no formato consumido pelo frontend."""
    try:
        with engine.connect() as conn:
            cab = conn.execute(
                text(
                    "SELECT id, titulo, criada_em, atualizada_em "
                    "FROM conversas WHERE id = :id"
                ),
                {"id": conversa_id},
            ).fetchone()
            if not cab:
                return None

            msgs = conn.execute(
                text(
                    "SELECT id, role, content, has_chart, chart_data, sugestao, criada_em "
                    "FROM mensagens WHERE conversa_id = :id "
                    "ORDER BY criada_em ASC, id ASC"
                ),
                {"id": conversa_id},
            ).fetchall()

            return {
                "id": cab[0],
                "titulo": cab[1],
                "criada_em": cab[2].isoformat() if cab[2] else None,
                "atualizada_em": cab[3].isoformat() if cab[3] else None,
                "messages": [
                    {
                        "id": m[0],
                        "role": m[1],
                        "content": m[2] or "",
                        "hasChart": bool(m[3]),
                        "chartData": m[4],  # JSONB já vem como dict
                        "sugestao": m[5],
                        "criada_em": m[6].isoformat() if m[6] else None,
                    }
                    for m in msgs
                ],
            }
    except Exception as e:
        logger.error(f"Erro ao buscar conversa {conversa_id}: {e}")
        return None


def adicionar_mensagem(
    conversa_id: int,
    role: str,
    content: str,
    chart_data: dict | None = None,
    sugestao: str | None = None,
) -> int | None:
    """Insere uma mensagem na conversa e atualiza o timestamp da conversa."""
    if role not in ("user", "assistant"):
        raise ValueError("role deve ser 'user' ou 'assistant'")
    try:
        with engine.begin() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO mensagens "
                    "(conversa_id, role, content, has_chart, chart_data, sugestao) "
                    "VALUES (:cid, :r, :c, :h, CAST(:cd AS JSONB), :s) RETURNING id"
                ),
                {
                    "cid": conversa_id,
                    "r": role,
                    "c": content or "",
                    "h": bool(chart_data),
                    "cd": json.dumps(chart_data) if chart_data is not None else None,
                    "s": sugestao,
                },
            ).fetchone()
            conn.execute(
                text("UPDATE conversas SET atualizada_em = NOW() WHERE id = :id"),
                {"id": conversa_id},
            )
            return row[0] if row else None
    except Exception as e:
        logger.error(f"Erro ao adicionar mensagem na conversa {conversa_id}: {e}")
        return None

# =============================================================================
# DASHBOARD CHARTS (gráficos fixados pelo usuário, máx. DASHBOARD_CHART_LIMIT)
# =============================================================================

def listar_dashboard_charts() -> list[dict]:
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, titulo, chart_data, posicao, criada_em "
                    "FROM dashboard_charts ORDER BY posicao ASC, id ASC"
                )
            ).fetchall()
            return [
                {
                    "id": r[0],
                    "titulo": r[1],
                    "chartData": r[2],
                    "posicao": r[3],
                    "criada_em": r[4].isoformat() if r[4] else None,
                }
                for r in rows
            ]
    except Exception as e:
        logger.error(f"Erro ao listar dashboard_charts: {e}")
        return []


def contar_dashboard_charts() -> int:
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT COUNT(*) FROM dashboard_charts")).fetchone()
            return row[0] if row else 0
    except Exception as e:
        logger.error(f"Erro ao contar dashboard_charts: {e}")
        return 0


def adicionar_dashboard_chart(titulo: str, chart_data: dict) -> dict:
    """Insere um chart no dashboard. Retorna {'ok':bool, 'id':int|None, 'erro':str|None}."""
    if not chart_data or not chart_data.get("type"):
        return {"ok": False, "id": None, "erro": "chartData inválido"}
    try:
        with engine.begin() as conn:
            total = conn.execute(text("SELECT COUNT(*) FROM dashboard_charts")).scalar() or 0
            if total >= DASHBOARD_CHART_LIMIT:
                return {
                    "ok": False,
                    "id": None,
                    "erro": f"Limite de {DASHBOARD_CHART_LIMIT} gráficos atingido.",
                }
            row = conn.execute(
                text(
                    "INSERT INTO dashboard_charts (titulo, chart_data, posicao) "
                    "VALUES (:t, CAST(:cd AS JSONB), :p) RETURNING id"
                ),
                {
                    "t": (titulo or "Gráfico")[:200],
                    "cd": json.dumps(chart_data),
                    "p": total,
                },
            ).fetchone()
            return {"ok": True, "id": row[0] if row else None, "erro": None}
    except Exception as e:
        logger.error(f"Erro ao adicionar dashboard_chart: {e}")
        return {"ok": False, "id": None, "erro": "erro interno"}


def deletar_dashboard_chart(chart_id: int) -> bool:
    try:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM dashboard_charts WHERE id = :id"),
                {"id": chart_id},
            )
            return True
    except Exception as e:
        logger.error(f"Erro ao deletar dashboard_chart {chart_id}: {e}")
        return False
