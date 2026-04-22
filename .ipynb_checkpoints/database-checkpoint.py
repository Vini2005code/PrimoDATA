import pandas as pd
from config import engine # Importamos a conexão que criamos no outro arquivo

def buscar_total_pacientes():
    """Retorna o número total de pacientes cadastrados."""
    query = "SELECT count(*) FROM pacientes"
    df = pd.read_sql(query, engine)
    return df.iloc[0, 0]

def buscar_idade_media():
    """Calcula a idade média usando a lógica de Engenharia que aprendemos."""
    query = "SELECT AVG(EXTRACT(YEAR FROM AGE(data_nascimento))) FROM pacientes"
    df = pd.read_sql(query, engine)
    return int(df.iloc[0, 0]) if not df.empty else 0