import streamlit as st
import datetime
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import io
import os
import xlsxwriter

st.set_page_config(layout="wide", page_title="Calibración SIMAJ")

# ==========================================
# CSS GLOBAL Y ESTILOS
# ==========================================
st.markdown("""
<style>
    h1, h2, h3 { color: #00B2A9 !important; font-weight: 800 !important; }
    h4 { color: #5C6670 !important; }
    hr { border-bottom: 3px solid #F37021 !important; margin: 1.5em 0 !important; }
    .stAlert { border-left: 5px solid #00B2A9 !important; background-color: #f0fdfa !important; }
    div[data-baseweb="select"] > div { border-color: #00B2A9 !important; }
    @media print {
        * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
        header, footer, .stDeployButton, [data-testid="stSidebar"] { display: none !important; }
        html, body, .stApp, div[data-testid="stAppViewContainer"], div[data-testid="stMain"] {
            height: auto !important; overflow: visible !important; position: static !important;
        }
        .main .block-container { max-width: 100% !important; padding: 0 !important; }
        div[data-testid="stVerticalBlock"] { page-break-inside: avoid; }
        details:not([open]) { display: none !important; }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# BASES DE DATOS DE EQUIPOS
# ==========================================
equipos_o3 = {
    "Pintas": "24-0305", "Santa Fe": "24-0307", "Miravalle": "24-0302", "Centro": "23-1564", 
    "Country": "23-2319", "Atemajac": "24-0385", "Oblatos": "24-0766", "Santa Margarita": "24-0387", 
    "Vallarta": "24-0388", "Loma Dorada": "24-0941", "Águilas": "24-0768", "Santa Anita": "24-0333", "Tlaquepaque": "24-0948"
}

equipos_nox = {
    "Pintas": "24-0179", "Santa Fe": "24-0579", "Miravalle": "24-0587", "Centro": "24-0595", 
    "Country": "23-2360", "Atemajac": "24-0705", "Oblatos": "24-0710", "Santa Margarita": "24-0570", 
    "Vallarta": "24-0592", "Loma Dorada": "24-0709", "Águilas": "24-0594", "Santa Anita": "24-0182", "Tlaquepaque": "24-0700"
}

equipos_co = {
    "Pintas": "24-1119", "Santa Fe": "24-1120", "Miravalle": "24-0169", "Centro": "24-0152", 
    "Country": "24-0151", "Atemajac": "24-0146", "Oblatos": "24-1121", "Santa Margarita": "24-0399", 
    "Loma Dorada": "24-1122", "Águilas": "ML9830 155", "Santa Anita": "24-0395"
}

equipos_so2 = {
    "Pintas": "17-1764", "Miravalle": "23-1538", "Centro": "17-1762", "Oblatos": "17-1765", "Tlaquepaque": "17-1763"
}

# ==========================================
# MENÚ LATERAL (SIDEBAR)
# ==========================================
st.sidebar.title("🛠️ Menú SIMAJ")
if os.path.exists("simaj.png"): st.sidebar.image("simaj.png")
gas_sel = st.sidebar.radio("Selecciona el Gas a Calibrar:", ["Ozono (O3)", "Óxidos de Nitrógeno (NOx)", "Monóxido de Carbono (CO)", "Dióxido de Azufre (SO2)"])

datos_resumen = {}

# Variables dinámicas de acuerdo al gas
if gas_sel == "Ozono (O3)":
    equipos_act = equipos_o3
    modelo_analizador = "Serinus 10"
    flujo_ideal_vol = 500
    flujo_tol = 0.025
    cero_tol = 0.003
    puntos_multipunto = [0.400, 0.300, 0.200, 0.100, 0.001]
    span_gen_default = 0.400
elif gas_sel == "Óxidos de Nitrógeno (NOx)":
    equipos_act = equipos_nox
    modelo_analizador = "Serinus 40"
    flujo_ideal_vol = 650
    flujo_tol = 0.05
    cero_tol = 0.003
    puntos_multipunto = [0.400, 0.300, 0.200, 0.100, 0.001]
    span_gen_default = 0.400
elif gas_sel == "Monóxido de Carbono (CO)":
    equipos_act = equipos_co
    modelo_analizador = "Serinus 30"
    flujo_ideal_vol = 1000
    flujo_tol = 0.025
    cero_tol = 0.5
    puntos_multipunto = [40.0, 30.0, 20.0, 10.0, 0.001]
    span_gen_default = 40.0
else: # SO2
    equipos_act = equipos_so2
    modelo_analizador = "Serinus 50"
    flujo_ideal_vol = 700
    flujo_tol = 0.025
    cero_tol = 0.003
    puntos_multipunto = [0.400, 0.300, 0.200, 0.100, 0.0001]
    span_gen_default = 0.400

st.title(f"FORMATO DE CALIBRACIÓN {gas_sel}")
st.subheader("Analizadores de Gases")

# ==========================================
# 1. DATOS DEL ANALIZADOR
# ==========================================
with st.expander("🛠️ DATOS DEL ANALIZADOR Y CONDICIONES AMBIENTALES", expanded=True):
    col_izq, col_der = st.columns([1, 1.2])
    with col_izq:
        estaciones = ["Selecciona una opción..."] + list(equipos_act.keys())
        estacion_sel = st.selectbox("Estación:", estaciones)
        
        fab_final = "ACOEM"
        mod_final = modelo_analizador
        
        if gas_sel == "Monóxido de Carbono (CO)" and estacion_sel == "Águilas":
            mod_final = "ML9830"
        elif gas_sel == "Dióxido de Azufre (SO2)" and estacion_sel in ["Pintas", "Centro", "Oblatos", "Tlaquepaque"]:
            fab_final = "ECOTECH"
            
        st.text_input("Fabricante", value=fab_final)
        st.text_input("Modelo", value=mod_final)
        
        num_serie_val = equipos_act.get(estacion_sel, "")
        st.text_input("N/S (Automático)", value=num_serie_val, disabled=True)
        st.selectbox("El analizador presenta Falla o Alarma", ["-", "No 🟢", "Sí 🔴"])

        datos_resumen["Estación"] = estacion_sel
        datos_resumen["Gas Calibrado"] = gas_sel
        datos_resumen["Número de Serie"] = num_serie_val

    with col_der:
        st.markdown("#### ")
        col_ini, col_fin = st.columns(2)
        with col_ini:
            st.markdown("### Inicial")
            fecha_ref = st.date_input("Fecha (Inicial)", datetime.date.today(), max_value=datetime.date.today())
            st.time_input("Hora (Inicial)", value=None)
            st.number_input("Temp exterior (C°) - Ini", value=0.0)
            st.number_input("Temp interior (C°) - Ini", value=0.0)
            st.number_input("Presión ambiental (Torr) - Ini", value=634.0)
            datos_resumen["Fecha de Servicio"] = str(fecha_ref)

        with col_fin:
            st.markdown("### Final")
            st.date_input("Fecha (Final)", datetime.date.today(), max_value=datetime.date.today())
            st.time_input("Hora (Final)", value=None)
            st.number_input("Temp exterior (C°) - Fin", value=0.0)
            st.number_input("Temp interior (C°) - Fin", value=0.0)
            st.number_input("Presión ambiental (Torr) - Fin", value=634.0)

# ==========================================
# 2. HISTÓRICO
# ==========================================
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
    req_multi = fila_historico("Calibración Multipunto", "multipunto", datetime.date(2026, 1, 1), 6)

abrir_basico = req_basico or req_comp
abrir_cs = req_cs or req_comp
abrir_multi = req_multi or req_comp
abrir_comp = req_comp

# ==========================================
# 3. FALLAS Y ALARMAS
# ==========================================
with st.expander("⚠️ DESCRIPCIÓN DE FALLA O ALARMA", expanded=abrir_basico):
    st.text_area("Detalle de la eventualidad", placeholder="Mencionar falla, alarma o cualquier anormalidad...", label_visibility="collapsed")

# ==========================================
# 4. PARÁMETROS GENERALES
# ==========================================
with st.expander("📊 REVISIÓN DE PARÁMETROS GENERALES", expanded=abrir_basico):
    h1, h2, h3, h4, h5, h6, h7 = st.columns([2, 1, 1, 1.5, 1.5, 1.5, 1.5])
    with h1: st.write("**Parámetro**")
    with h2: st.write("**Unidades**")
    with h3: st.write("**Ideal**")
    with h4: st.write("**Inicial**")
    with h5: st.write("**Comentarios**")
    with h6: st.write("**Final**")
    with h7: st.write("**Comentarios**")

    resultados_pg = []

    def evaluar_y_mostrar(val, min_val, max_val):
        if val is None: 
            st.write("")
        elif min_val <= val <= max_val: 
            st.success("Cumple ✅")
            resultados_pg.append(True)
        else: 
            st.error("NO CUMPLE ❌")
            resultados_pg.append(False)

    def fila_regla(param, unit, ideal_str, min_val, max_val, key):
        c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 1, 1, 1.5, 1.5, 1.5, 1.5])
        with c1: st.write(param)
        with c2: st.write(unit)
        with c3: st.write(ideal_str)
        with c4: val_ini = st.number_input("ini", key=f"ini_{key}", label_visibility="collapsed", value=None)
        with c5: evaluar_y_mostrar(val_ini, min_val, max_val)
        with c6: val_fin = st.number_input("fin", key=f"fin_{key}", label_visibility="collapsed", value=None)
        with c7: evaluar_y_mostrar(val_fin, min_val, max_val)
        return val_ini, val_fin 

    def fila_libre(param, unit, ideal_str, key):
        c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 1, 1, 1.5, 1.5, 1.5, 1.5])
        with c1: st.write(param)
        with c2: st.write(unit)
        with c3: st.write(ideal_str)
        with c4: val_ini = st.number_input("ini", key=f"ini_{key}", label_visibility="collapsed", value=None)
        with c5: st.text_input("c_ini", key=f"c_ini_{key}", label_visibility="collapsed")
        with c6: val_fin = st.number_input("fin", key=f"fin_{key}", label_visibility="collapsed", value=None)
        with c7: st.text_input("c_fin", key=f"c_fin_{key}", label_visibility="collapsed")
        return val_ini, val_fin

    if gas_sel == "Ozono (O3)":
        fila_libre("Flujo Estándar", "cc/min", "500", "o3_f_est")
        fila_regla("Flujo Volumétrico", "cc/min", "500", 487.5, 512.5, "o3_f_vol") 
        fila_regla("Presión de gas", "Torr", "629", 619.0, 630.0, "o3_p_gas")
        fila_regla("Voltaje de referencia", "Volts", "1.4 - 4", 1.4, 4.0, "o3_v_ref")
        fila_regla("Corriente de la lámpara", "mA", "9.5 - 10.5", 9.5, 10.5, "o3_c_lamp")
        fila_regla("Temperatura de la lámpara", "°C", "45 - 55", 45.0, 55.0, "o3_t_lamp")
        fila_regla("Pot de la lámpara UV", "N/A", "254", 254.0, 254.0, "o3_pot")
        fila_regla("Temperatura del Chassis", "°C", "0 - 50", 0.0, 50.0, "o3_t_chas")
        fila_regla("Temperatura del flujo", "°C", "10 - 90", 10.0, 90.0, "o3_t_flujo")
        fila_regla("INPUT (Pots)", "N/A", "50-200", 50.0, 200.0, "o3_in")
        fila_libre("Ganancia", "N/A", "N/A", "o3_gan")
        
    elif gas_sel == "Óxidos de Nitrógeno (NOx)":
        fila_libre("Flujo Estándar", "cc/min", "650", "nox_f_est")
        fila_regla("Flujo Volumétrico", "cc/min", "650", 617.5, 682.5, "nox_f_vol") 
        fila_regla("Presión de gas", "Torr", "80-300", 80.0, 300.0, "nox_p_gas")
        fila_regla("Temp. celda de reaccion", "°C", "50 ±10%", 45.0, 55.0, "nox_t_celda")
        fila_regla("Temp. del convertidor", "°C", "250-335", 250.0, 335.0, "nox_t_conv")
        fila_regla("Temperatura del Chassis", "°C", "0-50", 0.0, 50.0, "nox_t_chas")
        fila_regla("Temperatura de Manifold", "°C", "50", 45.0, 55.0, "nox_t_man")
        fila_regla("Temperatura de Cooler", "°C", "13 ±10%", 11.7, 14.3, "nox_t_cool")
        fila_regla("Alto voltaje", "Volt", "640-670", 640.0, 670.0, "nox_alto_v")
        fila_regla("Flujo de vacio", "torr", "50-200", 50.0, 200.0, "nox_f_vacio")
        fila_libre("Ganancia", "N/A", "N/A", "nox_gan")
        
    elif gas_sel == "Monóxido de Carbono (CO)":
        fila_libre("Flujo Estándar", "cc/min", "1000", "co_f_est")
        fila_regla("Flujo Volumétrico", "cc/min", "1000", 975.0, 1025.0, "co_f_vol")
        fila_libre("Presión de celda", "Torr", "631.7", "co_p_celda") 
        fila_regla("IR Source", "Volt", "5 ± 0.5", 4.5, 5.5, "co_ir")
        fila_regla("Temp. de Scrubber", "°C", "90 ± 10", 80.0, 100.0, "co_t_scrub")
        fila_regla("Voltaje de referencia", "Volt", "3.6 - 4.4", 3.6, 4.4, "co_v_ref")
        fila_regla("Voltaje de concentración", "Volt", "0 - 3.1", 0.0, 3.1, "co_v_conc")
        fila_regla("Temp. celda de reaccion", "°C", "50", 45.0, 55.0, "co_t_celda")
        fila_regla("Temperatura del Chassis", "°C", "0-50", 0.0, 50.0, "co_t_chas")
        fila_regla("Temperatura de flujo", "°C", "50", 45.0, 55.0, "co_t_flujo")
        fila_regla("Temperatura del espejo", "°C", "50 ± 10", 40.0, 60.0, "co_t_esp")
        fila_regla("INPUT (Pots)", "N/A", "180-230", 180.0, 230.0, "co_in")
        fila_libre("Ganancia", "N/A", "N/A", "co_gan")
        
    else: # SO2
        fila_libre("Flujo", "cc/min", "700", "so2_f_vol")
        fila_libre("Presión de gas", "Torr", "-", "so2_p_gas")
        fila_regla("Voltaje de referencia", "Volts", "1.5 - 3.5", 1.5, 3.5, "so2_v_ref")
        fila_regla("Corriente de la lámpara", "mA", "34 - 36", 34.0, 36.0, "so2_c_lamp")
        fila_regla("Alto voltaje", "Volts", "690 - 715", 690.0, 715.0, "so2_alto_v")
        fila_regla("Temperatura del Chassis", "°C", "0 - 50", 0.0, 50.0, "so2_t_chas")
        fila_regla("Temperatura de celda", "°C", "47-53", 47.0, 53.0, "so2_t_celda")
        fila_regla("Temperatura del Cooler", "°C", "11.7-14.3", 11.7, 14.3, "so2_t_cool")
        fila_regla("Temperatura del bloque", "°C", "50", 45.0, 55.0, "so2_t_bloq")
        fila_libre("Valor de la ganancia", "-", "-", "so2_gan")
        fila_regla("Valor de ajuste POT lámpara", "-", "10-100", 10.0, 100.0, "so2_pot")

    # Dictamen de Parámetros Generales
    if len(resultados_pg) > 0:
        datos_resumen["Parámetros Generales"] = "Cumple" if all(resultados_pg) else "NO CUMPLE"
    else:
        datos_resumen["Parámetros Generales"] = "Sin datos"

# ==========================================
# 5. VERIFICACIÓN Y AJUSTE DE FLUJO
# ==========================================
with st.expander("💨 VERIFICACIÓN Y AJUSTE DE FLUJO", expanded=abrir_basico):
    col_cal1, col_cal2 = st.columns(2)
    with col_cal1:
        st.markdown("**Calibrador**")
        st.text_input("Fabricante", value="Bios International Corp", key="fab_cal1")
        st.text_input("Modelo", value="Definer 220 M", key="mod_cal1")
        st.text_input("N/S", value="129115", key="ns_cal1")

    with col_cal2:
        st.markdown("**Certificación**")
        st.text_input("Laboratorio", value="COMEXSA", key="lab_cal1")
        st.text_input("Técnico", value="Lizeth Morales", key="tec_cal1")
        st.date_input("Vigente hasta", datetime.date(2026, 6, 20), key="vig_cal1")
        st.text_input("No de certificado", value="E13496529 Flujo", key="cert_cal1")

    st.markdown("**Parámetro medido por calibrador**")
    col_p1, col_p2 = st.columns(2)
    with col_p1: st.number_input("Presión Ambiental medida (Torr)", value=None, key="p_amb_calib")
    with col_p2: st.number_input("Temperatura interna (°C)", value=None, key="t_int_calib")

    def eval_flujo(val, ideal, tolerancia):
        if val is None: return "", "", ""
        desv = (val - ideal) / ideal
        cond = "Cumple" if -tolerancia <= desv <= tolerancia else "NO CUMPLE"
        return f"{desv * 100:.2f}%", cond, ("No" if cond == "Cumple" else "SÍ")

    def render_tabla_flujo(titulo, key_prefix):
        st.markdown(f"#### {titulo}")
        c1, c2, c3, c4, c5, c6 = st.columns([2, 1, 1.5, 1.5, 1.5, 1.5])
        with c1: st.write("**Parámetro**")
        with c2: st.write("**Ideal**")
        with c3: st.write("**Captura**")
        with c4: st.write("**% desv**")
        with c5: st.write("**Condición**")
        with c6: st.write("**Ajuste**")

        c1, c2, c3, c4, c5, c6 = st.columns([2, 1, 1.5, 1.5, 1.5, 1.5])
        with c1: st.write("Flujo Estandar (cc/min)")
        with c2: st.write("-")
        with c3: st.number_input("val_est", key=f"{key_prefix}_est", label_visibility="collapsed")
        with c4: st.write("-")
        with c5: st.write("-")
        with c6: st.write("-")

        c1, c2, c3, c4, c5, c6 = st.columns([2, 1, 1.5, 1.5, 1.5, 1.5])
        with c1: st.write("Flujo Volumétrico (cc/min)")
        with c2: st.write(str(flujo_ideal_vol))
        with c3: val = st.number_input("val_vol", key=f"{key_prefix}_vol", label_visibility="collapsed")
        desv_str, cond, req = eval_flujo(val, flujo_ideal_vol, flujo_tol)
        with c4: st.write(desv_str)
        with c5:
            if cond == "Cumple": st.success(cond)
            elif cond == "NO CUMPLE": st.error(cond)
        with c6: st.write(req)
        return val

    flujo_vol_verif = render_tabla_flujo("Verificación", "verif")
    flujo_vol_ajus = render_tabla_flujo("Ajuste", "ajus")

    # Dictamen de Flujo
    if flujo_vol_ajus is not None:
        d_a = (flujo_vol_ajus - flujo_ideal_vol) / flujo_ideal_vol
        datos_resumen["Ajuste de Flujo"] = "Cumple" if (-flujo_tol <= d_a <= flujo_tol) else "NO CUMPLE"
    elif flujo_vol_verif is not None:
        d_v = (flujo_vol_verif - flujo_ideal_vol) / flujo_ideal_vol
        datos_resumen["Ajuste de Flujo"] = "Cumple" if (-flujo_tol <= d_v <= flujo_tol) else "NO CUMPLE"
    else:
        datos_resumen["Ajuste de Flujo"] = "Sin datos"

# ==========================================
# 6. REVISIÓN BÁSICA DE COMPONENTES
# ==========================================
with st.expander("🔍 REVISIÓN BÁSICA DE COMPONENTES", expanded=abrir_basico):
    c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 3])
    with c1: st.write("**Componente**")
    with c2: st.write("**Estado**")
    with c3: st.write("**Limpieza**")
    with c4: st.write("**Reemplazo**")
    with c5: st.write("**Observaciones**")

    def fila_comp(nombre, key, placeholder="Especificar detalles..."):
        c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 3])
        with c1: st.write(nombre)
        with c2: st.selectbox("Estado", ["-", "Bueno 🟢", "Malo 🔴"], key=f"est_{key}", label_visibility="collapsed")
        with c3: st.selectbox("Limpieza", ["-", "Sí 🟢", "No 🔴"], key=f"limp_{key}", label_visibility="collapsed")
        with c4: st.selectbox("Reemplazo", ["-", "Sí 🟢", "No 🔴"], key=f"reemp_{key}", label_visibility="collapsed")
        with c5: st.text_input("Obs", placeholder=placeholder, key=f"obs_{key}", label_visibility="collapsed")

    if gas_sel == "Ozono (O3)":
        fila_comp("Lámpara UV (revisión electrónica)", "b_lamp")
        fila_comp("Mangueras", "b_mang")
        fila_comp("Válvulas de calibración", "b_valv")
        fila_comp("Filtro externo de 47 mm", "b_fil")
        fila_comp("Display", "b_disp")
        fila_comp("Manifold", "b_man")
    elif gas_sel == "Óxidos de Nitrógeno (NOx)":
        fila_comp("Tubería", "b_tub")
        fila_comp("Mangueras", "b_mang_nox")
        fila_comp("Generador de Ozono", "b_gen")
        fila_comp("Display", "b_disp_nox")
        fila_comp("Permapure", "b_perm")
    elif gas_sel == "Monóxido de Carbono (CO)":
        fila_comp("Tubería", "b_tub_co")
        fila_comp("Mangueras", "b_mang_co")
        fila_comp("Válvulas de calibración", "b_valv_co")
        fila_comp("Filtro externo de 47 mm", "b_fil_co")
        fila_comp("Display", "b_disp_co")
        fila_comp("Manifold", "b_man_co")
    else: # SO2
        fila_comp("Tubería", "b_tub_so2")
        fila_comp("Mangueras", "b_mang_so2")
        fila_comp("Kicker", "b_kicker")
        fila_comp("Lámpara UV", "b_lamp_so2")
        fila_comp("Display", "b_disp_so2")

# ==========================================
# 7. DATOS DEL CALIBRADOR (INFERIOR)
# ==========================================
with st.expander("📑 DATOS DE CALIBRACIÓN Y CALIBRADOR", expanded=(abrir_cs or abrir_multi)):
    idx_calib = 1 if (abrir_cs or abrir_multi) else 0
    st.selectbox("Calibración req", ["No requerido", "Requerido"], index=idx_calib, key="calib_req", label_visibility="collapsed")
    col_cal3, col_cal4 = st.columns(2)
    with col_cal3:
        st.text_input("Fabricante", value="Acoem", key="fab_calib2")
        st.text_input("Modelo", value="Serinus Cal 3000", key="mod_calib2")
        st.selectbox("N/S", ["23-1998", "24-1135", "Otro..."], key="ns_calib2")
    with col_cal4:
        st.text_input("Laboratorio", value="INECC", key="lab_calib2")
        st.text_input("Técnico", value="Humberto Bustamante", key="tec_calib2")
        st.date_input("Vigente hasta", datetime.date(2026, 8, 8), key="vig_calib2")

# ==========================================
# 8. VERIFICACIÓN CERO-SPAN
# ==========================================
with st.expander("⚖️ VERIFICACIÓN CERO-SPAN", expanded=abrir_cs):
    idx_cs = 1 if abrir_cs else 0
    st.selectbox("Req Cero-Span", ["No requerido", "Requerido"], index=idx_cs, key="req_cero_span", label_visibility="collapsed")

    col_cs_izq, col_cs_der = st.columns(2)
    with col_cs_izq:
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: st.write("")
        with c2: st.write("**Inicial**")
        with c3: st.write("**Final**")
        
        if gas_sel in ["Ozono (O3)", "Monóxido de Carbono (CO)", "Dióxido de Azufre (SO2)"]:
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1: st.write("Ganancia")
            with c2: st.number_input("ini", key="cs_g_i", label_visibility="collapsed")
            with c3: st.number_input("fin", key="cs_g_f", label_visibility="collapsed")
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1: st.write("Zero Offset (ppb/ppm)")
            with c2: st.number_input("ini", key="cs_z_i", label_visibility="collapsed")
            with c3: st.number_input("fin", key="cs_z_f", label_visibility="collapsed")
        else: # NOx
            for param, kp in [("Ganancia NO", "cs_gn_"), ("Ganancia Aux (NOx)", "cs_gax_"), ("Zero Offset NO", "cs_zno_"), ("Zero Offset NO2", "cs_zno2_")]:
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1: st.write(param)
                with c2: st.number_input("ini", key=f"{kp}i", label_visibility="collapsed")
                with c3: st.number_input("fin", key=f"{kp}f", label_visibility="collapsed")

    with col_cs_der:
        st.markdown("**Tiempo de respuesta al suministrar gas**")
        for gas, kp in [("Cero", "tr_c"), ("Span", "tr_s")]:
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1: st.write(gas)
            with c2: st.number_input("val", key=kp, label_visibility="collapsed")
            with c3: st.write("min")

    col_cs_cero, col_cs_span = st.columns(2)
    dif_c_ok = span_s_ok = False
    dif_c = desv_s = None
    
    with col_cs_cero:
        st.markdown("#### Concentración Cero")
        c1, c2, c3 = st.columns(3)
        with c1: st.write("**Cero**")
        with c2: st.write("**Analizador**")
        with c3: st.write("**Dif**")
        c1, c2, c3 = st.columns(3)
        cero_gen_default = 0.0001 if gas_sel == "Dióxido de Azufre (SO2)" else 0.001
        with c1: val_cg = st.number_input("Cero Gen", value=cero_gen_default, disabled=True, key="vcg")
        with c2: resp_c = st.number_input("Resp Cero", value=0.000, format="%.4f", key="rac")
        with c3:
            if resp_c is not None:
                dif_c = resp_c - val_cg
                st.write(f"**{dif_c:.4f}**")
            else: st.write("")
        c1, c2, c3 = st.columns(3)
        with c1: st.write("")
        with c2: st.write("**Cond**")
        with c3:
            if dif_c is not None:
                dif_c_ok = -cero_tol <= dif_c <= cero_tol
                if dif_c_ok: st.success("Cumple ✅")
                else: st.error("NO CUMPLE ❌")

    with col_cs_span:
        st.markdown("#### Concentración Span")
        c1, c2, c3 = st.columns(3)
        with c1: st.write("**Span**")
        with c2: st.write("**Analizador**")
        with c3: st.write("**% desv**")
        c1, c2, c3 = st.columns(3)
        with c1: val_sg = st.number_input("Span Gen", value=span_gen_default, disabled=True, key="vsg")
        with c2: resp_s = st.number_input("Resp Span", value=0.000, format="%.4f", key="ras")
        with c3:
            if resp_s is not None and val_sg != 0:
                desv_s = (resp_s - val_sg) / val_sg
                st.write(f"**{desv_s * 100:.2f}%**")
            else: st.write("")
        c1, c2, c3 = st.columns(3)
        with c1: st.write("")
        with c2: st.write("**Cond**")
        with c3:
            if desv_s is not None:
                span_s_ok = -0.025 <= desv_s <= 0.025
                if span_s_ok: st.success("Cumple ✅")
                else: st.error("NO CUMPLE ❌")

    # Dictamen Cero y Span
    if dif_c is not None and desv_s is not None:
        datos_resumen["Cero y Span"] = "Cumple" if (dif_c_ok and span_s_ok) else "NO CUMPLE"
    else:
        datos_resumen["Cero y Span"] = "Sin datos"

    st.write("")
    st.selectbox("¿Se realizó verificación de Scrubber?", ["-", "Sí 🟢", "No 🔴"], key="cs_vs")

# ==========================================
# 9. CALIBRACIÓN MULTIPUNTO
# ==========================================
with st.expander("📈 CALIBRACIÓN MULTIPUNTO", expanded=abrir_multi):
    idx_multi = 1 if abrir_multi else 0
    st.selectbox("Req Multipunto", ["No requerido", "Requerido"], index=idx_multi, key="req_multi", label_visibility="collapsed")

    col_pts, col_res = st.columns([1.5, 1])
    with col_pts:
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.write("**Calibrador**")
        with c2: st.write("**Analizador**")
        with c3: st.write("**Diferencia**")
        with c4: st.write("**% desv**")

        x_vals, y_vals, desviaciones = [], [], []

        for i, cal_val in enumerate(puntos_multipunto):
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.number_input("cal", value=cal_val, disabled=True, key=f"mc_{i}", label_visibility="collapsed")
            with c2: ana_val = st.number_input("ana", value=None, key=f"ma_{i}", format="%.4f", label_visibility="collapsed")
            with c3:
                if ana_val is not None:
                    dif = ana_val - cal_val
                    st.write(f"**{dif:.4f}**")
                else: st.write("")
            with c4:
                if ana_val is not None and cal_val != 0:
                    desv = (dif / cal_val)
                    desviaciones.append(desv)
                    st.write(f"**{desv * 100:.2f}%**")
                else: st.write("")

            if ana_val is not None:
                x_vals.append(cal_val)
                y_vals.append(ana_val)

        st.write("")
        c1, c2, c3, c4 = st.columns(4)
        with c3: st.markdown("#### Promedio")
        with c4:
            if desviaciones:
                promedio = sum(desviaciones) / len(desviaciones)
                if abs(promedio) > 0.025: st.markdown(f"**:red[{promedio * 100:.2f}%]**")
                else: st.write(f"**{promedio * 100:.2f}%**")
            else: promedio = None; st.write("")

    m, b, r2 = None, None, None
    if len(x_vals) > 1:
        try:
            x_arr, y_arr = np.array(x_vals), np.array(y_vals)
            m, b = np.polyfit(x_arr, y_arr, 1)
            r2 = (np.corrcoef(x_arr, y_arr)[0,1])**2
        except: pass

    cond_m = cond_b = cond_r2 = cond_prom = False

    with col_res:
        st.markdown("**Ecuación y Condición**")
        r1, r2_col, r3 = st.columns([1, 1, 1.2])
        with r1:
            st.write("**m =**"); st.write("**b =**"); st.write("**R2 =**")
        with r2_col:
            st.write(f"{m:.8f}" if m is not None else "-")
            st.write(f"{b:.8f}" if b is not None else "-")
            st.write(f"{r2:.8f}" if r2 is not None else "-")
        with r3:
            if m is not None:
                cond_m = 0.98 <= m <= 1.02
                cond_b = -2.0 <= b <= 2.0
                cond_r2 = 0.99 <= r2 <= 1.0
                if cond_m: st.success("Cumple")
                else: st.error("NO CUMPLE")
                if cond_b: st.success("Cumple")
                else: st.error("NO CUMPLE")
                if cond_r2: st.success("Cumple")
                else: st.error("NO CUMPLE")
            else: st.write("") 
            
        st.markdown("**Condición Promedio**")
        if promedio is not None:
            cond_prom = -0.025 <= promedio <= 0.025
            if cond_prom: st.success("Cumple ✅")
            else: st.error("NO CUMPLE ❌")

    st.write("---")
    # Dictamen Multipunto
    if len(x_vals) > 0:
        cond_puntos = len(x_vals) == 5
        if cond_m and cond_b and cond_r2 and cond_prom and cond_puntos:
            st.success("✅ **CALIBRACIÓN MULTIPUNTO APROBADA**")
            datos_resumen["Calibración Multipunto"] = "Cumple"
        else:
            st.error("❌ **CALIBRACIÓN MULTIPUNTO RECHAZADA**")
            datos_resumen["Calibración Multipunto"] = "NO CUMPLE"
    else:
        datos_resumen["Calibración Multipunto"] = "Sin datos"

    col_graf, col_texto = st.columns([1.5, 1])
    with col_graf:
        if len(x_vals) > 1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='markers+text', name='Analizador',
                                     text=[f"{v:.4f}" for v in y_vals], textposition="top left", marker=dict(size=10, color='#00B2A9')))
            x_line = np.linspace(0, max(x_vals)*1.1, 100)
            y_line = m * x_line + b if m is not None else x_line
            fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', name='Tendencia', line=dict(color='#5C6670', dash='dash')))
            fig.update_layout(title="Regresión Lineal", height=400)
            st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 10. REVISIÓN DETALLADA
# ==========================================
with st.expander("🔍 REVISIÓN DETALLADA DE COMPONENTES", expanded=abrir_comp):
    st.selectbox("Req Detalle", ["No requerido", "Requerido"], index=(1 if abrir_comp else 0), key="req_det", label_visibility="collapsed")
    c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 3])
    with c1: st.write("**Componente**")
    with c2: st.write("**Estado**")
    with c3: st.write("**Limpieza**")
    with c4: st.write("**Reemplazo**")
    with c5: st.write("**Observaciones**")

    if gas_sel in ["Ozono (O3)", "Monóxido de Carbono (CO)"]:
        fila_comp("Bomba de Vacío externa", "d_bomba")
        fila_comp("Tubería", "d_tub")
        fila_comp("Filtro interno de 47 mm", "d_fil_i")
        fila_comp("Bomba de Vacío Interna", "d_bomba_i")
        fila_comp("O-rings de celda de reacción", "d_orings")
        fila_comp("Filtros sinterizados", "d_fsint")
        fila_comp("Orificios críticos", "d_orit")
        fila_comp("Ventilador de fuente", "d_vent")
        fila_comp("Tubo de celda de reacción", "d_tubo")
        fila_comp("Filtro óptico", "d_fopt")
        fila_comp("Tarjetas electrónicas", "d_tarj")
        fila_comp("Fuente de voltaje", "d_fvolt")
    else: # NOx y SO2
        fila_comp("Bomba de Vacío externa", "d_bomba_gn")
        fila_comp("Generador de Ozono", "d_gen_gn")
        fila_comp("Permapure", "d_perm_gn")

# ==========================================
# 11. RESUMEN Y EXPORTACIÓN A EXCEL
# ==========================================
with st.expander("✍️ RESUMEN Y FIRMAS FINALES", expanded=True):
    # Formato fiel a la solicitud (títulos exactos y visibles)
    obs_gen = st.text_area("Observaciones Generales", placeholder="Mencionar anomalías...", label_visibility="visible", key="res_obs")
    conclusiones = st.text_area("Conclusiones", placeholder="Mencionar si cumplen criterio...", label_visibility="visible", key="res_conc")

    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        emp_tec = st.text_input("Empresa/Institución", value="Secretaría de Medio Ambiente y Desarrollo Territorial", key="e_tec")
        nom_tec = st.text_input("Técnico", value="José Alfredo Jiménez Ramos", key="n_tec")
    with c2:
        emp_sup = st.text_input("Empresa/Institución ", value="Secretaría de Medio Ambiente y Desarrollo Territorial", key="e_sup") # Espacio extra para no duplicar ID
        nom_sup = st.text_input("Supervisor", value="Beatriz Rodríguez Pérez", key="n_sup")

st.divider()

# BOTONES FINALES
c_print, c_excel = st.columns(2)
with c_print:
    st.markdown("<p style='text-align: center; color: gray;'>Presiona <b>Ctrl + P</b> para guardar el PDF nativo.</p>", unsafe_allow_html=True)

with c_excel:
    try:
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        worksheet = workbook.add_worksheet('Reporte Ejecutivo')
        
        # DEFINICIÓN DE FORMATOS (Estilo SIMAJ)
        f_titulo = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#00B2A9', 'align': 'center', 'valign': 'vcenter'})
        f_seccion = workbook.add_format({'bold': True, 'bg_color': '#F37021', 'font_color': 'white', 'border': 1, 'align': 'center'})
        f_etiqueta = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'valign': 'vcenter'})
        f_valor = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        f_texto_largo = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'top', 'text_wrap': True})
        f_bien = workbook.add_format({'border': 1, 'bg_color': '#d4edda', 'font_color': '#155724', 'bold': True, 'align': 'center', 'valign': 'vcenter'})
        f_mal = workbook.add_format({'border': 1, 'bg_color': '#f8d7da', 'font_color': '#721c24', 'bold': True, 'align': 'center', 'valign': 'vcenter'})
        
        # CONFIGURACIÓN DE PÁGINA Y COLUMNAS
        worksheet.set_column('B:B', 35)
        worksheet.set_column('C:C', 45)
        
        # LOGO Y TÍTULO
        if os.path.exists("simaj.png"):
            worksheet.insert_image('B2', 'simaj.png', {'x_scale': 0.4, 'y_scale': 0.4, 'x_offset': 10, 'y_offset': 5})
        
        worksheet.merge_range('B2:C4', f"REPORTE EJECUTIVO DE CALIBRACIÓN\n{gas_sel}", f_titulo)
        worksheet.set_row(1, 30)
        
        # 1. DATOS GENERALES
        fila = 6
        worksheet.merge_range(f'B{fila}:C{fila}', "📋 DATOS GENERALES DEL EQUIPO", f_seccion)
        fila += 1
        worksheet.write(f'B{fila}', "Estación", f_etiqueta); worksheet.write(f'C{fila}', estacion_sel, f_valor); fila += 1
        worksheet.write(f'B{fila}', "Gas Calibrado", f_etiqueta); worksheet.write(f'C{fila}', gas_sel, f_valor); fila += 1
        worksheet.write(f'B{fila}', "Número de Serie", f_etiqueta); worksheet.write(f'C{fila}', num_serie_val, f_valor); fila += 1
        worksheet.write(f'B{fila}', "Fecha de Servicio", f_etiqueta); worksheet.write(f'C{fila}', str(fecha_ref), f_valor); fila += 2
        
        # 2. DICTÁMENES TÉCNICOS
        worksheet.merge_range(f'B{fila}:C{fila}', "✅ DICTÁMENES TÉCNICOS AUTOMÁTICOS", f_seccion)
        fila += 1
        
        dictamenes = [
            ("Parámetros Generales", datos_resumen["Parámetros Generales"]),
            ("Ajuste de Flujo", datos_resumen["Ajuste de Flujo"]),
            ("Cero y Span", datos_resumen["Cero y Span"]),
            ("Calibración Multipunto", datos_resumen["Calibración Multipunto"])
        ]
        
        for nombre, resultado in dictamenes:
            worksheet.write(f'B{fila}', nombre, f_etiqueta)
            if resultado == "Cumple": worksheet.write(f'C{fila}', "Cumple", f_bien)
            elif resultado == "NO CUMPLE": worksheet.write(f'C{fila}', "NO CUMPLE", f_mal)
            else: worksheet.write(f'C{fila}', resultado, f_valor)
            fila += 1
            
        fila += 1
        
        # 3. OBSERVACIONES Y FIRMAS
        worksheet.merge_range(f'B{fila}:C{fila}', "📝 OBSERVACIONES Y FIRMAS", f_seccion)
        fila += 1
        worksheet.write(f'B{fila}', "Observaciones Generales", f_etiqueta)
        worksheet.write(f'C{fila}', obs_gen, f_texto_largo); worksheet.set_row(fila-1, 40); fila += 1
        worksheet.write(f'B{fila}', "Conclusiones", f_etiqueta)
        worksheet.write(f'C{fila}', conclusiones, f_texto_largo); worksheet.set_row(fila-1, 40); fila += 1
        
        # Firmas Técnico
        worksheet.write(f'B{fila}', "Empresa / Institución (Técnico)", f_etiqueta)
        worksheet.write(f'C{fila}', emp_tec, f_valor); fila += 1
        worksheet.write(f'B{fila}', "Técnico", f_etiqueta)
        worksheet.write(f'C{fila}', nom_tec, f_valor); fila += 1
        worksheet.write(f'B{fila}', "Firma Técnico", f_etiqueta)
        worksheet.write(f'C{fila}', "", f_valor); worksheet.set_row(fila-1, 60); fila += 1 # Altura para firma
        
        # Firmas Supervisor
        worksheet.write(f'B{fila}', "Empresa / Institución (Supervisor)", f_etiqueta)
        worksheet.write(f'C{fila}', emp_sup, f_valor); fila += 1
        worksheet.write(f'B{fila}', "Supervisor", f_etiqueta)
        worksheet.write(f'C{fila}', nom_sup, f_valor); fila += 1
        worksheet.write(f'B{fila}', "Firma Supervisor", f_etiqueta)
        worksheet.write(f'C{fila}', "", f_valor); worksheet.set_row(fila-1, 60); fila += 1 # Altura para firma

        workbook.close()
        
        st.download_button(
            label="📥 Descargar Reporte Ejecutivo en Excel",
            data=buffer.getvalue(),
            file_name=f"Reporte_{gas_sel[:3]}_{estacion_sel}_{fecha_ref}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        st.error(f"Error generando Excel: {e}")
