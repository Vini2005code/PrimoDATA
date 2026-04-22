import pandas as pd
from sqlalchemy import text, inspect
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