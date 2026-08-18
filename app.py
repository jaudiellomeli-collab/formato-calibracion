import streamlit as st
import datetime
import numpy as np
import plotly.graph_objects as go
import os

st.set_page_config(layout="wide", page_title="Calibración O3 SIMAJ")

# ==========================================
# INYECCIÓN DE CSS (TEMA SIMAJ + IMPRESIÓN NATIVA)
# ==========================================
estilos_personalizados = """
<style>
    /* COLORES SIMAJ */
    h1, h2, h3 { color: #00B2A9 !important; font-weight: 800 !important; }
    h4 { color: #5C6670 !important; }
    hr { border-bottom: 3px solid #F37021 !important; margin: 1.5em 0 !important; }
    .stAlert { border-left: 5px solid #00B2A9 !important; background-color: #f0fdfa !important; }
    div[data-baseweb="select"] > div { border-color: #00B2A9 !important; }
    
    /* REGLAS MAESTRAS PARA EL PDF NATIVO (Ctrl + P) */
    @media print {
        * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
        header, footer, .stDeployButton { display: none !important; }
        html, body, .stApp, div[data-testid="stAppViewContainer"], div[data-testid="stMain"] {
            height: auto !important;
            overflow: visible !important;
            position: static !important;
        }
        .main .block-container { max-width: 100% !important; padding: 0 !important; }
        div[data-testid="stVerticalBlock"] { page-break-inside: avoid; }
        
        /* Ocultar elementos cerrados del expander para que no estorben en la impresión */
        details:not([open]) { display: none !important; }
    }
</style>
"""
st.markdown(estilos_personalizados, unsafe_allow_html=True)

# Base de datos de equipos O3 SIMAJ
equipos_o3 = {
    "Pintas": "24-0305", "Santa Fe": "24-0307", "Miravalle": "24-0302",
    "Centro": "23-1564", "Country": "23-2319", "Atemajac": "24-0385",
    "Oblatos": "24-0766", "Santa Margarita": "24-0387", "Vallarta": "24-0388",
    "Loma Dorada": "24-0941", "Águilas": "24-0768", "Santa Anita": "24-0333",
    "Tlaquepaque": "24-0948"
}

# ==========================================
# LOGO Y ENCABEZADO FIJO
# ==========================================
if os.path.exists("simaj.png"):
    st.image("simaj.png", width=300)
else:
    st.info("📌 Sube la imagen 'simaj.png' a GitHub para ver el logo oficial.")

st.title("FORMATO")
st.subheader("Parámetros Generales de O3 - Analizadores de Gases")

col_vacia, col_folio, col_codigo, col_version = st.columns([1, 1, 1, 1])
with col_folio: st.text_input("Folio")
with col_codigo: st.text_input("Código", value="S08-4-G1-PG", disabled=True)
with col_version: st.text_input("Fecha de versión", value="30/09/2025", disabled=True)

# ==========================================
# 1. DATOS DEL ANALIZADOR
# ==========================================
with st.expander("🛠️ DATOS DEL ANALIZADOR Y CONDICIONES AMBIENTALES", expanded=True):
    col_izq, col_der = st.columns([1, 1.2])

    with col_izq:
        estaciones = ["Selecciona una opción..."] + list(equipos_o3.keys())
        estacion_sel = st.selectbox("Estación:", estaciones)
        st.markdown("#### Analizador")
        st.text_input("Fabricante", value="ACOEM")
        st.text_input("Modelo", value="Serinus 10")
        
        # Asignación automática de N/S
        num_serie_val = equipos_o3.get(estacion_sel, "")
        st.text_input("N/S (Automático)", value=num_serie_val, disabled=True)
        
        st.selectbox("El analizador presenta Falla o Alarma", ["-", "No 🟢", "Sí 🔴"])

    with col_der:
        st.markdown("#### ")
        col_ini, col_fin = st.columns(2)
        with col_ini:
            st.markdown("### Inicial")
            fecha_ref = st.date_input("Fecha (Inicial)", datetime.date.today(), max_value=datetime.date.today())
            st.time_input("Hora (Inicial)", value=None)
            st.number_input("Temperatura exterior (C°) - Ini", value=0.0)
            st.number_input("Temperatura interior (C°) - Ini", value=0.0)
            st.number_input("Presión ambiental (Torr) - Ini", value=634.0)

        with col_fin:
            st.markdown("### Final")
            st.date_input("Fecha (Final)", datetime.date.today(), max_value=datetime.date.today())
            st.time_input("Hora (Final)", value=None)
            st.number_input("Temperatura exterior (C°) - Fin", value=0.0)
            st.number_input("Temperatura interior (C°) - Fin", value=0.0)
            st.number_input("Presión ambiental (Torr) - Fin", value=634.0)

