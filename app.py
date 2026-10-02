import streamlit as st
import datetime
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import io
import os
import json
from PIL import Image
import streamlit.components.v1 as components
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(layout="wide", page_title="Calibración SIMAJ")

# ==========================================
# CSS GLOBAL Y COMPRESOR EXTREMO PARA PDF
# ==========================================
st.markdown("""
<style>
    h1, h2, h3 { color: #00B2A9 !important; font-weight: 800 !important; }
    h4 { color: #5C6670 !important; margin-bottom: 2px !important; }
    hr { border-bottom: 3px solid #F37021 !important; margin: 1.5em 0 !important; }
    .stAlert { border-left: 5px solid #00B2A9 !important; background-color: #f0fdfa !important; }
    div[data-baseweb="select"] > div { border-color: #00B2A9 !important; }
    
    .header-firma { background-color: #A6A6A6; color: black; font-weight: bold; text-align: center; padding: 5px; border: 1px solid #7a7a7a; margin-bottom: 10px; font-size: 16px; }
    .linea-firma { margin-top: 40px; border-bottom: 1px solid black; width: 100%; height: 25px; }
    .header-tabla { background-color: #e0e0e0; font-weight: bold; text-align: center; padding: 4px; border: 1px solid #ccc; }
    
    @media print {
        @page { size: letter portrait; margin: 1cm 0.5cm; }
        * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
        header, footer, .stDeployButton, [data-testid="stSidebar"], #btn-imprimir { display: none !important; }
        div[role="radiogroup"] { display: none !important; } 
        html, body, [class*="st-"] { font-size: 11px !important; line-height: 1.25 !important; color: black !important; }
        h1 { font-size: 16px !important; margin: 8px 0 4px 0 !important; padding: 0 !important; }
        h2, h3 { font-size: 13px !important; margin: 6px 0 3px 0 !important; padding: 0 !important; }
        h4 { font-size: 11px !important; margin: 4px 0 2px 0 !important; padding: 0 !important; font-weight: bold !important; }
        html, body, .stApp, div[data-testid="stAppViewContainer"], div[data-testid="stMain"] { height: auto !important; overflow: visible !important; position: static !important; }
        .main .block-container { max-width: 100% !important; padding: 0 10px !important; margin-top: -20px !important; }
        [data-testid="column"] { padding: 0 4px !important; }
        [data-testid="stVerticalBlock"] { gap: 0.3rem !important; }
        div[data-testid="stHorizontalBlock"] { gap: 0.3rem !important; align-items: center !important; }
        input[type="text"], input[type="number"], textarea, div[data-baseweb="select"] > div {
            font-size: 10px !important; padding: 2px 4px !important; min-height: 20px !important; height: 22px !important; border: 1px solid #a0a0a0 !important; margin: 0 !important;
        }
        .stSelectbox svg, .stExpander > details > summary > svg { display: none !important; }
        .stExpander { border: 1px solid #ddd !important; border-radius: 4px !important; margin-bottom: 6px !important; page-break-inside: avoid !important; }
        .stExpander summary { padding: 4px 6px !important; min-height: 0 !important; background-color: #f7f7f7 !important; }
        details:not([open]) { display: none !important; }
        hr { margin: 4px 0 !important; border-color: #ddd !important; }
        .stAlert { padding: 4px 8px !important; border-width: 1px !important; margin-bottom: 2px !important; }
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
equipos_pm10 = {"Pintas": "CM17461024", "Santa Fe": "...", "Miravalle": "...", "Centro": "...", "Country": "...", "Atemajac": "...", "Oblatos": "...", "Santa Margarita": "...", "Vallarta": "...", "Loma Dorada": "...", "Águilas": "...", "Santa Anita": "...", "Tlaquepaque": "..."}
equipos_pm25 = {"Pintas": "5014i203281301", "Santa Fe": "DN17069", "Miravalle": "...", "Centro": "...", "Country": "...", "Atemajac": "...", "Oblatos": "...", "Santa Margarita": "...", "Vallarta": "...", "Loma Dorada": "...", "Águilas": "...", "Santa Anita": "...", "Tlaquepaque": "..."}

# ==========================================
# MENÚ SUPERIOR HORIZONTAL Y LOGO
# ==========================================
st.write("<br>", unsafe_allow_html=True)
tipo_servicio = st.radio("Selecciona el Tipo de Servicio:", ["SIMAJ", "Mantenimiento Externo"], horizontal=True)
es_externo = (tipo_servicio == "Mantenimiento Externo")
st.divider()

col_logo, col_menu = st.columns([1, 2.5], gap="large")
with col_logo:
    if os.path.exists("simaj.png"): st.image("simaj.png", width=250)
    else: st.markdown("<h1 style='color:#00B2A9;'>SIMAJ</h1>", unsafe_allow_html=True)

with col_menu:
    st.markdown("#### Selecciona el Equipo a Calibrar:")
    gas_sel = st.radio("Selecciona el Equipo:", ["Ozono (O3)", "Óxidos de Nitrógeno (NOx)", "Monóxido de Carbono (CO)", "Dióxido de Azufre (SO2)", "PM BAM", "PM Thermo"], horizontal=True, label_visibility="collapsed")
    pm_tipo = "N/A"
    if gas_sel in ["PM BAM", "PM Thermo"]:
        pm_tipo = st.radio("Selecciona el Parámetro de Partículas:", ["PM10", "PM2.5"], horizontal=True)

st.divider()
datos_resumen = {}
es_gas = gas_sel in ["Ozono (O3)", "Óxidos de Nitrógeno (NOx)", "Monóxido de Carbono (CO)", "Dióxido de Azufre (SO2)"]
es_bam = gas_sel == "PM BAM"
es_thermo = gas_sel == "PM Thermo"
es_particulas = es_bam or es_thermo

if gas_sel == "Ozono (O3)": equipos_act = equipos_o3; modelo_analizador = "Serinus 10"
elif gas_sel == "Óxidos de Nitrógeno (NOx)": equipos_act = equipos_nox; modelo_analizador = "Serinus 40"
elif gas_sel == "Monóxido de Carbono (CO)": equipos_act = equipos_co; modelo_analizador = "Serinus 30"
elif gas_sel == "Dióxido de Azufre (SO2)": equipos_act = equipos_so2; modelo_analizador = "Serinus 50"
elif es_bam or es_thermo:
    equipos_act = equipos_pm10 if pm_tipo == "PM10" else equipos_pm25
    modelo_analizador = "BAM 1020" if es_bam else "5014i"

# Valores por defecto para mantenimiento externo (en blanco)
fab_cal1_def = "" if es_externo else "Bios International Corp"
mod_cal1_def = "" if es_externo else "Definer 220 M"
lab_cal1_def = "" if es_externo else "COMEXSA"
tec_cal1_def = "" if es_externo else "Lizeth Morales"
fab_cal2_def = "" if es_externo else "ACOEM"
mod_cal2_def = "" if es_externo else "Serinus Cal 3000"
lab_cal2_def = "" if es_externo else "INECC"
tec_cal2_def = "" if es_externo else "Humberto Bustamante"
tec_nombre_def = "" if es_externo else "Jaudiel Alejandro Jaime Lomelí"
sup_nombre_def = "" if es_externo else "Beatriz Rodríguez Pérez"

# ==========================================
# ENCABEZADO
# ==========================================
st.title(f"FORMATO DE CALIBRACIÓN {gas_sel}" if es_gas else f"FORMATO DE CALIBRACIÓN {gas_sel} ({pm_tipo})")
st.subheader("Parámetros Generales - Monitor de " + ("Gases" if es_gas else "Partículas"))

# ==========================================
# FUNCIONES AUXILIARES GLOBALES
# ==========================================
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
    with c4: st.text_input("ini", key=f"ini_{key}", label_visibility="collapsed")
    with c5: st.text_input("c_ini", key=f"c_ini_{key}", label_visibility="collapsed")
    with c6: st.text_input("fin", key=f"fin_{key}", label_visibility="collapsed")
    with c7: st.text_input("c_fin", key=f"c_fin_{key}", label_visibility="collapsed")
    return None, None

def fila_comp(nombre, key, placeholder="Especificar..."):
    c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 3])
    with c1: st.write(nombre)
    with c2: st.selectbox("Estado", ["-", "Bueno 🟢", "Malo 🔴"], key=f"est_{key}", label_visibility="collapsed")
    with c3: st.selectbox("Limpieza", ["-", "Sí 🟢", "No 🔴"], key=f"limp_{key}", label_visibility="collapsed")
    with c4: st.selectbox("Reemplazo", ["-", "Sí 🟢", "No 🔴"], key=f"reemp_{key}", label_visibility="collapsed")
    with c5: st.text_input("Obs", placeholder=placeholder, key=f"obs_{key}", label_visibility="collapsed")

def fila_simple(nombre, key, ph="No se realizó"):
    c1, c2 = st.columns([1, 2])
    with c1: st.write(nombre)
    with c2: st.text_input("obs", key=key, label_visibility="collapsed", placeholder=ph)

# ==========================================
# 1. DATOS DEL ANALIZADOR
# ==========================================
with st.expander("🛠 DATOS DEL ANALIZADOR Y CONDICIONES AMBIENTALES", expanded=True):
    col_izq, col_der = st.columns([1, 1.2])
    with col_izq:
        estaciones = ["Selecciona una opción..."] + list(equipos_act.keys())
        estacion_sel = st.selectbox("Estación:", estaciones)
        
        fab_final = "ACOEM" if es_gas else ("Met One" if es_bam else "Thermo Fisher")
        mod_final = modelo_analizador
        if gas_sel == "Monóxido de Carbono (CO)" and estacion_sel == "Águilas": mod_final = "ML9830"
        elif gas_sel == "Dióxido de Azufre (SO2)" and estacion_sel in ["Pintas", "Centro", "Oblatos", "Tlaquepaque"]: fab_final = "ECOTECH"
            
        st.text_input("Fabricante", value=fab_final)
        st.text_input("Modelo", value=mod_final)
        num_serie_val = equipos_act.get(estacion_sel, "")
        st.text_input("N/S (Automático)", value=num_serie_val, disabled=True)
        st.number_input("Presión ambiental ÚNICA (Torr)", value=634.0)
        
        falla = st.selectbox("El analizador presenta Falla o Alarma", ["-", "No 🟢", "Sí 🔴"])
        if falla == "Sí 🔴": st.text_area("Descripción de Falla o Alarma")

        datos_resumen["Estación"] = estacion_sel
        datos_resumen["Gas Calibrado"] = gas_sel if es_gas else f"{gas_sel} ({pm_tipo})"

    with col_der:
        st.markdown("#### ")
        col_ini, col_fin = st.columns(2)
        with col_ini:
            st.markdown("### Inicial")
            fecha_ref = st.date_input("Fecha (Inicial)", datetime.date.today(), max_value=datetime.date.today())
            st.time_input("Hora (Inicial)", value=None)
            st.number_input("Temp exterior (C°) - Ini", value=0.0)
            st.number_input("Temp interior (C°) - Ini", value=0.0)
            datos_resumen["Fecha de Servicio"] = str(fecha_ref)
        with col_fin:
            st.markdown("### Final")
            st.date_input("Fecha (Final)", datetime.date.today(), max_value=datetime.date.today())
            st.time_input("Hora (Final)", value=None)
            st.number_input("Temp exterior (C°) - Fin", value=0.0)
            st.number_input("Temp interior (C°) - Fin", value=0.0)

# ==========================================
# 2. HISTÓRICO (SE OCULTA EN MANTENIMIENTO EXTERNO)
# ==========================================
if not es_externo:
    with st.expander("📅 HISTÓRICO DE MANTENIMIENTOS", expanded=True):
        h1, h2, h3, h4 = st.columns([2, 1.5, 1, 1.5])
        with h1: st.write("**Mantenimiento**")
        with h2: st.write("**Fecha de último registro**")
        with h3: st.write("**Periodicidad (Mes)**")
        with h4: st.write("**Mantenimiento Requerido**")

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
else:
    req_basico = req_cs = req_comp = True

# ==========================================
# 3. PARÁMETROS GENERALES
# ==========================================
with st.expander("📊 REVISIÓN DE PARÁMETROS GENERALES", expanded=req_basico):
    h1, h2, h3, h4, h5, h6, h7 = st.columns([2, 1, 1, 1.5, 1.5, 1.5, 1.5])
    with h1: st.write("**Parámetro**")
    with h2: st.write("**Unidades**")
    with h3: st.write("**Ideal**")
    with h4: st.write("**Inicial**")
    with h5: st.write("**Comentarios**")
    with h6: st.write("**Final**")
    with h7: st.write("**Comentarios**")

    resultados_pg = []
    def procesar_resultado(r_ini, r_fin):
        if r_fin is not None: resultados_pg.append(r_fin)
        elif r_ini is not None: resultados_pg.append(r_ini)

    if gas_sel == "Ozono (O3)":
        fila_libre("Flujo Estándar", "cc/min", "500", "o3_f_est")
        procesar_resultado(*fila_regla("Flujo Volumétrico", "cc/min", "500", 487.5, 512.5, "o3_f_vol"))
        procesar_resultado(*fila_regla("Presión de gas", "Torr", "629", 619.0, 630.0, "o3_p_gas"))
        procesar_resultado(*fila_regla("Voltaje de referencia", "Volts", "1.4 - 4", 1.4, 4.0, "o3_v_ref"))
        procesar_resultado(*fila_regla("Corriente de la lámpara", "mA", "9.5 - 10.5", 9.5, 10.5, "o3_c_lamp"))
        procesar_resultado(*fila_regla("Temperatura de la lámpara", "°C", "45 - 55", 45.0, 55.0, "o3_t_lamp"))
        procesar_resultado(*fila_regla("Pot de la lámpara UV", "N/A", "254", 254.0, 254.0, "o3_pot"))
        procesar_resultado(*fila_regla("Temperatura del Chassis", "°C", "0 - 50", 0.0, 50.0, "o3_t_chas"))
        procesar_resultado(*fila_regla("Temperatura del flujo", "°C", "10 - 90", 10.0, 90.0, "o3_t_flujo"))
        procesar_resultado(*fila_regla("INPUT (Pots)", "N/A", "50-200", 50.0, 200.0, "o3_in"))
        fila_libre("Ganancia", "N/A", "N/A", "o3_gan")
        
    elif gas_sel == "Óxidos de Nitrógeno (NOx)":
        fila_libre("Flujo Estándar", "cc/min", "650", "nox_f_est")
        procesar_resultado(*fila_regla("Flujo Volumétrico", "cc/min", "650", 617.5, 682.5, "nox_f_vol"))
        procesar_resultado(*fila_regla("Presión de gas", "Torr", "80-300", 80.0, 300.0, "nox_p_gas"))
        procesar_resultado(*fila_regla("Temp. celda de reaccion", "°C", "50 ±10%", 45.0, 55.0, "nox_t_celda"))
        procesar_resultado(*fila_regla("Temp. del convertidor", "°C", "250-335", 250.0, 335.0, "nox_t_conv"))
        procesar_resultado(*fila_regla("Temperatura del Chassis", "°C", "0-50", 0.0, 50.0, "nox_t_chas"))
        procesar_resultado(*fila_regla("Temperatura de Manifold", "°C", "50", 45.0, 55.0, "nox_t_man"))
        procesar_resultado(*fila_regla("Temperatura de Cooler", "°C", "13 ±10%", 11.7, 14.3, "nox_t_cool"))
        procesar_resultado(*fila_regla("Alto voltaje", "Volt", "640-670", 640.0, 670.0, "nox_alto_v"))
        procesar_resultado(*fila_regla("Flujo de vacio", "torr", "50-200", 50.0, 200.0, "nox_f_vacio"))
        fila_libre("Ganancia", "N/A", "N/A", "nox_gan")
        
    elif gas_sel == "Monóxido de Carbono (CO)":
        fila_libre("Flujo Estándar", "cc/min", "1000", "co_f_est")
        procesar_resultado(*fila_regla("Flujo Volumétrico", "cc/min", "1000", 975.0, 1025.0, "co_f_vol"))
        fila_libre("Presión de celda", "Torr", "631.7", "co_p_celda") 
        procesar_resultado(*fila_regla("IR Source", "Volt", "5 ± 0.5", 4.5, 5.5, "co_ir"))
        procesar_resultado(*fila_regla("Temp. de Scrubber", "°C", "90 ± 10", 80.0, 100.0, "co_t_scrub"))
        procesar_resultado(*fila_regla("Voltaje de referencia", "Volt", "3.6 - 4.4", 3.6, 4.4, "co_v_ref"))
        procesar_resultado(*fila_regla("Voltaje de concentración", "Volt", "0 - 3.1", 0.0, 3.1, "co_v_conc"))
        procesar_resultado(*fila_regla("Temp. celda de reaccion", "°C", "50", 45.0, 55.0, "co_t_celda"))
        procesar_resultado(*fila_regla("Temperatura del Chassis", "°C", "0-50", 0.0, 50.0, "co_t_chas"))
        procesar_resultado(*fila_regla("Temperatura de flujo", "°C", "50", 45.0, 55.0, "co_t_flujo"))
        procesar_resultado(*fila_regla("Temperatura del espejo", "°C", "50 ± 10", 40.0, 60.0, "co_t_esp"))
        procesar_resultado(*fila_regla("INPUT (Pots)", "N/A", "180-230", 180.0, 230.0, "co_in"))
        fila_libre("Ganancia", "N/A", "N/A", "co_gan")
        
    elif gas_sel == "Dióxido de Azufre (SO2)":
        fila_libre("Flujo", "cc/min", "700", "so2_f_vol")
        fila_libre("Presión de gas", "Torr", "-", "so2_p_gas")
        procesar_resultado(*fila_regla("Voltaje de referencia", "Volts", "1.5 - 3.5", 1.5, 3.5, "so2_v_ref"))
        procesar_resultado(*fila_regla("Corriente de la lámpara", "mA", "34 - 36", 34.0, 36.0, "so2_c_lamp"))
        procesar_resultado(*fila_regla("Alto voltaje", "Volts", "690 - 715", 690.0, 715.0, "so2_alto_v"))
        procesar_resultado(*fila_regla("Temperatura del Chassis", "°C", "0 - 50", 0.0, 50.0, "so2_t_chas"))
        procesar_resultado(*fila_regla("Temperatura de celda", "°C", "47-53", 47.0, 53.0, "so2_t_celda"))
        procesar_resultado(*fila_regla("Temperatura del Cooler", "°C", "11.7-14.3", 11.7, 14.3, "so2_t_cool"))
        procesar_resultado(*fila_regla("Temperatura del bloque", "°C", "50", 45.0, 55.0, "so2_t_bloq"))
        fila_libre("Valor de la ganancia", "-", "-", "so2_gan")
        procesar_resultado(*fila_regla("Valor de ajuste POT lámpara", "-", "10-100", 10.0, 100.0, "so2_pot"))

    elif es_bam:
        # PM BAM: Adiós flujo volumétrico, puros parámetros crudos
        fila_libre("Reloj Horario/fecha", "N/A", "N/A", "bam_reloj")
        fila_libre("RS232", "N/A", "N/A", "bam_rs232")
        fila_libre("Rango de operación", "mg", "0 - 1,000", "bam_rango")
        fila_libre("BAM Sample", "min", "50", "bam_bsamp")
        fila_libre("MET Sample", "min", "60", "bam_msamp")
        fila_libre("Offset", "mg", "0", "bam_off")
        c_time = "4" if pm_tipo == "PM10" else "8"
        fila_libre("Count time", "min", c_time, "bam_ctime")
        fila_libre("CONC type", "N/A", "ACTUAL", "bam_conc")
        procesar_resultado(*fila_regla("Flujo Nominal", "L/min", "16.28 - 17.11", 16.28, 17.11, "bam_fnom"))
        procesar_resultado(*fila_regla("Temperatura de flujo", "°C", "5 - 60", 5.0, 60.0, "bam_tflujo"))
        procesar_resultado(*fila_regla("Temperatura Ambiental", "°C", "4 - 50", 4.0, 50.0, "bam_tamb"))
        procesar_resultado(*fila_regla("Presión sobre filtro (AP)", "mmHg", "0 - 500", 0.0, 500.0, "bam_pfilt"))
        procesar_resultado(*fila_regla("Presión Barométrica", "mmHg", "400 - 800", 400.0, 800.0, "bam_pbaro"))
        procesar_resultado(*fila_regla("Presión de vacío de la muestra", "mmHg", "-5 a 250", -5.0, 250.0, "bam_pvac"))
        procesar_resultado(*fila_regla("Traza (Heater)", "°C", "1 - 99", 1.0, 99.0, "bam_traza"))
        fila_libre("Control de Humedad Relativa", "N/A", "SI", "bam_chum")
        procesar_resultado(*fila_regla("Humedad relativa de la muestra", "%", "20 - 45", 20.0, 45.0, "bam_hrmues"))
        procesar_resultado(*fila_regla("Humedad relativa ambiental", "%", "5 - 95", 5.0, 95.0, "bam_hramb"))

    elif es_thermo:
        # PM Thermo: Adiós volumétricos, solo Nominal y Raw
        fila_libre("Rango de operación", "ug/m3", "0 - 1000", "th_rango")
        fila_libre("Tiempo de integración", "Minutos", "20", "th_tint")
        procesar_resultado(*fila_regla("Flujo Nominal", "L/min", "16.67", 16.00, 17.34, "th_fnom"))
        procesar_resultado(*fila_regla("Braw", "N/A", "5000 - 20000", 5000.0, 20000.0, "th_braw"))
        procesar_resultado(*fila_regla("Bzero", "N/A", "0", -500.0, 500.0, "th_bzero")) # Tolerancia típica
        procesar_resultado(*fila_regla("Alpha", "N/A", "0 - 100", 0.0, 100.0, "th_alpha"))
        procesar_resultado(*fila_regla("Temperatura Ambiental", "°C", "4 - 50", 4.0, 50.0, "th_tamb"))
        procesar_resultado(*fila_regla("Presión Barométrica", "mmHg", "400 - 800", 400.0, 800.0, "th_pbaro"))
        procesar_resultado(*fila_regla("Humedad relativa ambiental", "%", "5 - 95", 5.0, 95.0, "th_hr_amb"))
        procesar_resultado(*fila_regla("Humedad relativa de la muestra", "%", "5 - 95", 5.0, 95.0, "th_hr_mues"))
        procesar_resultado(*fila_regla("Presión de vacío de la muestra", "mmHg", "-5 a 250", -5.0, 250.0, "th_pvac"))
        procesar_resultado(*fila_regla("Temperatura de flujo", "°C", "5 - 60", 5.0, 60.0, "th_tflujo"))
        procesar_resultado(*fila_regla("Temperatura de la tarjeta", "°C", "5 - 60", 5.0, 60.0, "th_ttarj"))

# ==========================================
# 4. VERIFICACIÓN Y CALIBRACIÓN DE SENSORES Y FLUJO (PM)
# ==========================================
if es_particulas:
    with st.expander("🛠 VERIFICACIÓN Y CALIBRACIÓN DE SENSORES Y FLUJO", expanded=req_comp):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("**Calibrador (Sensores y Flujo)**")
            st.text_input("Marca", value="Mesa Labs" if not es_externo else "", key="pm_cal_mca")
            st.text_input("Modelo", value="DeltaCal DC1" if not es_externo else "", key="pm_cal_mod")
            st.text_input("N/S", value="152892" if not es_externo else "", key="pm_cal_ns")
        with col_c2:
            st.markdown("**Certificación**")
            st.text_input("Laboratorio", value="Comexsa" if not es_externo else "", key="pm_cal_lab")
            st.date_input("Fecha de calibración", datetime.date(2026, 1, 20), key="pm_cal_fecha")
            st.text_input("No de certificado", value="E252677468" if not es_externo else "", key="pm_cal_cert")

        st.divider()

        if es_thermo:
            # BLOQUE THERMO (3 Puntos Temp y Humedad)
            def sensor_3p(titulo, limite_dif, val_ideal_desc):
                st.markdown(f"#### {titulo}")
                c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
                with c1: st.write("**Calibrador**")
                with c2: st.write("**Monitor**")
                with c3: st.write("**Diferencia**")
                
                cal_v, mon_v = [], []
                for i in range(1, 4):
                    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
                    with c1: c_val = st.number_input(f"c{i}", key=f"{titulo}_c{i}", label_visibility="collapsed", value=None)
                    with c2: m_val = st.number_input(f"m{i}", key=f"{titulo}_m{i}", label_visibility="collapsed", value=None)
                    with c3:
                        if c_val is not None and m_val is not None: st.write(f"{(m_val - c_val):.2f}")
                        else: st.write("-")
                    if c_val is not None: cal_v.append(c_val)
                    if m_val is not None: mon_v.append(m_val)
                
                c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
                with c1:
                    prom_c = sum(cal_v)/len(cal_v) if cal_v else None
                    st.write(f"**{prom_c:.2f}**" if prom_c else "Promedio")
                with c2:
                    prom_m = sum(mon_v)/len(mon_v) if mon_v else None
                    st.write(f"**{prom_m:.2f}**" if prom_m else "Promedio")
                with c3:
                    if prom_c and prom_m:
                        dif_prom = prom_m - prom_c
                        if abs(dif_prom) <= limite_dif: st.success(f"{dif_prom:.2f}")
                        else: st.error(f"{dif_prom:.2f}")
                    else: st.write("-")
                with c4:
                    st.text_input("Comentarios", key=f"{titulo}_obs", placeholder="Comentarios...", label_visibility="collapsed")
                    st.write(f"<small>{val_ideal_desc}</small>", unsafe_allow_html=True)
            
            col_izq, col_der = st.columns(2)
            with col_izq:
                sensor_3p("Temperatura Ambiente", 2.0, "La diferencia debe ser menor a ± 2 °C")
                sensor_3p("Humedad Relativa", 2.0, "La diferencia debe ser menor a ± 2 %")
                sensor_3p("Temperatura de flujo", 2.0, "La diferencia debe ser menor a ± 2 °C")
            
            with col_der:
                st.markdown("#### Presión Barométrica")
                c1, c2, c3 = st.columns(3); c1.write("Lectura"); c_bar1 = c2.number_input("C_bar_l", label_visibility="collapsed", value=None); m_bar1 = c3.number_input("M_bar_l", label_visibility="collapsed", value=None)
                if c_bar1 and m_bar1: st.write(f"Diferencia: {abs(m_bar1-c_bar1):.1f} mmHg (Ideal < 10)")
                c1, c2, c3 = st.columns(3); c1.write("Calibración"); c_bar2 = c2.number_input("C_bar_c", label_visibility="collapsed", value=None); m_bar2 = c3.number_input("M_bar_c", label_visibility="collapsed", value=None)
                if c_bar2 and m_bar2: st.write(f"Diferencia: {abs(m_bar2-c_bar2):.1f} mmHg (Ideal < 2)")

                st.markdown("#### Flujo")
                c1, c2, c3 = st.columns(3); c1.write("Calibrador"); c2.write("Monitor"); c3.write("% Desviación")
                c1, c2, c3 = st.columns(3); f_cal = c1.number_input("f_cal", label_visibility="collapsed", value=None); f_mon = c2.number_input("f_mon", label_visibility="collapsed", value=None)
                with c3:
                    if f_cal and f_mon: st.write(f"{((f_mon-f_cal)/f_cal)*100:.2f}%")
                st.write("<small>El valor promedio debe estar entre 16.00 y 17.34 Lpm</small>", unsafe_allow_html=True)

        elif es_bam:
            # BLOQUE BAM (Flujo Litros por Minuto)
            st.markdown("#### Flujo en Litros por Minuto")
            c1, c2, c3, c4 = st.columns([1, 1, 2, 1])
            with c1: st.write("**Calibrador (lpm)**")
            with c2: st.write("**Monitor (lpm)**")
            with c3: st.write("**Comentarios**")
            with c4: st.write("**Requirió Ajuste**")
            
            cal_targets = [15.0, 18.43, 16.67]
            for idx, target in enumerate(cal_targets):
                c1, c2, c3, c4 = st.columns([1, 1, 2, 1])
                with c1: st.number_input(f"Target {idx}", value=target, disabled=True, label_visibility="collapsed", key=f"bam_ft_{idx}")
                with c2: st.number_input(f"Monitor {idx}", value=None, label_visibility="collapsed", key=f"bam_fm_{idx}")
                with c3:
                    if idx == 0: st.text_area("Observaciones Generales", key="bam_f_obs", height=90, label_visibility="collapsed")
                with c4:
                    if idx == 0: st.radio("¿Calibró?", ["No", "Sí"], key="bam_f_cal", horizontal=True, label_visibility="collapsed")
            
            st.write("<small>El valor del flujo debe ser 16.67 ±0.67 lpm</small>", unsafe_allow_html=True)

    with st.expander("⚖️ CALIBRACIÓN DE MASAS (FOILS)", expanded=req_comp):
        st.markdown("#### Ingreso de datos de Foils de Calibración")
        col_cm1, col_cm2 = st.columns(2)
        with col_cm1:
            st.text_input("Equipo de Calibración (Foils)", placeholder="Ej. Foil Set CM3534", key="cm_eq")
            st.text_input("Reference No. / Certificado", placeholder="Ej. FH125C14", key="cm_ref")
        with col_cm2:
            st.date_input("Fecha de Certificación de Foils", datetime.date(2025, 11, 12), key="cm_fecha")
            st.number_input("Mass Coefficient Inicial", value=7000.0, key="cm_mass_ini")
        
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1: st.write("**Lectura**")
        with c2: st.write("**Foil Value Span (Ideal)**")
        with c3: st.write("**Beta Average (Lectura del equipo)**")
        
        c1, c2, c3 = st.columns(3)
        with c1: st.write("Calibración Cero")
        with c2: st.write("N/A")
        with c3: st.number_input("Beta Cero", value=0.0, key="cm_beta_cero", label_visibility="collapsed")
        
        c1, c2, c3 = st.columns(3)
        with c1: st.write("Calibración Span")
        with c2: st.number_input("Span Ideal", value=1000.0, key="cm_span_ideal", label_visibility="collapsed")
        with c3: st.number_input("Beta Span", value=0.0, key="cm_beta_span", label_visibility="collapsed")

# ==========================================
# 5. VERIFICACIÓN Y AJUSTE DE FLUJO (SÓLO GASES)
# ==========================================
if es_gas:
    with st.expander("💨 VERIFICACIÓN Y AJUSTE DE FLUJO", expanded=req_basico):
        col_cal1, col_cal2 = st.columns(2)
        with col_cal1:
            st.markdown("**Calibrador de Flujo**")
            st.text_input("Fabricante", value=fab_cal1_def, key="fab_cal1")
            st.text_input("Modelo", value=mod_cal1_def, key="mod_cal1")
            st.text_input("N/S Calibrador de Flujo", key="ns_cal1")

        with col_cal2:
            st.markdown("**Certificación**")
            st.text_input("Laboratorio", value=lab_cal1_def, key="lab_cal1")
            st.text_input("Técnico", value=tec_cal1_def, key="tec_cal1")
            st.date_input("Vigente hasta", datetime.date(2026, 6, 20), key="vig_cal1")
            st.text_input("No de certificado", value=cert_cal1_def, key="cert_cal1")

        def render_tabla_flujo_gases(titulo, key_prefix):
            st.markdown(f"#### {titulo}")
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1.5, 1.5, 1.5])
            with c1: st.write("Flujo Estandar (cc/min)")
            with c2: st.write("-")
            with c3: st.number_input("val_est", key=f"{key_prefix}_est", label_visibility="collapsed")
            with c4: st.write("-")
            with c5: st.write("-")

            c1, c2, c3, c4, c5 = st.columns([2, 1, 1.5, 1.5, 1.5])
            with c1: st.write("Flujo Volumétrico (cc/min)")
            with c2: st.write(str(flujo_ideal_vol))
            with c3: val = st.number_input("val_vol", key=f"{key_prefix}_vol", label_visibility="collapsed")
            with c4: 
                if val: st.write(f"{((val-flujo_ideal_vol)/flujo_ideal_vol)*100:.2f}%")
            return val

        flujo_vol_verif = render_tabla_flujo_gases("Verificación", "verif")
        req_ajuste_final = "SÍ" if (flujo_vol_verif and abs(flujo_vol_verif - flujo_ideal_vol)/flujo_ideal_vol > flujo_tol) else "No"
        st.markdown(f"#### ¿Requiere ajuste volumétrico?: **{req_ajuste_final}**")

        if req_ajuste_final == "SÍ":
            render_tabla_flujo_gases("Ajuste", "ajus")

# ==========================================
# EVIDENCIAS FOTOGRÁFICAS (SÓLO MANTENIMIENTO EXTERNO)
# ==========================================
if es_externo:
    with st.expander("📷 EVIDENCIAS FOTOGRÁFICAS (PROVEEDOR)", expanded=True):
        st.markdown("**Sube las fotografías que evidencian el mantenimiento (Se comprimirán para no saturar la memoria).**")
        fotos_subidas = st.file_uploader("Seleccionar Imágenes", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        if fotos_subidas:
            columnas_fotos = st.columns(3)
            for i, foto in enumerate(fotos_subidas):
                with columnas_fotos[i % 3]:
                    img = Image.open(foto)
                    img.thumbnail((800, 800))
                    st.image(img, use_container_width=True)
                    st.text_input("Descripción:", key=f"desc_foto_{i}", placeholder="Ej. Filtro reemplazado...")

# ==========================================
# 6. LIMPIEZA, REVISIÓN Y REEMPLAZO (PM Separado)
# ==========================================
with st.expander("🔍 LIMPIEZA, REVISIÓN Y REEMPLAZO", expanded=req_basico):
    if es_gas:
        c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 3])
        with c1: st.write("**Componente**")
        with c2: st.write("**Estado**")
        with c3: st.markdown("<b>Limpieza</b>", unsafe_allow_html=True)
        with c4: st.markdown("<b>Reemplazo</b>", unsafe_allow_html=True)
        with c5: st.write("**Observaciones**")

        fila_comp("Bomba de Vacío externa", "d_bomba")
        fila_comp("Tarjetas electrónicas", "d_tarj")
        fila_comp("Fuente de voltaje", "d_fvolt")
    
    elif es_particulas:
        st.markdown("<div class='header-tabla'>Limpieza de:</div>", unsafe_allow_html=True)
        fila_simple("Gabinete", "limp_gab")
        fila_simple("Tubo de la traza", "limp_tub")
        fila_simple("Cabezal", "limp_cab")
        if es_thermo: fila_simple("Cortador de Partículas", "limp_cort")
        fila_simple("Tarjetas Electrónicas" if es_thermo else "Tarjetas", "limp_tarj")
        fila_simple("Ventiladores" if es_thermo else "Ventilador", "limp_vent")
        fila_simple("Celda de medición", "limp_celd")

        st.markdown("<div class='header-tabla'>Revisión de:</div>", unsafe_allow_html=True)
        fila_simple("Display", "rev_disp", "En óptimas condiciones")
        fila_simple("Calefactor de la Traza / factor de la Traza", "rev_calf", "Opera correctamente")
        fila_simple("Traza", "rev_traza", "En óptimas condiciones")
        fila_simple("Fugas", "rev_fugas", "Ninguna")
        fila_simple("Fuente de voltaje", "rev_fvolt", "Opera correctamente")
        fila_simple("Cinta de vidrio / filtro", "rev_cinta", "Tiene 1/2 de cinta disponible")
        if es_thermo: fila_simple("Rodamiento de celda", "rev_rod", "En óptimas condiciones")
        fila_simple("Bomba", "rev_bomba", "Opera correctamente")

        st.markdown("<div class='header-tabla'>Reemplazo (en caso de ser necesario) de:</div>", unsafe_allow_html=True)
        if es_thermo: fila_simple("Ventilador de fuente", "reemp_vent")
        fila_simple("Cinta de vidrio / filtro", "reemp_cinta")
        if es_bam: fila_simple("O-rings", "reemp_orings")
        fila_simple("Bomba de Vacío", "reemp_bomba")

# ==========================================
# BLOQUES ESPECÍFICOS PARA GASES (CERO-SPAN Y MULTIPUNTO)
# ==========================================
if es_gas:
    with st.expander("📑 DATOS DEL CALIBRADOR DE GASES", expanded=req_cs):
        col_cal3, col_cal4 = st.columns(2)
        with col_cal3:
            st.text_input("Fabricante", value=fab_cal2_def, key="fab_calib2")
            st.text_input("Modelo", value=mod_cal2_def, key="mod_calib2")
            st.text_input("N/S Calibrador de Gases", key="ns_calib2")
        with col_cal4:
            st.markdown("**Certificación**")
            st.text_input("Laboratorio", value=lab_cal2_def, key="lab_calib2")
            st.text_input("Técnico", value=tec_cal2_def, key="tec_calib2")
            st.date_input("Vigente hasta", datetime.date(2026, 8, 8), key="vig_calib2")

    with st.expander("⚖️ VERIFICACIÓN CERO-SPAN", expanded=req_cs):
        col_cs_izq, col_cs_der = st.columns(2)
        with col_cs_izq:
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1: st.write("")
            with c2: st.write("**Inicial**")
            with c3: st.write("**Final**")
            
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1: st.write("Ganancia")
            with c2: st.number_input("ini", key="cs_g_i", label_visibility="collapsed")
            with c3: st.number_input("fin", key="cs_g_f", label_visibility="collapsed")
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1: st.write("Zero Offset (ppb/ppm)")
            with c2: st.number_input("ini", key="cs_z_i", label_visibility="collapsed")
            with c3: st.number_input("fin", key="cs_z_f", label_visibility="collapsed")

        with col_cs_der:
            st.markdown("**Tiempo de respuesta al suministrar gas**")
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1: st.write("Cero")
            with c2: st.number_input("val", key="tr_c", label_visibility="collapsed")
            with c3: st.write("min")

        col_cs_cero, col_cs_span = st.columns(2)
        dif_c = desv_s = None
        
        with col_cs_cero:
            st.markdown("#### Concentración Cero")
            c1, c2, c3 = st.columns(3)
            with c1: val_cg = st.number_input("Cero Gen", value=0.001, disabled=True, key="vcg")
            with c2: resp_c = st.number_input("Resp Cero", value=0.000, format="%.4f", key="rac")
            with c3:
                if resp_c is not None:
                    dif_c = resp_c - val_cg
                    st.write(f"Dif: **{dif_c:.4f}**")
                    if -cero_tol <= dif_c <= cero_tol: st.success("Cumple ✅")
                    else: st.error("NO CUMPLE ❌")
        with col_cs_span:
            st.markdown("#### Concentración Span")
            c1, c2, c3 = st.columns(3)
            with c1: val_sg = st.number_input("Span Gen", value=span_gen_default, disabled=True, key="vsg")
            with c2: resp_s = st.number_input("Resp Span", value=0.000, format="%.4f", key="ras")
            with c3:
                if resp_s is not None and val_sg != 0:
                    desv_s = (resp_s - val_sg) / val_sg
                    st.write(f"% desv: **{desv_s * 100:.2f}%**")
                    if -0.03 <= desv_s <= 0.03: st.success("Cumple ✅")
                    else: st.error("NO CUMPLE ❌")

    with st.expander("📈 CALIBRACIÓN MULTIPUNTO", expanded=req_comp):
        col_pts, col_res = st.columns([1.5, 1])
        with col_pts:
            x_vals, y_vals, desviaciones = [], [], []
            for i, cal_val in enumerate(puntos_multipunto):
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.number_input("cal", value=cal_val, disabled=True, key=f"mc_{i}", label_visibility="collapsed")
                with c2: ana_val = st.number_input("ana", value=None, key=f"ma_{i}", format="%.4f", label_visibility="collapsed")
                with c3:
                    if ana_val is not None:
                        dif = ana_val - cal_val
                        st.write(f"**{dif:.4f}**")
                        if cal_val != 0:
                            desviaciones.append(dif / cal_val)
                            st.write(f"{(dif/cal_val)*100:.2f}%")
                if ana_val is not None: x_vals.append(cal_val); y_vals.append(ana_val)

        m = b = r2 = promedio = None
        if len(x_vals) > 1:
            try:
                m, b = np.polyfit(np.array(x_vals), np.array(y_vals), 1)
                r2 = (np.corrcoef(x_vals, y_vals)[0,1])**2
                if desviaciones: promedio = sum(desviaciones) / len(desviaciones)
            except: pass

        with col_res:
            if m is not None:
                st.metric("Pendiente (m)", f"{m:.5f}")
                st.metric("Intercepto (b)", f"{b:.5f}")
                st.metric("R²", f"{r2:.6f}")
                cond_m = 0.95 <= m <= 1.05
                cond_b = -3.0 <= b <= 3.0
                cond_prom = -0.03 <= promedio <= 0.03 if promedio else False
                if cond_m and cond_b and cond_prom: st.success("✅ MULTIPUNTO APROBADO")
                else: st.error("❌ MULTIPUNTO RECHAZADO")
            else:
                st.info("Ingresa los datos para regresión.")

# ==========================================
# 10. RESUMEN Y FIRMAS
# ==========================================
with st.expander("✍️ RESUMEN Y FIRMAS FINALES", expanded=True):
    st.markdown("**Observaciones Generales**")
    obs_gen = st.text_area("Obs Gen", placeholder="Mencionar anomalías...", label_visibility="collapsed", key="res_obs")
    st.markdown("**Conclusiones**")
    conclusiones = st.text_area("Conclusiones", placeholder="Mencionar conclusiones...", label_visibility="collapsed", key="res_conc")

    st.write("<br>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("<div class='header-firma'>Técnico / Operador</div>", unsafe_allow_html=True)
        st.text_input("Empresa/Ins", value="Secretaría de Medio Ambiente y Desarrollo Territorial" if not es_externo else "", key="e_tec")
        st.text_input("Nombre", value=tec_nombre_def, key="n_tec")
        st.date_input("Fecha", datetime.date.today(), key="f_tec")
        st.markdown("""<div style="display: flex; align-items: flex-end; margin-top: 30px;"><span style="font-weight: bold; margin-right: 15px;">Firma:</span><div class="linea-firma"></div></div>""", unsafe_allow_html=True)
        
    with c2:
        st.markdown("<div class='header-firma'>Supervisado / Revisado por</div>", unsafe_allow_html=True)
        st.text_input("Institución", value="Desarrollo Territorial" if not es_externo else "", key="e_sup")
        st.text_input("Nombre", value=sup_nombre_def, key="n_sup")
        st.date_input("Fecha", datetime.date.today(), key="f_sup")
        st.markdown("""<div style="display: flex; align-items: flex-end; margin-top: 30px;"><span style="font-weight: bold; margin-right: 15px;">Firma:</span><div class="linea-firma"></div></div>""", unsafe_allow_html=True)

st.divider()

# ==========================================
# ENVÍO DE DATOS A GOOGLE DRIVE Y PDF
# ==========================================
col_imprimir, col_drive = st.columns(2)

with col_imprimir:
    components.html(
        """
        <div style="text-align: center; margin-top: 10px;" id="btn-imprimir">
            <button onclick="window.parent.print()" style="padding: 14px 28px; font-size: 16px; font-weight: bold; background-color: #00B2A9; color: white; border: none; border-radius: 8px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
                🖨️ Imprimir / Guardar PDF Visual
            </button>
        </div>
        """, height=80
    )

with col_drive:
    if st.button("☁️ Respaldar Reporte COMPLETO en Drive", use_container_width=True):
        if estacion_sel == "Selecciona una opción...":
            st.error("⚠️ Falla: Selecciona la Estación de Monitoreo al inicio del formato.")
        else:
            with st.spinner("Empaquetando el 100% de los datos y subiendo a Google Drive..."):
                try:
                    SCOPES = ['https://www.googleapis.com/auth/drive.file']
                    creds_dict = json.loads(st.secrets["google_credentials"])
                    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
                    servicio_drive = build('drive', 'v3', credentials=creds)
                    
                    CARPETA_ID = 'PEGA_AQUI_EL_ID_DE_TU_CARPETA' 
                    
                    gas_n = gas_sel[:2] if es_gas else f"PM_{pm_tipo}"
                    fecha_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                    nombre_archivo = f"Reporte_{tipo_servicio[:3]}_{estacion_sel}_{gas_n}_{fecha_str}.xlsx"
                    
                    estado_completo = []
                    for key, value in st.session_state.items():
                        if not key.startswith('_'):
                            estado_completo.append({"Campo (ID)": key, "Valor Capturado": str(value)})
                    df_estado = pd.DataFrame(estado_completo)
                    
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                        df_estado.to_excel(writer, sheet_name="Datos_Capturados", index=False)
                        
                    excel_buffer.seek(0)
                    metadatos_archivo = {'name': nombre_archivo, 'parents': [CARPETA_ID]}
                    media = MediaIoBaseUpload(excel_buffer, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)
                    archivo_subido = servicio_drive.files().create(body=metadatos_archivo, media_body=media, fields='id').execute()
                    
                    st.success(f"✅ ¡Reporte guardado en Drive! (ID: {archivo_subido.get('id')})")
                    
                except Exception as e:
                    st.error(f"❌ Error de conexión con Google Drive: Revise sus credenciales y Secrets.")
