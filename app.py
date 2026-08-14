import streamlit as st
import datetime
import numpy as np
import plotly.graph_objects as go
import os

st.set_page_config(layout="wide", page_title="Calibración O3 SIMAJ")

# --- CSS MEJORADO (Estilo SIMAJ + Colores semáforo) ---
estilos_personalizados = """
<style>
    h1, h2, h3 { color: #00B2A9 !important; }
    hr { border-bottom: 3px solid #F37021 !important; margin: 1.5em 0 !important; }
    .stSuccess { background-color: #d4edda !important; color: #155724 !important; border-left: 5px solid #28a745 !important; }
    .stError { background-color: #f8d7da !important; color: #721c24 !important; border-left: 5px solid #dc3545 !important; }
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

# ==========================================
# 1. DATOS DEL ANALIZADOR
# ==========================================
with st.expander("🛠️ DATOS DEL ANALIZADOR", expanded=True):
    col_izq, col_der = st.columns(2)
    with col_izq:
        estacion = st.selectbox("Estación:", [""] + list(equipos_o3.keys()))
        num_serie = equipos_o3.get(estacion, "")
        st.text_input("Número de Serie (Automático):", value=num_serie, disabled=True)
    with col_der:
        st.date_input("Fecha de calibración", datetime.date.today())

# ==========================================
# 2. VERIFICACIÓN Y AJUSTE DE FLUJO (Regla estricta 2.5%)
# ==========================================
with st.expander("💨 VERIFICACIÓN Y AJUSTE DE FLUJO", expanded=True):
    st.caption("Nota: El Flujo Volumétrico debe estar en el rango de 500 cc/min ± 2.5% (487.5 - 512.5 cc/min)")
    
    def evaluar_flujo(val):
        if val is None: return "", ""
        cumple = 487.5 <= val <= 512.5
        color = "success" if cumple else "error"
        return f"{val} cc/min", color

    c1, c2 = st.columns(2)
    with c1:
        v_ini = st.number_input("Flujo Volumétrico Inicial (cc/min)", value=None)
        res, col = evaluar_flujo(v_ini)
        if res: getattr(st, col)(f"Estado: {res}")
        
    with c2:
        v_fin = st.number_input("Flujo Volumétrico Final (cc/min)", value=None)
        res, col = evaluar_flujo(v_fin)
        if res: getattr(st, col)(f"Estado: {res}")

# ==========================================
# 3. COMPONENTES (Estado Bueno/Malo, Limpieza/Remplazo)
# ==========================================
with st.expander("🔍 REVISIÓN DE COMPONENTES", expanded=True):
    def fila_comp(nombre):
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 2])
        with c1: st.write(nombre)
        with c2: 
            estado = st.selectbox("Estado", ["Bueno", "Malo"], key=f"e_{nombre}")
            if estado == "Bueno": st.success("Bueno")
            else: st.error("Malo")
        with c3: st.selectbox("¿Limpieza?", ["Sí", "No"], key=f"l_{nombre}")
        with c4: st.selectbox("¿Remplazo?", ["Sí", "No"], key=f"r_{nombre}")
        with c5: st.text_input("Observaciones", key=f"o_{nombre}", label_visibility="collapsed")

    fila_comp("Bomba de Vacío")
    fila_comp("Filtro 47mm")
    fila_comp("O-rings")

# ==========================================
# (Agrega aquí las secciones que faltan usando la misma lógica de expanders)
# ==========================================

st.markdown("<p style='text-align: center; color: gray;'>Presiona Ctrl+P para guardar el formato PDF.</p>", unsafe_allow_html=True)