# ==========================================
# 2. HISTÓRICO (MOTOR DE LA LÓGICA DE APERTURA)
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
            es_requerido = (fecha_ref - fecha_ult).days > (periodicidad_meses * 30)
            if es_requerido: 
                st.error("Requerido")
            else: 
                st.success("No Requerido")
            return es_requerido

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
    st.text_area("Detalle de la eventualidad", placeholder="Mencionar falla, alarma o cualquier anormalidad detectada. Vincular con evento de bitácora...", label_visibility="collapsed")

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

    def evaluar_y_mostrar(val, min_val, max_val):
        if val is None: st.write("")
        elif min_val <= val <= max_val: st.success("Cumple ✅")
        else: st.error("NO CUMPLE ❌")

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

    val_ini_est, val_fin_est = fila_libre("Flujo Estándar", "cc/min", "500", "flujo_est")
    val_ini_vol, val_fin_vol = fila_regla("Flujo Volumétrico", "cc/min", "500", 487.5, 512.5, "flujo_vol") 
    fila_regla("Presión de gas", "Torr", "629", 619.0, 630.0, "pres_gas")
    fila_regla("Voltaje de referencia", "Volts", "1.4 - 4", 1.4, 4.0, "volt_ref")
    fila_regla("Corriente de la lámpara", "mA", "9.5 - 10.5", 9.5, 10.5, "corr_lamp")
    fila_regla("Temperatura de la lámpara", "°C", "45 - 55", 45.0, 55.0, "temp_lamp")
    fila_regla("Pot de la lámpara UV", "N/A", "254", 254.0, 254.0, "pot_uv")
    fila_regla("Temperatura del Chassis", "°C", "0 - 50", 0.0, 50.0, "temp_chas")
    fila_regla("Temperatura del flujo", "°C", "10 - 90", 10.0, 90.0, "temp_flujo")
    fila_regla("INPUT (Pots)", "N/A", "50-200", 50.0, 200.0, "in_pots")
    fila_libre("Ganancia", "N/A", "N/A", "ganancia")

