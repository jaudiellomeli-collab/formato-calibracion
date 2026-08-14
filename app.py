import streamlit as st
import datetime
import numpy as np
import plotly.graph_objects as go
import os

st.set_page_config(layout="wide", page_title="Calibración O3 SIMAJ")

# --- CSS MEJORADO (Estilo SIMAJ + Semáforo) ---
estilos_personalizados = """
<style>
    h1, h2, h3 { color: #00B2A9 !important; font-weight: 800 !important; }
    h4 { color: #5C6670 !important; }
    hr { border-bottom: 3px solid #F37021 !important; margin: 1.5em 0 !important; }
    /* Estilo de validación visual */
    div[data-baseweb="select"] > div { border-color: #00B2A9 !important; }
    @media print {
        header, footer, .stDeployButton { display: none !important; }
        details:not([open]) { display: none !important; }
    }
</style>
"""
st.markdown(estilos_personalizados, unsafe_allow_html=True)

# Base de datos de equipos O3
equipos_o3 = {
    "Atemajac": "24-0385", "Santa Margarita": "24-0387", "Country": "23-2319",
    "Oblatos": "24-0766", "Vallarta": "24-0388", "Águilas": "24-0768",
    "Centro": "23-1564", "Tlaquepaque": "24-0948", "Miravalle": "24-0302",
    "Loma Dorada": "24-0941", "Pintas": "24-0305", "Santa Fe": "24-0307", "Santa Anita": "24-0333"
}

if os.path.exists("simaj.png"): st.image("simaj.png", width=300)

st.title("FORMATO DE CALIBRACIÓN O3")

# --- 1. DATOS ANALIZADOR ---
with st.expander("🛠️ DATOS DEL ANALIZADOR", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        estacion = st.selectbox("Estación:", [""] + list(equipos_o3.keys()))
        num_serie = equipos_o3.get(estacion, "")
        st.text_input("Número de Serie:", value=num_serie, disabled=True)
    with col2:
        st.date_input("Fecha de calibración")

# --- 2. FLUJOS (Regla 2.5%) ---
with st.expander("💨 VERIFICACIÓN Y AJUSTE DE FLUJO", expanded=True):
    def validar_color(val, min_v, max_v):
        if val is None: return "gray"
        return "green" if min_v <= val <= max_v else "red"

    c1, c2 = st.columns(2)
    with c1:
        v_ini = st.number_input("Flujo Volumétrico Inicial (cc/min)", value=None)
        color = validar_color(v_ini, 487.5, 512.5)
        st.markdown(f":{color}[Estado: {'Cumple' if color=='green' else 'NO CUMPLE'}]")
    with c2:
        v_fin = st.number_input("Flujo Volumétrico Final (cc/min)", value=None)
        color = validar_color(v_fin, 487.5, 512.5)
        st.markdown(f":{color}[Estado: {'Cumple' if color=='green' else 'NO CUMPLE'}]")

# --- 3. REVISIÓN COMPONENTES (Semáforo Si/No/Bueno/Malo) ---
with st.expander("🔍 REVISIÓN DE COMPONENTES", expanded=True):
    def fila_comp(nombre):
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 2])
        with c1: st.write(nombre)
        with c2: 
            estado = st.selectbox("Estado", ["Bueno", "Malo"], key=f"e_{nombre}")
            st.markdown(f":{'green' if estado=='Bueno' else 'red'}[{estado}]")
        with c3: 
            limp = st.selectbox("¿Limpieza?", ["Sí", "No"], key=f"l_{nombre}")
            st.markdown(f":{'green' if limp=='Sí' else 'red'}[{limp}]")
        with c4: 
            remp = st.selectbox("¿Remplazo?", ["Sí", "No"], key=f"r_{nombre}")
            st.markdown(f":{'green' if remp=='Sí' else 'red'}[{remp}]")
        with c5: st.text_input("Obs", key=f"o_{nombre}", label_visibility="collapsed")

    fila_comp("Bomba de Vacío Externa")
    fila_comp("Bomba de Vacío Interna")
    fila_comp("Filtro 47mm")

# --- 4. FIRMAS ---
with st.expander("✍️ FIRMAS", expanded=True):
    c1, c2 = st.columns(2)
    with c1: 
        st.text_input("Empresa/Institución")
        st.text_input("Nombre Técnico")
    with c2: 
        st.text_input("Empresa/Institución")
        st.text_input("Nombre Supervisor")
