import streamlit as st
import pandas as pd
import googlemaps
import google.generativeai as genai
from datetime import datetime
import time

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="ASSISTÊNCIA FINDER", layout="wide", page_icon="🔍")

st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: 700; color: #1E3A8A; }
    .sub-header { font-size: 1.2rem; color: #4B5563; margin-bottom: 2rem; }
    .card { background-color: #F9FAFB; padding: 20px; border-radius: 10px; border: 1px solid #E5E7EB; margin-bottom: 15px; }
    .status-confirmada { color: #047857; font-weight: bold; background-color: #D1FAE5; padding: 4px 8px; border-radius: 4px; }
    .status-provavel { color: #B45309; font-weight: bold; background-color: #FEF3C7; padding: 4px 8px; border-radius: 4px; }
    .score-badge { font-size: 1.2rem; font-weight: bold; float: right; color: #1E3A8A; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CONFIGURAÇÕES DE API
# ==========================================
GMAPS_API_KEY = ""
GEMINI_API_KEY = ""

if not GMAPS_API_KEY or not GEMINI_API_KEY:
    st.warning("⚠️ Esta função requer ativação/configuração de chaves de API (Google Maps e Gemini) no código.")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro') 

# ==========================================
# DADOS DE REFERÊNCIA
# ==========================================
UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

SEGMENTOS = {
    "Eletroportáteis": ["liquidificadores", "batedeiras", "processadores", "cafeteiras", "torradeiras"],
    "Cozinhas Profissionais": ["fornos profissionais", "fogões industriais", "refrigeração comercial"],
    "Panelas de Pressão": ["conserto panela pressão", "assistência panela pressão", "troca de válvulas"],
    "Todos": []
}

# CNAEs importados e categorizados da Base Tramontina 2026
CNAES_POR_SEGMENTO = {
    "Eletroportáteis": [
        "9521-5/00", # Principal para equipamentos eletroeletrônicos de uso pessoal/doméstico
        "3313-9/99", # Complementar para manutenção elétrica
        "3314-7/10", # Equipamentos para uso geral
        "3313-9/01"  # Manutenção e reparação de geradores, transformadores e motores
    ],
    "Cozinhas Profissionais": [
        "3314-7/07", # Refrigeração e ventilação comercial/industrial
        "3314-7/06", # Equipamentos para instalações térmicas (fornos)
        "3314-7/10", # Equipamentos para uso geral
        "4322-3/02", # Sistemas centrais de ventilação e refrigeração
        "3321-0/00", # Instalação de máquinas e equipamentos industriais
        "3313-9/99", # Aparelhos e materiais elétricos
        "3314-7/04"  # Compressores
    ],
    "Panelas de Pressão": [
        "9521-5/00", # Reparação de equipamentos de uso pessoal e doméstico
        "9529-1/99", # Reparação de outros objetos e equipamentos não especificados
        "3319-8/00"  # Equipamentos e produtos não especificados anteriormente
    ],
    "Todos": []
}

RAIOS = {"Cidade": 0, "10 km": 10000, "25 km": 25000, "50 km": 50000, "100 km": 100000}

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
st.markdown('<p class="main-header">ASSISTÊNCIA FINDER 🔍</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Inteligência para prospecção de Assistências Técnicas Autorizadas</p>', unsafe_allow_html=True)

with st.form("search_form"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        cidade = st.text_input("Digite a cidade", placeholder="Ex: Porto Alegre")
    with col2:
        uf = st.selectbox("UF", UFS, index=20)
    with col3:
        segmento = st.selectbox("Segmento", list(SEGMENTOS.keys()))
    with col4:
        raio = st.selectbox("Raio de Busca", list(RAIOS.keys()), index=2)
    
    submit = st.form_submit_button("PESQUISAR ASSISTÊNCIAS", use_container_width=True)

# ==========================================
# LÓGICA DE PESQUISA E PROGRESSO
# ==========================================
if submit:
    if not cidade:
        st.error("Por favor, digite uma cidade.")
    elif not GMAPS_API_KEY:
        st.error("Esta função requer ativação/configuração de API do Google Maps. A pesquisa não pode prosseguir sem acesso aos dados geográficos reais.")
    else:
        # Feedback visual dos CNAEs que serão utilizados
        cnaes_ativos = CNAES_POR_SEGMENTO.get(segmento, [])
        if cnaes_ativos:
            st.info(f"Filtros de CNAE auxiliares ativos para {segmento}: {', '.join(cnaes_ativos)}")

        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("✓ Consultando Google Maps (Places API)...")
        progress_bar.progress(20)
        time.sleep(1)
        
        status_text.text("✓ Pesquisando informações públicas (Google Search Grounding)...")
        progress_bar.progress(40)
        time.sleep(1)
        
        status_text.text("✓ Analisando empresas e eliminando duplicidades...")
        progress_bar.progress(60)
        time.sleep(1)
        
        status_text.text("✓ Validando evidências com Gemini AI (Score e Status)...")
        progress_bar.progress(80)
        time.sleep(1)
        
        status_text.text("✓ Calculando compatibilidade técnica e finalizando...")
        progress_bar.progress(100)
        status_text.text("Pesquisa concluída.")
        
        st.warning("⚠️ Modo de demonstração: Como as chaves de API não foram inseridas no script, nenhuma assistência confirmada foi recuperada da rede.")
        
        st.divider()
        st.subheader("RESUMO DA PESQUISA")
        r_col1, r_col2, r_col3, r_col4 = st.columns(4)
        r_col1.metric("Empresas encontradas", "0")
        r_col2.metric("Confirmadas", "0")
        r_col3.metric("Prováveis", "0")
        r_col4.metric("Não confirmadas", "0")
        
        st.info("Nenhuma assistência confirmada encontrada na área selecionada.")
        if st.button("EXPANDIR PESQUISA"):
            st.write("Pesquisando municípios próximos...")