# ==========================================
# 5. VERIFICACIÓN Y AJUSTE DE FLUJO
# ==========================================
with st.expander("💨 VERIFICACIÓN Y AJUSTE DE FLUJO", expanded=abrir_basico):
    col_cal1, col_cal2 = st.columns(2)
    with col_cal1:
        st.markdown("**Calibrador**")
        st.text_input("Fabricante", value="Bios International Corp", key="fab_calib1")
        st.text_input("Modelo", value="Definer 220 M", key="mod_calib1")
        st.text_input("N/S", value="129115", key="ns_calib1")

    with col_cal2:
        st.markdown("**Certificación**")
        st.text_input("Laboratorio", value="COMEXSA", key="lab_calib1")
        st.text_input("Técnico", value="Lizeth Morales", key="tec_calib1")
        fecha_vigencia = st.date_input("Vigente hasta", datetime.date(2026, 6, 20), max_value=datetime.date(2030, 1, 1), key="vig_calib1")
        st.text_input("No de certificado", value="E13496529 Flujo", key="cert_calib1")

    estado_valido = "Valido" if fecha_vigencia > fecha_ref else "NO VALIDO"
    with col_cal1:
        if estado_valido == "Valido": st.success(f"Estado: {estado_valido}")
        else: st.error(f"Estado: {estado_valido}")

    st.markdown("**Parámetro medido por calibrador**")
    col_p1, col_p2 = st.columns(2)
    with col_p1: st.number_input("Presión Ambiental medida (Torr)", value=None, key="p_amb_calib")
    with col_p2: st.number_input("Temperatura interna (°C)", value=None, key="t_int_calib")

    # Regla estricta 2.5%
    def eval_25(val, ideal):
        if val is None: return "", "", ""
        desv = (val - ideal) / ideal
        cond = "Cumple" if -0.025 <= desv <= 0.025 else "NO CUMPLE"
        return f"{desv * 100:.2f}%", cond, ("No" if cond == "Cumple" else "SI")

    def render_tabla_flujo(titulo, val_est, val_vol, key_prefix):
        st.markdown(f"#### {titulo}")
        h1, h2, h3, h4, h5, h6 = st.columns([2, 1, 1.5, 1.5, 1.5, 1.5])
        with h1: st.write("**Parámetro**")
        with h2: st.write("**Ideal**")
        with h3: st.write("**Captura**")
        with h4: st.write("**% desv**")
        with h5: st.write("**Condición**")
        with h6: st.write("**Ajuste**")

        # Flujo Estándar SIN evaluación ni validación
        c1, c2, c3, c4, c5, c6 = st.columns([2, 1, 1.5, 1.5, 1.5, 1.5])
        with c1: st.write("Flujo Estandar (cc/min)")
        with c2: st.write("-")
        with c3: st.number_input("val_est", value=val_est, key=f"{key_prefix}_est", label_visibility="collapsed")
        with c4: st.write("-")
        with c5: st.write("-")
        with c6: st.write("-")

        # Flujo Volumétrico CON evaluación 2.5%
        c1, c2, c3, c4, c5, c6 = st.columns([2, 1, 1.5, 1.5, 1.5, 1.5])
        with c1: st.write("Flujo Volumétrico (cc/min)")
        with c2: st.write("500")
        with c3: val = st.number_input("val_vol", value=val_vol, key=f"{key_prefix}_vol", label_visibility="collapsed")
        desv_str, cond, req = eval_25(val, 500)
        with c4: st.write(desv_str)
        with c5:
            if cond == "Cumple": st.success(cond)
            elif cond == "NO CUMPLE": st.error(cond)
        with c6: st.write(req)
        
        return val

    # VERIFICACIÓN INICIAL
    flujo_vol_verif = render_tabla_flujo("Verificación", val_ini_est, val_ini_vol, "verif")
    
    # Evaluar requisito de ajuste Inmediatamente después de la verificación
    req_ajuste_final = ""
    if flujo_vol_verif is not None:
        d_v = (flujo_vol_verif - 500) / 500
        req_ajuste_final = "No" if (-0.025 <= d_v <= 0.025) else "SÍ"
        
    st.markdown(f"#### ¿Requiere ajuste volumétrico?: **{req_ajuste_final}**")
    st.caption("*La condición se cumple cuando la desviación es menor o igual a ±2.5%")

    # AJUSTE FINAL
    flujo_vol_ajus = render_tabla_flujo("Ajuste", val_fin_est, val_fin_vol, "ajus")

    st.markdown("#### RESUMEN VERIFICACIÓN | AJUSTE")
    col_v1, col_v2 = st.columns(2)
    cond_resumen_v = ""
    with col_v1:
        st.info("**VERIFICACIÓN**")
        sv1, sv2, sv3, sv4 = st.columns(4)
        with sv1: st.write("**INICIAL**"); st.write(str(flujo_vol_verif) if flujo_vol_verif is not None else "")
        with sv2: st.write("**IDEAL**"); st.write("500")
        with sv3:
            st.write("**% desv**")
            if flujo_vol_verif is not None:
                d_v = (flujo_vol_verif - 500) / 500
                st.write(f"{d_v * 100:.2f}%")
        with sv4:
            st.write("**Condición***")
            if flujo_vol_verif is not None:
                cond_resumen_v = "Cumple" if -0.025 <= d_v <= 0.025 else "NO CUMPLE"
                if cond_resumen_v == "Cumple": st.success(cond_resumen_v)
                else: st.error(cond_resumen_v)

    with col_v2:
        st.info("**AJUSTE**")
        sa1, sa2, sa3 = st.columns(3)
        with sa1: st.write("**FINAL**"); st.write(str(flujo_vol_ajus) if flujo_vol_ajus is not None else "")
        with sa2:
            st.write("**% desv**")
            if flujo_vol_ajus is not None:
                d_a = (flujo_vol_ajus - 500) / 500
                st.write(f"{d_a * 100:.2f}%")
        with sa3:
            st.write("**Condición***")
            if flujo_vol_ajus is not None:
                cond_resumen_a = "Cumple" if -0.025 <= d_a <= 0.025 else "NO CUMPLE"
                if cond_resumen_a == "Cumple": st.success(cond_resumen_a)
                else: st.error(cond_resumen_a)

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

    def fila_componente_basica(nombre, key):
        c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 3])
        with c1: st.write(nombre)
        with c2: st.selectbox("Estado", ["-", "Bueno 🟢", "Malo 🔴"], key=f"est_{key}", label_visibility="collapsed")
        with c3: st.selectbox("Limpieza", ["-", "Sí 🟢", "No 🔴"], key=f"limp_{key}", label_visibility="collapsed")
        with c4: st.selectbox("Reemplazo", ["-", "Sí 🟢", "No 🔴"], key=f"reemp_{key}", label_visibility="collapsed")
        with c5: st.text_input("Obs", placeholder="Especificar detalles o justificación...", key=f"obs_{key}", label_visibility="collapsed")

    fila_componente_basica("Lámpara UV (revisión electrónica)", "lamp_uv_rev")
    fila_componente_basica("Mangueras", "mangueras")
    fila_componente_basica("Válvulas de calibración", "valvulas")
    fila_componente_basica("Filtro externo de 47 mm", "filtro")
    fila_componente_basica("Display", "display")
    fila_componente_basica("Manifold", "manifold")

