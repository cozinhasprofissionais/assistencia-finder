import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
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
</style>
""", unsafe_allow_html=True)

# ==========================================
# CONFIGURAÇÕES DE API (Apenas Gemini)
# ==========================================
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    st.warning("⚠️ Chave do Gemini não encontrada no 'Secrets'. Configure para ativar a Inteligência Artificial.")
else:
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

RAIOS = {"10 km": 10000, "25 km": 25000, "50 km": 50000, "100 km": 100000}

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
st.markdown('<p class="main-header">ASSISTÊNCIA FINDER 🔍</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Buscador Inteligente via OpenStreetMap (Gratuito)</p>', unsafe_allow_html=True)

with st.form("search_form"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        cidade = st.text_input("Digite a cidade", placeholder="Ex: Porto Alegre")
    with col2:
        uf = st.selectbox("UF", UFS, index=20)
    with col3:
        segmento = st.selectbox("Segmento", list(SEGMENTOS.keys()))
    with col4:
        raio = st.selectbox("Raio de Busca", list(RAIOS.keys()), index=1)
    
    submit = st.form_submit_button("PESQUISAR ASSISTÊNCIAS", use_container_width=True)

# ==========================================
# LÓGICA DE PESQUISA (OpenStreetMap) + GEMINI
# ==========================================
if submit:
    if not cidade:
        st.error("Por favor, digite uma cidade.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("✓ Localizando coordenadas da cidade (Nominatim)...")
        progress_bar.progress(20)
        
        headers = {"User-Agent": "AssistenciaFinder_Tramontina/1.0"}
        geo_url = f"https://nominatim.openstreetmap.org/search?city={cidade}&state={uf}&country=Brazil&format=json"
        
        try:
            geo_resp = requests.get(geo_url, headers=headers)
            
            if geo_resp.status_code != 200 or not geo_resp.json():
                st.warning(f"Não foi possível encontrar as coordenadas para {cidade} - {uf}.")
                progress_bar.progress(100)
            else:
                geo_data = geo_resp.json()
                lat = geo_data[0]["lat"]
                lon = geo_data[0]["lon"]
                
                status_text.text("✓ Buscando comércios e assistências (Overpass API)...")
                progress_bar.progress(50)
                
                raio_m = RAIOS[raio]
                # Alterado para HTTPS e com tratamento de erro
                overpass_url = "https://overpass-api.de/api/interpreter"
                
                query = f"""
                [out:json][timeout:25];
                (
                  node["shop"="electronics"](around:{raio_m},{lat},{lon});
                  node["shop"="hardware"](around:{raio_m},{lat},{lon});
                  node["craft"="electronics_repair"](around:{raio_m},{lat},{lon});
                  node["shop"="appliance"](around:{raio_m},{lat},{lon});
                );
                out center;
                """
                
                op_resp = requests.get(overpass_url, params={'data': query})
                
                # Variável para guardar as empresas
                empresas = []
                
                # Proteção: Se o servidor gratuito falhar, criamos dados de contingência para teste
                if op_resp.status_code == 200:
                    try:
                        elementos = op_resp.json().get("elements", [])
                        empresas = [{"nome": e["tags"].get("name", "Sem Nome"), "rua": e["tags"].get("addr:street", "Endereço não mapeado")} for e in elementos if "tags" in e and "name" in e["tags"]]
                    except:
                        empresas = []
                
                # Ativando o Plano B se o servidor falhou ou retornou vazio
                if not empresas:
                    st.warning("⚠️ O servidor gratuito de mapas falhou ou não encontrou dados. Usando plano de contingência para validar a Inteligência Artificial.")
                    empresas = [
                        {"nome": "Eletro Service Silva", "rua": "Av. Assis Brasil"},
                        {"nome": "Refrigeração Pinguim", "rua": "Rua Voluntários da Pátria"},
                        {"nome": "Bazar e Panelas Zé", "rua": "Av. Bento Gonçalves"}
                    ]
                
                status_text.text("✓ Análise finalizada!")
                progress_bar.progress(100)
                
                st.divider()
                st.subheader(f"RESUMO DA PESQUISA: {cidade.upper()} - {uf}")
                
                st.write("### Principais Resultados:")
                
                lista_para_gemini = []
                
                for emp in empresas[:10]:
                    nome = emp["nome"]
                    rua = emp["rua"]
                    lista_para_gemini.append(nome)
                    
                    with st.expander(f"🏢 {nome}"):
                        st.write(f"**Rua:** {rua}")
                
                # Inteligência Artificial em ação
                if GEMINI_API_KEY and len(lista_para_gemini) > 0:
                    st.write("---")
                    st.write("### 🤖 O que a Inteligência Artificial acha?")
                    st.write("Enviando a lista de empresas encontradas para o Gemini analisar...")
                    
                    prompt = f"""
                    Você é um especialista em prospecção B2B da Tramontina. 
                    Nós encontramos estas empresas na cidade de {cidade}: {', '.join(lista_para_gemini)}.
                    Avaliando apenas pelo NOME das empresas, cite até 3 que parecem ser as mais indicadas para se tornarem uma Assistência Técnica Autorizada e explique brevemente o porquê.
                    """
                    
                    resposta = model.generate_content(prompt)
                    st.success(resposta.text)
                        
        except Exception as e:
            st.error(f"Erro inesperado durante a consulta: {e}")
