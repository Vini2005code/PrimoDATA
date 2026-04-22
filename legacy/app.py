import streamlit as st
import plotly.graph_objects as go
from legacy.ai_engine import processar_pergunta
from Dataserver.database import (
    buscar_total_pacientes, 
    buscar_idade_media, 
    buscar_dados_diagnosticos, 
    buscar_media_retorno
)

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Mitra Med AI", page_icon="🏥", layout="wide")

# 2. BARRA LATERAL (CHAT INTELIGENTE)
with st.sidebar:
    st.title("🤖 Assistente Mitra")
    st.info("Analise dados e tire dúvidas clínicas em tempo real.")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Doutor, o que deseja analisar?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Consultando base de dados segura..."):
                try:
                    resposta = processar_pergunta(prompt)
                    st.markdown(resposta)
                    st.session_state.messages.append({"role": "assistant", "content": resposta})
                except Exception as e:
                    st.error(f"Erro na conexão com IA: {e}")

# 3. PAINEL PRINCIPAL
st.title("🏥 Mitra Med - Dashboard Inteligente")
st.markdown("---")

# Cards de Indicadores
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Pacientes Atendidos", buscar_total_pacientes())
with col2:
    st.metric("Idade Média", f"{buscar_idade_media()} anos")
with col3:
    st.metric("Média de Retorno", f"{buscar_media_retorno():.1f} dias")

st.markdown("---")

# Visualização de Gráficos
col_esq, col_dir = st.columns([2, 1])

with col_esq:
    st.write("### 📊 Prevalência de Diagnósticos")
    df_diag = buscar_dados_diagnosticos()
    if not df_diag.empty:
        fig = go.Figure(go.Bar(x=df_diag['total'], y=df_diag['diagnostico'], orientation='h', marker_color='#2c3e50'))
        fig.update_layout(template="plotly_white", height=400, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

with col_dir:
    st.write("### ⏱️ Alerta de Fidelização")
    media = buscar_media_retorno()
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number", 
        value=media, 
        gauge={'axis': {'range': [None, 60]}, 'bar': {'color': "#2c3e50"}, 'threshold': {'line': {'color': "red", 'width': 4}, 'value': 30}}
    ))
    fig_g.update_layout(height=350)
    st.plotly_chart(fig_g, use_container_width=True)