# ==========================================
# 7. DATOS DEL CALIBRADOR (INFERIOR)
# ==========================================
with st.expander("📑 DATOS DE CALIBRACIÓN Y CALIBRADOR", expanded=(abrir_cs or abrir_multi)):
    idx_calib = 1 if (abrir_cs or abrir_multi) else 0
    st.selectbox("Calibración req", ["No requerido", "Requerido"], index=idx_calib, key="calib_req", label_visibility="collapsed")
    
    col_cal3, col_cal4 = st.columns(2)
    with col_cal3:
        st.markdown("**Calibrador**")
        st.text_input("Fabricante", value="Acoem", key="fab_calib2")
        st.text_input("Modelo", value="Serinus Cal 3000", key="mod_calib2")
        st.selectbox("N/S", ["24-1135", "Otro..."], key="ns_calib2")
    with col_cal4:
        st.markdown("**Certificación**")
        st.text_input("Laboratorio", value="INECC", key="lab_calib2")
        st.text_input("Técnico", value="Humberto Bustamante", key="tec_calib2")
        fecha_vigencia_2 = st.date_input("Vigente hasta", datetime.date(2026, 8, 5), max_value=datetime.date(2030, 1, 1), key="vig_calib2")
        st.text_input("No de certificado", value="3547-1-1 / 3547-1-2", key="cert_calib2")

    estado_valido_2 = "Valido" if fecha_vigencia_2 > fecha_ref else "NO VALIDO"
    with col_cal3:
        if estado_valido_2 == "Valido": st.success(f"Estado: {estado_valido_2}")
        else: st.error(f"Estado: {estado_valido_2}")

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
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: st.write("**Ganancia**")
        with c2: st.number_input("Ganancia Ini", key="cs_gan_ini", label_visibility="collapsed", value=None)
        with c3: st.number_input("Ganancia Fin", key="cs_gan_fin", label_visibility="collapsed", value=None)
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: st.write("**Zero Offset (ppb)**")
        with c2: st.number_input("Zero Ini", key="cs_zero_ini", label_visibility="collapsed", value=None)
        with c3: st.number_input("Zero Fin", key="cs_zero_fin", label_visibility="collapsed", value=None)

    with col_cs_der:
        st.markdown("**Tiempo de respuesta al suministrar gas**")
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1: st.write("Cero")
        with c2: st.number_input("T. Resp Cero", key="cs_t_resp_cero", label_visibility="collapsed", value=None)
        with c3: st.write("min")
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1: st.write("Span")
        with c2: st.number_input("T. Resp Span", key="cs_t_resp_span", label_visibility="collapsed", value=None)
        with c3: st.write("min")

    col_cs_cero, col_cs_span = st.columns(2)
    with col_cs_cero:
        st.markdown("#### Concentración Cero")
        c1, c2, c3 = st.columns(3)
        with c1: st.write("**Valor Cero**")
        with c2: st.write("**Analizador**")
        with c3: st.write("**Diferencia**")
        c1, c2, c3 = st.columns(3)
        with c1: val_cero_gen = st.number_input("Val Cero Gen", value=0.001, disabled=True, key="cs_vcg")
        with c2: resp_cero = st.number_input("Resp Cero", value=0.000, format="%.3f", key="cs_rac")
        with c3:
            if resp_cero is not None:
                dif_cero = resp_cero - val_cero_gen
                st.write(f"**{dif_cero:.3f}**")
            else: dif_cero = None; st.write("")
        c1, c2, c3 = st.columns(3)
        with c1: st.write("")
        with c2: st.write("**Condición**")
        with c3:
            if dif_cero is not None:
                if -0.003 <= dif_cero <= 0.003: st.success("Cumple ✅")
                else: st.error("NO CUMPLE ❌")

    with col_cs_span:
        st.markdown("#### Concentración Span")
        c1, c2, c3 = st.columns(3)
        with c1: st.write("**Valor Span**")
        with c2: st.write("**Analizador**")
        with c3: st.write("**% desv**")
        c1, c2, c3 = st.columns(3)
        with c1: val_span_gen = st.number_input("Val Span Gen", value=0.400, disabled=True, key="cs_vsg")
        with c2: resp_span = st.number_input("Resp Span", value=0.000, format="%.3f", key="cs_ras")
        with c3:
            if resp_span is not None and val_span_gen != 0:
                desv_span = (resp_span - val_span_gen) / val_span_gen
                st.write(f"**{desv_span * 100:.0f}%**")
            else: desv_span = None; st.write("")
        c1, c2, c3 = st.columns(3)
        with c1: st.write("")
        with c2: st.write("**Condición**")
        with c3:
            if desv_span is not None:
                if -0.025 <= desv_span <= 0.025: st.success("Cumple ✅")
                else: st.error("NO CUMPLE ❌")

    st.write("")
    col_scrub1, col_scrub2 = st.columns([1, 2])
    with col_scrub1: st.selectbox("¿Se realizó verificación de Scrubber?", ["Selecciona...", "Sí 🟢", "No 🔴"], key="cs_verif_scrubber")
    with col_scrub2: st.text_input("Observaciones", placeholder="Especificar detalles o justificación...", key="cs_obs_scrubber")

