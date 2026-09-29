import streamlit as st
import datetime
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import os
import streamlit.components.v1 as components

st.set_page_config(layout="wide", page_title="Calibración SIMAJ")

# ==========================================
# CSS GLOBAL Y COMPRESOR EXTREMO PARA PDF
# ==========================================
st.markdown("""
<style>
    h1, h2, h3 { color: #00B2A9 !important; font-weight: 800 !important; }
    h4 { color: #5C6670 !important; }
    hr { border-bottom: 3px solid #F37021 !important; margin: 1.5em 0 !important; }
    .stAlert { border-left: 5px solid #00B2A9 !important; background-color: #f0fdfa !important; }
    div[data-baseweb="select"] > div { border-color: #00B2A9 !important; }
    
    /* COMPRESOR EXTREMO PARA EL PDF */
    @media print {
        @page { size: letter portrait; margin: 0.5cm; }
        * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
        header, footer, .stDeployButton, [data-testid="stSidebar"], #btn-imprimir { display: none !important; }
        
        html, body, [class*="st-"] { font-size: 11px !important; line-height: 1.1 !important; color: black !important; }
        h1 { font-size: 14px !important; margin: 0 !important; padding: 0 !important; }
        h2, h3 { font-size: 12px !important; margin: 2px 0 !important; padding: 0 !important; }
        h4 { font-size: 11px !important; margin: 2px 0 !important; padding: 0 !important; }
        
        html, body, .stApp, div[data-testid="stAppViewContainer"], div[data-testid="stMain"] {
            height: auto !important; overflow: visible !important; position: static !important;
        }
        
        .main .block-container { max-width: 100% !important; padding: 0 !important; }
        [data-testid="column"] { padding: 0 4px !important; }
        [data-testid="stVerticalBlock"] { gap: 0 !important; }
        div[data-testid="stHorizontalBlock"] { gap: 0.5em !important; }
        
        input[type="text"], input[type="number"], textarea {
            font-size: 10px !important; padding: 2px !important; min-height: 0 !important; height: 18px !important; border: 1px solid #ccc !important;
        }
        div[data-baseweb="select"] > div {
            font-size: 10px !important; padding: 2px !important; min-height: 0 !important; height: 18px !important; border: 1px solid #ccc !important;
        }
        
        .stSelectbox svg, .stExpander > details > summary > svg { display: none !important; }
        .stExpander { border: none !important; border-bottom: 1px solid #ddd !important; margin-bottom: 2px !important; page-break-inside: avoid; }
        .stExpander summary { padding: 2px 0 !important; min-height: 0 !important; }
        details:not([open]) { display: none !important; }
        
        hr { margin: 2px 0 !important; }
        .stAlert { padding: 4px !important; border-width: 2px !important; }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# BASES DE DATOS DE EQUIPOS
# ==========================================
equipos_o3 = {"Pintas": "24-0305", "Santa Fe": "24-0307", "Miravalle": "24-0302", "Centro": "23-1564", "Country": "23-2319", "Atemajac": "24-0385", "Oblatos": "24-0766", "Santa Margarita": "24-0387", "Vallarta": "24-0388", "Loma Dorada": "24-0941", "Águilas": "24-0768", "Santa Anita": "24-0333", "Tlaquepaque": "24-0948"}
equipos_nox = {"Pintas": "24-0179", "Santa Fe": "24-0579", "Miravalle": "24-0587", "Centro": "24-0595", "Country": "23-2360", "Atemajac": "24-0705", "Oblatos": "24-0710", "Santa Margarita": "24-0570", "Vallarta": "24-0592", "Loma Dorada": "24-0709", "Águilas": "24-0594", "Santa Anita": "24-0182", "Tlaquepaque": "24-0700"}
equipos_co = {"Pintas": "24-1119", "Santa Fe": "24-1120", "Miravalle": "24-0169", "Centro": "24-0152", "Country": "24-0151", "Atemajac": "24-0146", "Oblatos": "24-1121", "Santa Margarita": "24-0399", "Loma Dorada": "24-1122", "Águilas": "ML9830 155", "Santa Anita": "24-0395"}
equipos_so2 = {"Pintas": "17-1764", "Miravalle": "23-1538", "Centro": "17-1762", "Oblatos": "17-1765", "Tlaquepaque": "17-1763"}

# ==========================================
# MENÚ LATERAL (SIDEBAR)
# ==========================================
st.sidebar.title("🛠️ Menú SIMAJ")
if os.path.exists("simaj.png"): st.sidebar.image("simaj.png")
gas_sel = st.sidebar.radio("Selecciona el Gas a Calibrar:", ["Ozono (O3)", "Óxidos de Nitrógeno (NOx)", "Monóxido de Carbono (CO)", "Dióxido de Azufre (SO2)"])

datos_resumen = {}

if gas_sel == "Ozono (O3)":
    equipos_act = equipos_o3; modelo_analizador = "Serinus 10"; flujo_ideal_vol = 500; flujo_tol = 0.025; cero_tol = 0.003
    puntos_multipunto = [0.400, 0.300, 0.200, 0.100, 0.001]; span_gen_default = 0.400
elif gas_sel == "Óxidos de Nitrógeno (NOx)":
    equipos_act = equipos_nox; modelo_analizador = "Serinus 40"; flujo_ideal_vol = 650; flujo_tol = 0.05; cero_tol = 0.003
    puntos_multipunto = [0.400, 0.300, 0.200, 0.100, 0.001]; span_gen_default = 0.400
elif gas_sel == "Monóxido de Carbono (CO)":
    equipos_act = equipos_co; modelo_analizador = "Serinus 30"; flujo_ideal_vol = 1000; flujo_tol = 0.025; cero_tol = 0.5
    puntos_multipunto = [40.0, 30.0, 20.0, 10.0, 0.001]; span_gen_default = 40.0
else: 
    equipos_act = equipos_so2; modelo_analizador = "Serinus 50"; flujo_ideal_vol = 700; flujo_tol = 0.025; cero_tol = 0.003
    puntos_multipunto = [0.400, 0.300, 0.200, 0.100, 0.0001]; span_gen_default = 0.400

# ==========================================
# ENCABEZADO
# ==========================================
if os.path.exists("simaj.png"):
    st.image("simaj.png", width=250)
st.title(f"FORMATO DE CALIBRACIÓN {gas_sel}")
st.subheader("Analizadores de Gases")

# Funciones de UI
def evaluar_y_mostrar(val, min_val, max_val):
    if val is None: st.write("")
    elif min_val <= val <= max_val: st.success("Cumple ✅"); return True
    else: st.error("NO CUMPLE ❌"); return False

def fila_regla(param, unit, ideal_str, min_val, max_val, key):
    c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 1, 1, 1.5, 1.5, 1.5, 1.5])
    with c1: st.write(param)
    with c2: st.write(unit)
    with c3: st.write(ideal_str)
    with c4: val_ini = st.number_input("ini", key=f"ini_{key}", label_visibility="collapsed", value=None)
    with c5: r_ini = evaluar_y_mostrar(val_ini, min_val, max_val)
    with c6: val_fin = st.number_input("fin", key=f"fin_{key}", label_visibility="collapsed", value=None)
    with c7: r_fin = evaluar_y_mostrar(val_fin, min_val, max_val)
    return r_ini, r_fin 

def fila_libre(param, unit, ideal_str, key):
    c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 1, 1, 1.5, 1.5, 1.5, 1.5])
    with c1: st.write(param)
    with c2: st.write(unit)
    with c3: st.write(ideal_str)
    with c4: st.number_input("ini", key=f"ini_{key}", label_visibility="collapsed", value=None)
    with c5: st.text_input("c_ini", key=f"c_ini_{key}", label_visibility="collapsed")
    with c6: st.number_input("fin", key=f"fin_{key}", label_visibility="collapsed", value=None)
    with c7: st.text_input("c_fin", key=f"c_fin_{key}", label_visibility="collapsed")
    return None, None

def fila_comp(nombre, key, placeholder="Especificar detalles..."):
    c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 3])
    with c1: st.write(nombre)
    with c2: st.selectbox("Estado", ["-", "Bueno 🟢", "Malo 🔴"], key=f"est_{key}", label_visibility="collapsed")
    with c3: st.selectbox("Limpieza", ["-", "Sí 🟢", "No 🔴"], key=f"limp_{key}", label_visibility="collapsed")
    with c4: st.selectbox("Reemplazo", ["-", "Sí 🟢", "No 🔴"], key=f"reemp_{key}", label_visibility="collapsed")
    with c5: st.text_input("Obs", placeholder=placeholder, key=f"obs_{key}", label_visibility="collapsed")

# ==========================================
# 1. DATOS DEL ANALIZADOR
# ==========================================
with st.expander("🛠️ DATOS DEL ANALIZADOR Y CONDICIONES AMBIENTALES", expanded=True):
    col_izq, col_der = st.columns([1, 1.2])
    with col_izq:
        estaciones = ["Selecciona una opción..."] + list(equipos_act.keys())
        estacion_sel = st.selectbox("Estación:", estaciones)
        
        fab_final = "ACOEM"; mod_final = modelo_analizador
        if gas_sel == "Monóxido de Carbono (CO)" and estacion_sel == "Águilas": mod_final = "ML9830"
        elif gas_sel == "Dióxido de Azufre (SO2)" and estacion_sel in ["Pintas", "Centro", "Oblatos", "Tlaquepaque"]: fab_final = "ECOTECH"
            
        st.text_input("Fabricante", value=fab_final)
        st.text_input("Modelo", value=mod_final)
        
        num_serie_val = equipos_act.get(estacion_sel, "")
        st.text_input("N/S (Automático)", value=num_serie_val, disabled=True)
        st.number_input("Presión ambiental ÚNICA (Torr)", value=634.0)
        
        falla = st.selectbox("El analizador presenta Falla o Alarma", ["-", "No 🟢", "Sí 🔴"])
        if falla == "Sí 🔴":
            st.text_area("Descripción de Falla o Alarma", placeholder="Mencionar falla, alarma o anormalidad...")

    with col_der:
        st.markdown("#### ")
        col_ini, col_fin = st.columns(2)
        with col_ini:
            st.markdown("### Inicial")
            fecha_ref = st.date_input("Fecha (Inicial)", datetime.date.today(), max_value=datetime.date.today())
            st.time_input("Hora (Inicial)", value=None)
            st.number_input("Temp exterior (C°) - Ini", value=0.0)
            st.number_input("Temp interior (C°) - Ini", value=0.0)

        with col_fin:
            st.markdown("### Final")
            st.date_input("Fecha (Final)", datetime.date.today(), max_value=datetime.date.today())
            st.time_input("Hora (Final)", value=None)
            st.number_input("Temp exterior (C°) - Fin", value=0.0)
            st.number_input("Temp interior (C°) - Fin", value=0.0)

# ==========================================
# 2. HISTÓRICO
# ==========================================
with st.expander("📅 HISTÓRICO DE MANTENIMIENTOS", expanded=False):
    def fila_historico(nombre_mant, key_fecha, fecha_default, periodicidad_meses):
        c1, c2, c3, c4 = st.columns([2, 1.5, 1, 1.5])
        with c1: st.write(nombre_mant)
        with c2: fecha_ult = st.date_input(f"Fecha {key_fecha}", value=fecha_default, max_value=datetime.date.today(), label_visibility="collapsed")
        with c3: st.write(str(periodicidad_meses))
        with c4:
            es_req = (fecha_ref - fecha_ult).days > (periodicidad_meses * 30)
            if es_req: st.error("Requerido")
            else: st.success("No Requerido")
            return es_req

    req_basico = fila_historico("Mantenimiento Básico", "basico", datetime.date(2026, 5, 10), 1)
    req_cs = fila_historico("Verificación Cero-Span", "cero_span", datetime.date(2026, 1, 1), 3)
    req_comp = fila_historico("Mantenimiento Completo", "completo", datetime.date(2025, 1, 1), 6)

abrir_basico = req_basico or req_comp
abrir_cs = req_cs or req_comp

# ==========================================
# 3. CALIBRACIÓN MULTIPUNTO (Data Editor)
# ==========================================
with st.expander("📈 CALIBRACIÓN MULTIPUNTO", expanded=True):
    col_pts, col_res = st.columns([1.2, 1])
    
    with col_pts:
        st.markdown("#### Ingreso de Datos")
        # Generar DataFrame inicial
        df_multi = pd.DataFrame({
            "Punto": [1, 2, 3, 4, 5],
            "Patrón (ppb/ppm)": puntos_multipunto,
            "Analizador (ppb/ppm)": [0.0]*5
        })
        
        # Data Editor Interactivo (Mucho más limpio que columnas)
        edited_df = st.data_editor(
            df_multi, 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Punto": st.column_config.NumberColumn(disabled=True),
                "Patrón (ppb/ppm)": st.column_config.NumberColumn(disabled=True),
                "Analizador (ppb/ppm)": st.column_config.NumberColumn(format="%.4f")
            }
        )
        
        x_vals = []
        y_vals = []
        
        for idx, row in edited_df.iterrows():
            if row["Analizador (ppb/ppm)"] > 0 or row["Patrón (ppb/ppm)"] == min(puntos_multipunto):
                x_vals.append(row["Patrón (ppb/ppm)"])
                y_vals.append(row["Analizador (ppb/ppm)"])

    m, b, r2 = None, None, None
    if len(x_vals) > 1:
        try:
            x_arr, y_arr = np.array(x_vals), np.array(y_vals)
            m, b = np.polyfit(x_arr, y_arr, 1)
            r2 = (np.corrcoef(x_arr, y_arr)[0,1])**2
        except: pass

    with col_res:
        st.markdown("#### Resultados de Regresión")
        if m is not None:
            # Componente nativo st.metric para un look industrial
            m1, m2 = st.columns(2)
            m1.metric("Pendiente (m)", f"{m:.5f}", delta=f"{m - 1:.5f} offset", delta_color="inverse")
            m2.metric("Intercepto (b)", f"{b:.5f}")
            
            st.metric("Coef. Determinación (R²)", f"{r2:.6f}")
            
            cond_m = 0.98 <= m <= 1.02
            cond_b = -2.0 <= b <= 2.0
            cond_r2 = 0.99 <= r2 <= 1.0
            
            if cond_m and cond_b and cond_r2:
                st.success("✅ **DICTAMEN APROBADO** - La curva cumple con todos los criterios.")
            else:
                st.error("❌ **DICTAMEN RECHAZADO** - Revise los puntos o el analizador.")
        else:
            st.info("Ingrese los valores de lectura del analizador para generar la regresión.")

    # Gráfica Científica con Plotly
    if len(x_vals) > 1 and m is not None:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='markers+text', name='Analizador',
                                 text=[f"{v:.4f}" for v in y_vals], textposition="top left", 
                                 marker=dict(size=12, color='#00B2A9', line=dict(width=2, color='DarkSlateGrey'))))
        
        x_line = np.linspace(0, max(x_vals)*1.1, 100)
        fig.add_trace(go.Scatter(x=x_line, y=m * x_line + b, mode='lines', name=f'y = {m:.4f}x + {b:.4f}', 
                                 line=dict(color='#F37021', width=3, dash='dash')))
        
        fig.update_layout(
            title=f"Curva de Calibración | y = {m:.4f}x + {b:.4f} | R² = {r2:.6f}",
            xaxis_title="Concentración Patrón",
            yaxis_title="Respuesta del Analizador",
            template="plotly_white", # Estilo de publicación científica
            height=450,
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 10. RESUMEN Y FIRMAS
# ==========================================
with st.expander("✍️ RESUMEN Y FIRMAS FINALES", expanded=True):
    st.markdown("**Observaciones Generales**")
    st.text_area("Obs Gen", placeholder="Mencionar anomalías, limpieza de óptica, reemplazo de filtros...", label_visibility="collapsed")
    
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Empresa/Institución", value="Secretaría de Medio Ambiente y Desarrollo Territorial", key="e_tec")
        st.text_input("Técnico", value="Jaudiel Alejandro Jaime Lomelí", key="n_tec")
    with c2:
        st.text_input("Empresa/Institución ", value="Secretaría de Medio Ambiente y Desarrollo Territorial", key="e_sup")
        st.text_input("Supervisor", value="Beatriz Rodríguez Pérez", key="n_sup")

st.divider()

# ==========================================
# BOTÓN DE IMPRESIÓN (PDF NATIVO DIRECTO COMPRIMIDO)
# ==========================================
components.html(
    """
    <div style="text-align: center; margin-top: 10px;" id="btn-imprimir">
        <button onclick="window.parent.print()" style="padding: 14px 28px; font-size: 18px; font-weight: bold; background-color: #F37021; color: white; border: none; border-radius: 8px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
            🖨️ Descargar Reporte en PDF
        </button>
        <p style="font-family: sans-serif; color: #5C6670; font-size: 14px; margin-top: 10px;">
            (Asegúrate de seleccionar "Guardar como PDF" en el destino)
        </p>
    </div>
    """,
    height=120
)
