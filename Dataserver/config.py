import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

class Config:
    # Prefere DATABASE_URL (ambiente Replit). Fallback para variáveis individuais.
    DATABASE_URL = os.getenv("DATABASE_URL")
    DB_USER = os.getenv("PGUSER", os.getenv("DB_USER", "postgres"))
    DB_PASS = os.getenv("PGPASSWORD", os.getenv("DB_PASS", "20032007"))
    DB_HOST = os.getenv("PGHOST", os.getenv("DB_HOST", "localhost"))
    DB_PORT = os.getenv("PGPORT", os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("PGDATABASE", os.getenv("DB_NAME", "PrimordialbyMitra"))

    SQLALCHEMY_DATABASE_URL = DATABASE_URL or f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    MAX_PATIENTS_CONTEXT = 100
    LGPD_BLACKLIST = ["nome", "cpf", "rg", "telefone", "email"]

# Criando a engine com suporte a caracteres latinos (Brasil)
engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URL,
    connect_args={'client_encoding': 'utf8'} # Garante a conversa em UTF-8
)

