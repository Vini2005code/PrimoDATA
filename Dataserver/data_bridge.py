import requests

def buscar_prontuario_do_java(paciente_id):
    # O Java do seu colega entrega o dado mastigado aqui
    url = f"http://api-do-seu-colega.com/paciente/{paciente_id}"
    resposta = requests.get(url, headers={"Authorization": "Token-do-Medico"})
    return resposta.json()