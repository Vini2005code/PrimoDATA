# teste_conexao.py
from config import engine, Config
from database import get_dashboard_metrics
from legacy.ai_engine import analisar_demanda_medica

def testar_tudo():
    print("--- 🔍 INICIANDO TESTE DE SISTEMA ---")

    # 1. Testar Banco de Dados
    print("\n1. Verificando PostgreSQL...")
    metrics = get_dashboard_metrics()
    if metrics["total_pacientes"] != "Erro":
        print(f"✅ Conectado! Pacientes no banco: {metrics['total_pacientes']}")
    else:
        print("❌ Falha ao conectar no Postgres. Verifique o .env e se o banco está ligado.")

    # 2. Testar IA
    print("\n2. Verificando Gemini AI...")
    if not Config.GEMINI_API_KEY:
        print("❌ Chave API não encontrada no .env!")
    else:
        resposta = analisar_demanda_medica("Diga apenas 'Conexão OK' se estiver me ouvindo.")
        if "Erro" not in resposta:
            print(f"✅ Gemini respondeu: {resposta.strip()}")
        else:
            print(f"❌ Erro na IA: {resposta}")

    print("\n--- TESTE FINALIZADO ---")

if __name__ == "__main__":
    testar_tudo()