# ==========================================
# 9. CALIBRACIÓN MULTIPUNTO
# ==========================================
with st.expander("📈 CALIBRACIÓN MULTIPUNTO", expanded=abrir_multi):
    idx_multi = 1 if abrir_multi else 0
    st.selectbox("Req Multipunto", ["No requerido", "Requerido"], index=idx_multi, key="req_multi", label_visibility="collapsed")

    col_pts, col_res = st.columns([1.5, 1])
    with col_pts:
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.write("**Calibrador (ppm)**")
        with c2: st.write("**Analizador (ppm)**")
        with c3: st.write("**Diferencia**")
        with c4: st.write("**% desv**")

        puntos_cal = [0.400, 0.300, 0.200, 0.100, 0.040]
        x_vals, y_vals, desviaciones = [], [], []

        for i, cal_val in enumerate(puntos_cal):
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.number_input("cal", value=cal_val, disabled=True, key=f"multi_cal_{i}", label_visibility="collapsed")
            with c2: ana_val = st.number_input("ana", value=None, key=f"multi_ana_{i}", format="%.3f", label_visibility="collapsed")
            with c3:
                if ana_val is not None:
                    dif = ana_val - cal_val
                    st.write(f"**{dif:.3f}**")
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
                # Aplicamos color rojo si el promedio es mayor al 2.5% (0.025)
                if abs(promedio) > 0.025:
                    st.markdown(f"**:red[{promedio * 100:.2f}%]**")
                else:
                    st.write(f"**{promedio * 100:.2f}%**")
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
            st.write("**m =**"); st.write("**b =**"); st.write("**R2 =**"); st.write("**Eq =**")
        with r2_col:
            st.write(f"{m:.8f}" if m is not None else "-")
            st.write(f"{b:.8f}" if b is not None else "-")
            st.write(f"{r2:.8f}" if r2 is not None else "-")
            st.write(f"{m:.4f}x + {b:.4f}" if m is not None else "-")
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
            else:
                st.write("") 
            
        st.markdown("**Condición Promedio**")
        if promedio is not None:
            cond_prom = -0.025 <= promedio <= 0.025
            if cond_prom: st.success("Cumple ✅")
            else: st.error("NO CUMPLE ❌")

    # VALIDACIÓN GLOBAL DE MULTIPUNTO
    st.write("---")
    if len(x_vals) > 0:
        cond_puntos = len(x_vals) == 5
        if cond_m and cond_b and cond_r2 and cond_prom and cond_puntos:
            st.success("✅ **CALIBRACIÓN MULTIPUNTO APROBADA:** Cumple todas las condiciones establecidas y cuenta con los 5 puntos medidos.")
        else:
            st.error("❌ **CALIBRACIÓN MULTIPUNTO RECHAZADA:** No cumple alguna condición (m, b, R2, desviación promedio) o faltan puntos por capturar.")

    col_graf, col_texto = st.columns([1.5, 1])
    with col_graf:
        if len(x_vals) > 1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='markers+text', name='Analizador (ppm)',
                                     text=[f"{v:.3f}" for v in y_vals], textposition="top left", marker=dict(size=10, color='#00B2A9')))
            x_line = np.linspace(0, max(x_vals)*1.1, 100)
            y_line = m * x_line + b if m is not None else x_line
            fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', name='Tendencia', line=dict(color='#5C6670', dash='dash')))
            fig.update_layout(title="Regresión Lineal", xaxis_title="Calibrador (ppm)", yaxis_title="Analizador (ppm)", height=400)
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("💡 Ingresa al menos 2 valores arriba para graficar.")

        st.markdown("**Subir gráfica de concentraciones (Opcional)**")
        img_graf = st.file_uploader("Sube la imagen generada aquí", type=["png", "jpg", "jpeg"], key="up_graf_multi")
        if img_graf is not None: st.image(img_graf, caption="Gráfica", use_container_width=True)

    with col_texto:
        st.info('''**Análisis de resultados**
        $y = mx + b$
        $y$ = instrumento (ppm) | $x$ = calibrador (ppm) | $m$ = ganancia | $b$ = offset
        **Aceptada si:**
        * $m$ entre 0.98 y 1.02
        * $b$ entre -2 a +2
        * $R^2$ mayor que 0.99.
        * El promedio de desviación estándar no excede el ±2.5%.
        ''')

