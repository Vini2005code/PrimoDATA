import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Monta a URL de conexão de forma segura
DB_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

# Cria o motor de conexão (Engine)
engine = create_engine(DB_URL)

def get_connection():
    """Retorna uma conexão ativa com o banco de dados."""
    return engine.connect()
"""Se amanhã você mudar o banco de dados de PostgreSQL para Oracle (muito comum em hospitais grandes), 
você só mexe no config.py. O resto do seu sistema nem vai perceber a mudança. Isso se chama Manutenibilidade."""