# ==========================================
# 10. REVISIÓN DETALLADA DE COMPONENTES
# ==========================================
with st.expander("🔍 REVISIÓN DETALLADA DE COMPONENTES", expanded=abrir_comp):
    idx_comp = 1 if abrir_comp else 0
    st.selectbox("Req Detalle", ["No requerido", "Requerido"], index=idx_comp, key="req_detalle", label_visibility="collapsed")

    c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 3])
    with c1: st.write("**Componente**")
    with c2: st.write("**Estado**")
    with c3: st.write("**Limpieza**")
    with c4: st.write("**Reemplazo**")
    with c5: st.write("**Observaciones**")

    def fila_componente_detallada(nombre, key, placeholder="Especificar detalles o justificación..."):
        c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 3])
        with c1: st.write(nombre)
        with c2: st.selectbox("Estado", ["-", "Bueno 🟢", "Malo 🔴"], key=f"est_{key}", label_visibility="collapsed")
        with c3: st.selectbox("Limpieza", ["-", "Sí 🟢", "No 🔴"], key=f"limp_{key}", label_visibility="collapsed")
        with c4: st.selectbox("Reemplazo", ["-", "Sí 🟢", "No 🔴"], key=f"reemp_{key}", label_visibility="collapsed")
        with c5: st.text_input("Obs", placeholder=placeholder, key=f"obs_{key}", label_visibility="collapsed")

    fila_componente_detallada("Bomba de Vacío externa", "det_bomba_ext", "Registrar presión")
    fila_componente_detallada("Tubería", "det_tub")
    fila_componente_detallada("Filtro interno de 47 mm", "det_filtro_int")
    fila_componente_detallada("Bomba de Vacío Interna", "det_bomba_int")
    fila_componente_detallada("O-rings de celda de reacción", "det_orings")
    fila_componente_detallada("Filtros sinterizados", "det_filtros_sint")
    fila_componente_detallada("Orificios críticos", "det_orificios")
    fila_componente_detallada("Ventilador de fuente", "det_ventilador")
    fila_componente_detallada("Tubo de celda de reacción", "det_tubo_celda")
    fila_componente_detallada("Filtro óptico", "det_filtro_opt")
    fila_componente_detallada("Tarjetas electrónicas", "det_tarjetas")
    fila_componente_detallada("Fuente de voltaje", "det_fuente")

# ==========================================
# 11. RESUMEN Y FIRMAS
# ==========================================
with st.expander("✍️ RESUMEN Y FIRMAS FINALES", expanded=True):
    st.markdown("**Observaciones Generales**")
    st.text_area("Obs Gen", placeholder="Mencionar cualquier anormalidad detectada...", label_visibility="collapsed", key="res_obs_gen")
    st.markdown("**Conclusiones**")
    st.text_area("Conclusiones", placeholder="Mencionar si cumplen criterio de ±2.5%...", label_visibility="collapsed", key="res_conclusiones")

    st.write("")
    col_firma1, col_firma2 = st.columns(2)
    with col_firma1:
        st.markdown("#### Técnico / Operador")
        st.text_input("Empresa/Institución", value="Secretaría de Medio Ambiente y Desarrollo Territorial", key="empresa_tec")
        st.text_input("Nombre", value="José Alfredo Jiménez Ramos", key="nombre_tec")
        st.date_input("Fecha", datetime.date.today(), max_value=datetime.date.today(), key="fecha_tec")
        st.text_area("Firma", placeholder="(Espacio para firma)", height=100, key="firma_tec")

    with col_firma2:
        st.markdown("#### Supervisado / Revisado por")
        st.text_input("Empresa/Institución", value="Secretaría de Medio Ambiente y Desarrollo Territorial", key="empresa_sup")
        st.text_input("Nombre", value="Beatriz Rodríguez Pérez", key="nombre_sup")
        st.date_input("Fecha", datetime.date.today(), max_value=datetime.date.today(), key="fecha_sup")
        st.text_area("Firma", placeholder="(Espacio para firma)", height=100, key="firma_sup")

    st.markdown("<p style='text-align: center; font-size: 14px; color: gray;'>La evidencia fotográfica se entregará en un anexo.</p>", unsafe_allow_html=True)
