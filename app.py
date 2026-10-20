import streamlit as st
import datetime
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import io
import os
import base64
import json
import re
from PIL import Image, ImageOps
import streamlit.components.v1 as components
from email.message import EmailMessage
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from pdf_formato import construir_pdf, Caja, Alerta, Neg

st.set_page_config(layout="wide", page_title="Calibración SIMAJ")

# ==========================================
# CSS GLOBAL: CAPTURA EN PANTALLA E IMPRESIÓN DEL NAVEGADOR
# (el PDF descargable se genera aparte en pdf_formato.py; estas reglas solo afectan la página)
# ==========================================
st.markdown("""
<style>
    /* ---------- Pantalla (captura) ---------- */
    h1, h2, h3 { color: #00B2A9 !important; font-weight: 800 !important; }
    h4 { color: #5C6670 !important; margin-bottom: 2px !important; }
    hr { border-bottom: 3px solid #F37021 !important; margin: 1.5em 0 !important; }
    .stAlert { border-left: 5px solid #00B2A9 !important; background-color: #f0fdfa !important; }
    div[data-baseweb="select"] > div { border-color: #00B2A9 !important; }
    textarea { line-height: 1.35 !important; }

    .header-firma { background-color: #A6A6A6; color: black; font-weight: bold; text-align: center; padding: 5px; border: 1px solid #7a7a7a; margin-bottom: 10px; font-size: 16px; }
    .linea-firma { margin-top: 40px; border-bottom: 1px solid black; width: 100%; height: 25px; }
    .header-tabla { background-color: #e0e0e0; font-weight: bold; text-align: center; padding: 4px; border: 1px solid #ccc; margin-top: 10px; margin-bottom: 5px; }
    .resumen-servicio { display: none; }

    /* Fotografías: tarjetas del mismo tamaño en tres columnas */
    [class*="st-key-galeria_"] img { aspect-ratio: 1 / 1; object-fit: contain; background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; }

    /* ---------- Impresión del navegador ---------- */
    @media print {
        @page { size: letter portrait; margin: 1cm 0.8cm; }
        * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
        header, footer, .stDeployButton, [data-testid="stSidebar"], #btn-imprimir, [data-testid="stFileUploaderDropzone"] { display: none !important; }
        /* Los selectores del encabezado se sustituyen por un resumen legible; los demás radios sí se imprimen */
        [class*="st-key-selector_"] { display: none !important; }
        .resumen-servicio { display: block !important; font-size: 12px; padding: 4px 6px; border-left: 4px solid #00B2A9; background: #f0fdfa; margin: 4px 0; }
        html, body { font-size: 11px !important; line-height: 1.3 !important; color: black !important; }
        p, label, li, span, input, textarea { font-size: 11px !important; }
        h1 { font-size: 16px !important; margin: 8px 0 4px 0 !important; padding: 0 !important; }
        h2, h3 { font-size: 13px !important; margin: 6px 0 3px 0 !important; padding: 0 !important; }
        h4 { font-size: 11.5px !important; margin: 6px 0 3px 0 !important; padding: 0 !important; font-weight: bold !important; }
        html, body, .stApp, div[data-testid="stAppViewContainer"], div[data-testid="stMain"] { height: auto !important; overflow: visible !important; position: static !important; }
        .main .block-container, [data-testid="stMainBlockContainer"] { max-width: 100% !important; padding: 0 10px !important; }
        [data-testid="stVerticalBlock"] { gap: 0.45rem !important; }
        div[data-testid="stHorizontalBlock"] { gap: 0.5rem !important; align-items: flex-start !important; break-inside: avoid; page-break-inside: avoid; }
        /* Campos: altura mínima legible y crecimiento según el contenido (nada se recorta) */
        input[type="text"], input[type="number"] { padding: 3px 6px !important; min-height: 26px !important; height: auto !important; }
        textarea { padding: 3px 6px !important; min-height: 26px !important; height: auto !important; field-sizing: content; overflow: visible !important; white-space: pre-wrap !important; }
        div[data-baseweb="textarea"], div[data-baseweb="input"], div[data-baseweb="base-input"] { height: auto !important; min-height: 26px !important; overflow: visible !important; }
        input, textarea, div[data-baseweb="select"] > div { border: 1px solid #a0a0a0 !important; }
        div[data-baseweb="select"] > div { min-height: 26px !important; height: auto !important; }
        .stSelectbox svg, .stExpander > details > summary > svg { display: none !important; }
        .stExpander { border: 1px solid #ddd !important; border-radius: 4px !important; margin-bottom: 8px !important; }
        .stExpander summary { padding: 4px 6px !important; min-height: 0 !important; background-color: #f7f7f7 !important; break-after: avoid; page-break-after: avoid; }
        details:not([open]) { display: none !important; }
        hr { margin: 6px 0 !important; border-color: #ddd !important; }
        .stAlert { padding: 3px 8px !important; border-width: 1px !important; margin-bottom: 2px !important; }
        .header-firma { font-size: 12px !important; padding: 3px !important; }
        [class*="st-key-galeria_"] [data-testid="stColumn"] { break-inside: avoid; page-break-inside: avoid; }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CÓDIGO DE GOOGLE Y SECRETOS
# ==========================================
SCOPES_GOOGLE = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/gmail.send"]
SECRETS_REQUERIDOS = ["google_oauth", "drive_carpeta_id", "correo_coordinador"]

def credenciales_google():
    cfg = st.secrets["google_oauth"]
    return Credentials(None, refresh_token=cfg["refresh_token"], token_uri="https://oauth2.googleapis.com/token",
                       client_id=cfg["client_id"], client_secret=cfg["client_secret"], scopes=SCOPES_GOOGLE)

def secrets_faltantes():
    try:
        return [s for s in SECRETS_REQUERIDOS if s not in st.secrets]
    except Exception:  # no existe ningún archivo de secrets (por ejemplo, al correr en local)
        return SECRETS_REQUERIDOS

def error_google(e):
    """Mensaje de error breve: tipo, código HTTP y motivo, sin la URL de la petición ni datos de las credenciales."""
    estado = getattr(getattr(e, "resp", None), "status", None)
    motivo = getattr(e, "reason", None) or (e.args[0] if e.args and isinstance(e.args[0], str) else "")
    return type(e).__name__ + (f" (HTTP {estado})" if estado else "") + (f": {str(motivo)[:200]}" if motivo else "")

# ==========================================
# BORRADORES: SERIALIZACIÓN Y LIMPIEZA DEL FORMULARIO
# ==========================================
CLAVES_SELECTOR = ["k_tipo", "k_gas", "k_pm", "k_est"]
CLAVES_SIN_BORRADOR = set(CLAVES_SELECTOR + ["correo_borrador", "FormSubmitter"])
PREFIJOS_SIN_BORRADOR = ("_", "up_", "desc_fot_")  # las fotos y sus descripciones no se guardan en el borrador
VERSION_BORRADOR = 2
# Opciones de versiones anteriores del formato que cambiaron de texto
MIGRAR_OPCIONES = {"Sí 🟢": "Sí", "No 🔴": "No", "Bueno 🟢": "Bueno", "Malo 🔴": "Malo"}

def _a_json(v):
    if isinstance(v, datetime.date): return {"__fecha__": v.isoformat()}
    if isinstance(v, datetime.time): return {"__hora__": v.strftime("%H:%M:%S")}
    return v

def _de_json(k, v, legado):
    if isinstance(v, dict):
        if "__fecha__" in v: return datetime.date.fromisoformat(v["__fecha__"])
        if "__hora__" in v: return datetime.time.fromisoformat(v["__hora__"])
        return None
    if isinstance(v, str):
        if k.startswith(("est_", "limp_", "reemp_")): return MIGRAR_OPCIONES.get(v, v)
        if legado:  # los borradores anteriores guardaban fechas y horas como texto
            if re.match(r'^\d{4}-\d{2}-\d{2}$', v):
                try: return datetime.datetime.strptime(v, '%Y-%m-%d').date()
                except ValueError: pass
            elif re.match(r'^\d{2}:\d{2}(:\d{2})?$', v):
                try: return datetime.time.fromisoformat(v)
                except ValueError: pass
    return v

def datos_para_borrador():
    datos = {}
    for k, v in st.session_state.items():
        if k in CLAVES_SIN_BORRADOR or k.startswith(PREFIJOS_SIN_BORRADOR): continue
        if isinstance(v, (str, int, float, bool, type(None), datetime.date, datetime.time)): datos[k] = _a_json(v)
    return {"__version__": VERSION_BORRADOR, "datos": datos}

def restaurar_borrador(vista):
    legado = vista.get("__version__") != VERSION_BORRADOR
    datos = vista if legado else vista.get("datos", {})
    for k, v in datos.items():
        if k in CLAVES_SIN_BORRADOR or k.startswith(PREFIJOS_SIN_BORRADOR): continue
        st.session_state[k] = _de_json(k, v, legado)

def limpiar_formulario():
    """Al cambiar tipo de servicio, equipo o parámetro se inicia un formulario nuevo para no mezclar datos de otro formato."""
    conservar = set(CLAVES_SELECTOR + ["correo_borrador", "k_quien"])
    for k in list(st.session_state.keys()):
        if k not in conservar and not k.startswith("_"):
            del st.session_state[k]

def buscar_borrador(servicio, carpeta, nombre):
    nombre_q = nombre.replace("\\", "\\\\").replace("'", "\\'")
    res = servicio.files().list(q=f"name='{nombre_q}' and '{carpeta}' in parents and trashed=false", fields="files(id)").execute()
    archivos = res.get('files', [])
    if not archivos: return None, {}
    archivo_id = archivos[0]['id']
    contenido = servicio.files().get_media(fileId=archivo_id).execute()
    return archivo_id, json.loads(contenido.decode('utf-8'))

# ==========================================
# PANEL LATERAL: GUARDAR/CARGAR PROGRESO (CROSS-DEVICE)
# ==========================================
st.sidebar.markdown("### 💾 Progreso en la Nube")
st.sidebar.caption("¿Empezaste en el celular? Ingresa tu correo, guarda tu avance, y cárgalo en tu computadora para continuar.\n**(Nota: Las fotos y sus descripciones no se guardan en el borrador, súbelas al final en la computadora).**")
correo_borrador = st.sidebar.text_input("Tu Correo Electrónico:", key="correo_borrador", placeholder="tecnico@jalisco.gob.mx")

v_tipo = st.session_state.get('k_tipo', 'Selecciona una opción...')
v_est = st.session_state.get('k_est', 'Selecciona una opción...')
v_gas = st.session_state.get('k_gas', 'Ozono (O3)')
v_pm = st.session_state.get('k_pm', 'N/A')
vista_actual = f"{v_tipo}_{v_est}_{v_gas}_{v_pm}"

col_btn1, col_btn2 = st.sidebar.columns(2)
if col_btn1.button("📥 Guardar", use_container_width=True):
    if not correo_borrador:
        st.sidebar.error("Ingresa un correo.")
    elif v_est == "Selecciona una opción...":
        st.sidebar.error("Selecciona una Estación en la ventana principal primero.")
    elif secrets_faltantes():
        st.sidebar.error("Faltan credenciales de Google en Secrets.")
    else:
        try:
            with st.spinner("Guardando vista actual..."):
                servicio = build("drive", "v3", credentials=credenciales_google())
                carpeta = st.secrets["drive_carpeta_id"]
                nombre_borrador = f"borrador_{correo_borrador.strip()}.json"
                archivo_id, dict_global = buscar_borrador(servicio, carpeta, nombre_borrador)
                dict_global[vista_actual] = datos_para_borrador()
                media = MediaIoBaseUpload(io.BytesIO(json.dumps(dict_global).encode('utf-8')), mimetype='application/json', resumable=True)
                if archivo_id:
                    servicio.files().update(fileId=archivo_id, media_body=media).execute()
                else:
                    servicio.files().create(body={'name': nombre_borrador, 'parents': [carpeta]}, media_body=media).execute()
            st.sidebar.success(f"✅ Guardado: {v_gas} en {v_est}.")
        except Exception as e:
            st.sidebar.error(f"Error al guardar: {error_google(e)}")

if col_btn2.button("📤 Cargar", use_container_width=True):
    if not correo_borrador:
        st.sidebar.error("Ingresa un correo.")
    elif v_est == "Selecciona una opción...":
        st.sidebar.error("Selecciona la Estación y Equipo a cargar en la ventana principal.")
    elif secrets_faltantes():
        st.sidebar.error("Faltan credenciales de Google en Secrets.")
    else:
        dict_global = None
        try:
            with st.spinner("Cargando..."):
                servicio = build("drive", "v3", credentials=credenciales_google())
                archivo_id, dict_global = buscar_borrador(servicio, st.secrets["drive_carpeta_id"], f"borrador_{correo_borrador.strip()}.json")
        except Exception as e:
            st.sidebar.error(f"Error al cargar: {error_google(e)}")
        if dict_global is not None:
            if not archivo_id:
                st.sidebar.warning("No se encontró ningún borrador para este correo.")
            elif vista_actual in dict_global:
                restaurar_borrador(dict_global[vista_actual])
                st.rerun()
            else:
                st.sidebar.warning(f"No hay datos guardados para {v_gas} en {v_est}.")

# ==========================================
# BASES DE DATOS DE EQUIPOS Y SERIES
# ==========================================
equipos_o3 = {"Pintas": "24-0305", "Santa Fe": "24-0307", "Miravalle": "24-0302", "Centro": "23-1564", "Country": "23-2319", "Atemajac": "24-0385", "Oblatos": "24-0766", "Santa Margarita": "24-0387", "Vallarta": "24-0388", "Loma Dorada": "24-0941", "Águilas": "24-0768", "Santa Anita": "24-0333", "Tlaquepaque": "24-0948"}
equipos_nox = {"Pintas": "24-0179", "Santa Fe": "24-0579", "Miravalle": "24-0587", "Centro": "24-0595", "Country": "23-2360", "Atemajac": "24-0705", "Oblatos": "24-0710", "Santa Margarita": "24-0570", "Vallarta": "24-0592", "Loma Dorada": "24-0709", "Águilas": "24-0594", "Santa Anita": "24-0182", "Tlaquepaque": "24-0700"}
equipos_co = {"Pintas": "24-1119", "Santa Fe": "24-1120", "Miravalle": "24-0169", "Centro": "24-0152", "Country": "24-0151", "Atemajac": "24-0146", "Oblatos": "24-1121", "Santa Margarita": "24-0399", "Loma Dorada": "24-1122", "Águilas": "ML9830 155", "Santa Anita": "24-0395"}
equipos_so2 = {"Pintas": "17-1764", "Miravalle": "23-1538", "Centro": "17-1762", "Oblatos": "17-1765", "Tlaquepaque": "17-1763"}
equipos_pm10 = {"Pintas": "CM17461024", "Santa Fe": "DN16867", "Miravalle": "DN16862", "Centro": "DN17077", "Country": "G3448", "Atemajac": "", "Oblatos": "", "Santa Margarita": "EN12458", "Vallarta": "5014i203241211", "Loma Dorada": "5014i203171211", "Águilas": "EN12457", "Santa Anita": "EN12289", "Tlaquepaque": "CM18091003"}
equipos_pm25 = {"Pintas": "5014i203251211", "Santa Fe": "DN17069", "Miravalle": "DN17070", "Centro": "DN16864", "Country": "N14028", "Atemajac": "", "Oblatos": "", "Santa Margarita": "", "Vallarta": "5014i203131210", "Loma Dorada": "", "Águilas": "EN12462", "Santa Anita": "EN12291", "Tlaquepaque": ""}

# ==========================================
# MENÚ SUPERIOR HORIZONTAL Y LOGO
# ==========================================
st.write("<br>", unsafe_allow_html=True)
# Los selectores van en contenedores con clave para ocultarlos al imprimir y mostrar en su lugar un resumen legible
with st.container(key="selector_servicio"):
    st.markdown("#### Selecciona el Tipo de Servicio:")
    tipo_servicio = st.radio("Selecciona el Tipo de Servicio:", ["Selecciona una opción...", "SIMAJ", "Mantenimiento Externo"], horizontal=True,
                             key="k_tipo", label_visibility="collapsed", on_change=limpiar_formulario)
    es_externo = (tipo_servicio == "Mantenimiento Externo")

    if tipo_servicio == "Selecciona una opción...":
        st.warning("⚠️ Selecciona el tipo de mantenimiento para habilitar el formato.")
        st.stop()

    # Quién realiza el mantenimiento externo (obligatorio); se agrega al nombre del archivo y al asunto del correo
    if es_externo:
        quien_externo = st.radio("¿Quién realiza el mantenimiento?", ["Selecciona una opción...", "Proveedor", "SIMAJ"], horizontal=True, key="k_quien")
        if quien_externo == "Selecciona una opción...":
            st.warning("⚠️ Selecciona si el mantenimiento lo realiza un Proveedor o SIMAJ para habilitar el formato.")
            st.stop()
        origen_archivo = "PROV" if quien_externo == "Proveedor" else "SIMAJ"
    else:
        quien_externo = "SIMAJ"
        origen_archivo = "SIMAJ"
    st.caption("Cambiar el tipo de servicio, el equipo o el parámetro inicia un formato nuevo. Guarda tu avance antes de cambiar.")
es_proveedor = es_externo and quien_externo == "Proveedor"

st.divider()

col_logo, col_menu = st.columns([1, 2.5], gap="large")
with col_logo:
    if os.path.exists("simaj.png"): st.image("simaj.png", width=250)
    else: st.markdown("<h1 style='color:#00B2A9;'>SIMAJ</h1>", unsafe_allow_html=True)

with col_menu, st.container(key="selector_equipo"):
    st.markdown("#### Selecciona el Equipo a Calibrar:")
    gas_sel = st.radio("Selecciona el Equipo:", ["Ozono (O3)", "Óxidos de Nitrógeno (NOx)", "Monóxido de Carbono (CO)", "Dióxido de Azufre (SO2)", "PM BAM", "PM Thermo"],
                       horizontal=True, label_visibility="collapsed", key="k_gas", on_change=limpiar_formulario)
    pm_tipo = "N/A"
    if gas_sel in ["PM BAM", "PM Thermo"]:
        pm_tipo = st.radio("Selecciona el Parámetro de Partículas:", ["PM10", "PM2.5"], horizontal=True, key="k_pm", on_change=limpiar_formulario)

texto_servicio = tipo_servicio + (f" (realizado por: {quien_externo})" if es_externo else "")
texto_equipo = gas_sel if pm_tipo == "N/A" else f"{gas_sel} ({pm_tipo})"
st.markdown(f"<div class='resumen-servicio'><b>Tipo de servicio:</b> {texto_servicio} &nbsp;|&nbsp; <b>Equipo:</b> {texto_equipo}</div>", unsafe_allow_html=True)

st.divider()
datos_resumen = {}
es_gas = gas_sel in ["Ozono (O3)", "Óxidos de Nitrógeno (NOx)", "Monóxido de Carbono (CO)", "Dióxido de Azufre (SO2)"]
es_bam = gas_sel == "PM BAM"
es_thermo = gas_sel == "PM Thermo"
es_particulas = es_bam or es_thermo

flujo_ideal_vol = 0 

if gas_sel == "Ozono (O3)": 
    equipos_act = equipos_o3; modelo_analizador = "Serinus 10"
    flujo_ideal_vol = 500; flujo_tol = 0.025; cero_tol = 0.003; puntos_multipunto = [0.400, 0.300, 0.200, 0.100, 0.0]; span_gen_default = 0.400
elif gas_sel == "Óxidos de Nitrógeno (NOx)": 
    equipos_act = equipos_nox; modelo_analizador = "Serinus 40"
    flujo_ideal_vol = 650; flujo_tol = 0.05; cero_tol = 0.003; puntos_multipunto = [0.400, 0.300, 0.200, 0.100, 0.0]; span_gen_default = 0.400
elif gas_sel == "Monóxido de Carbono (CO)": 
    equipos_act = equipos_co; modelo_analizador = "Serinus 30"
    flujo_ideal_vol = 1000; flujo_tol = 0.025; cero_tol = 0.5; puntos_multipunto = [40.0, 30.0, 20.0, 10.0, 0.0]; span_gen_default = 40.0
elif gas_sel == "Dióxido de Azufre (SO2)": 
    equipos_act = equipos_so2; modelo_analizador = "Serinus 50"
    flujo_ideal_vol = 700; 
    flujo_tol = 0.025; cero_tol = 0.003; puntos_multipunto = [0.400, 0.300, 0.200, 0.100, 0.0]; span_gen_default = 0.400
elif es_bam or es_thermo:
    equipos_act = equipos_pm10 if pm_tipo == "PM10" else equipos_pm25
    modelo_analizador = "BAM 1020" if es_bam else "5014i"

# Valores por defecto para mantenimiento externo
fab_cal1_def = "" if es_externo else "Bios International Corp"
mod_cal1_def = "" if es_externo else "Definer 220 M"
lab_cal1_def = "" if es_externo else "COMEXSA"
tec_cal1_def = "" if es_externo else "Lizeth Morales"
cert_cal1_def = "" if es_externo else "E13496529 Flujo"
fab_cal2_def = "" if es_externo else "ACOEM"
mod_cal2_def = "" if es_externo else "Serinus Cal 3000"
lab_cal2_def = "" if es_externo else "INECC"
tec_cal2_def = "" if es_externo else "Humberto Bustamante"

tec_empresa_def = "" if es_externo else "Secretaría de Medio Ambiente y Desarrollo Territorial"
tec_nombre_def = "" if es_externo else "Jaudiel Alejandro Jaime Lomelí"
sup_nombre_def = "" if es_externo else "Beatriz Rodriguez Perez"
sup_empresa_def = "" if es_externo else "Desarrollo Territorial"
# Las fechas de certificado corresponden a los calibradores de SIMAJ; en mantenimiento externo se capturan
fecha_cal_pm_def = None if es_externo else datetime.date(2026, 1, 20)
fecha_cal1_def = None if es_externo else datetime.date(2026, 6, 20)
fecha_cal2_def = None if es_externo else datetime.date(2026, 8, 8)
# Solo un proveedor externo lleva "empresa"; si el servicio lo hace SIMAJ el dato es la institución
etq_empresa_tec = "Empresa proveedora" if es_proveedor else "Institución"

# ==========================================
# ENCABEZADO
# ==========================================
st.title(f"FORMATO DE CALIBRACIÓN {gas_sel}" if es_gas else f"FORMATO DE CALIBRACIÓN {gas_sel} ({pm_tipo})")
st.subheader("Parámetros Generales - Monitor de " + ("Gases" if es_gas else "Partículas"))

# ==========================================
# FUNCIONES AUXILIARES GLOBALES
# ==========================================
S_DAT = "Datos del analizador y condiciones ambientales"
S_HIS = "Histórico de mantenimientos"
S_PG = "Revisión de parámetros generales"
S_SENS = "Verificación y calibración de sensores y flujo"
S_MAS = "Calibración de masas (foils)"
S_FLU = "Verificación y ajuste de flujo"
S_LIM = "Limpieza, revisión y reemplazo"
S_CAL = "Datos del calibrador de gases"
S_CS = "Verificación cero-span"
S_MUL = "Calibración multipunto"
S_DET = "Revisión detallada de componentes"
S_RES = "Resumen y firmas finales"

ORDEN_PDF = [S_DAT, S_HIS, S_PG, S_SENS, S_MAS, S_FLU, S_LIM]
if es_externo: ORDEN_PDF.append(S_DET)
ORDEN_PDF.extend([S_CAL, S_CS, S_MUL])
if not es_externo: ORDEN_PDF.append(S_DET)
ORDEN_PDF.append(S_RES)

pdf_secciones = {}
pdf_ctx = {"sec": "", "sub": ""}

def _sec(nombre):
    return pdf_secciones.setdefault(nombre, {"pares": [], "tablas": {}, "textos": [], "textos_final": [], "notas": [], "graficas": [], "fotos": []})

# Opciones de selección que significan "sin capturar": no son un dato definitivo del reporte
SIN_DATO = ("-", "Selecciona una opción...")

def valor_pdf(valor):
    return "" if isinstance(valor, str) and valor in SIN_DATO else valor

def kv(seccion, etiqueta, valor, grupo=""):
    _sec(seccion)["pares"].append((etiqueta, valor_pdf(valor), grupo))
    return valor

def tabla_pdf(seccion, nombre, encabezado, fila, pesos=None, barra=False):
    _sec(seccion)["tablas"].setdefault(nombre, {"enc": encabezado, "filas": [], "pesos": pesos, "barra": barra})["filas"].append(fila)

def nota_pdf(seccion, texto):
    _sec(seccion)["notas"].append(texto)

def _res(ok):
    if ok is None: return ""
    return Alerta({True: "Cumple", False: "NO CUMPLE"}.get(ok, ""), ok)

ENC_PG = ["Parámetro", "Unidades", "Ideal", "Inicial", "Comentarios", "Final", "Comentarios"]
PESOS_PG = [2, 1, 1, 1.5, 1.5, 1.5, 1.5]

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
    tabla_pdf(S_PG, "", ENC_PG, [param, unit, ideal_str, Caja(val_ini), _res(r_ini), Caja(val_fin), _res(r_fin)], PESOS_PG)
    return r_ini, r_fin

def fila_libre(param, unit, ideal_str, key):
    c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 1, 1, 1.5, 1.5, 1.5, 1.5])
    with c1: st.write(param)
    with c2: st.write(unit)
    with c3: st.write(ideal_str)
    with c4: v_ini = st.text_input("ini", key=f"ini_{key}", label_visibility="collapsed")
    with c5: c_ini = st.text_area("c_ini", key=f"c_ini_{key}", label_visibility="collapsed", height="content")
    with c6: v_fin = st.text_input("fin", key=f"fin_{key}", label_visibility="collapsed")
    with c7: c_fin = st.text_area("c_fin", key=f"c_fin_{key}", label_visibility="collapsed", height="content")
    tabla_pdf(S_PG, "", ENC_PG, [param, unit, ideal_str, Caja(v_ini), Caja(c_ini), Caja(v_fin), Caja(c_fin)], PESOS_PG)
    return None, None

# Estado / limpieza / reemplazo: el valor guardado es el texto; el ícono solo se agrega al mostrarlo.
# "No" no lleva indicador de color (no limpiar o no reemplazar no es una falla) y "-" significa sin capturar.
OPC_ESTADO = ["-", "Bueno", "Malo"]
OPC_SINO = ["-", "Sí", "No"]
ICONOS_OPCION = {"Bueno": "Bueno 🟢", "Malo": "Malo 🔴", "Sí": "Sí ✅"}

def _ver_opcion(v):
    return ICONOS_OPCION.get(v, v)

def indicador_pdf(v):
    if v in ("Bueno", "Sí"): return Alerta(v, True)
    if v == "Malo": return Alerta(v, False)
    return Caja(valor_pdf(v))

def fila_comp(nombre, key, placeholder="Especificar..."):
    c1, c2, c3, c4, c5 = st.columns([2.2, 1.1, 1.1, 1.1, 3], vertical_alignment="top")
    with c1: st.write(nombre)
    with c2: estado = st.selectbox("Estado", OPC_ESTADO, key=f"est_{key}", label_visibility="collapsed", format_func=_ver_opcion)
    with c3: limpieza = st.selectbox("Limpieza", OPC_SINO, key=f"limp_{key}", label_visibility="collapsed", format_func=_ver_opcion)
    with c4: reemplazo = st.selectbox("Reemplazo", OPC_SINO, key=f"reemp_{key}", label_visibility="collapsed", format_func=_ver_opcion)
    with c5: obs = st.text_area("Obs", placeholder=placeholder, key=f"obs_{key}", label_visibility="collapsed", height="content")
    tabla_pdf(pdf_ctx["sec"], "", ["Componente", "Estado", "Limpieza", "Reemplazo", "Observaciones"],
              [nombre, indicador_pdf(estado), indicador_pdf(limpieza), indicador_pdf(reemplazo), Caja(obs, placeholder)], [2.2, 1.1, 1.1, 1.1, 3])

def fila_simple(nombre, key, ph="No se realizó"):
    c1, c2 = st.columns([1, 2], vertical_alignment="top")
    with c1: st.write(nombre)
    with c2: obs = st.text_area("obs", key=key, label_visibility="collapsed", placeholder=ph, height="content")
    tabla_pdf(pdf_ctx["sec"], pdf_ctx["sub"], None, [nombre, Caja(obs, ph)], [1, 2], barra=True)

LADO_FOTO = 600  # px de la miniatura cuadrada: suficiente para ver detalles en el PDF sin hacerlo pesado

@st.cache_data(max_entries=200, show_spinner=False)
def procesar_foto(datos):
    """Valida la imagen, corrige la orientación EXIF y devuelve una miniatura JPEG cuadrada: la foto completa
    centrada sobre fondo blanco, sin deformarla ni recortarla. Lanza una excepción si el archivo no es una imagen válida."""
    with Image.open(io.BytesIO(datos)) as img:
        img.verify()  # detecta archivos dañados o que no son imagen
    with Image.open(io.BytesIO(datos)) as img:
        img.draft("RGB", (LADO_FOTO * 2, LADO_FOTO * 2))  # JPEG grandes: decodifica a menor resolución y ahorra memoria
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            fondo = Image.new("RGB", img.size, "white")
            fondo.paste(img, mask=img.getchannel("A"))
            img = fondo
        img = img.convert("RGB")
        img.thumbnail((LADO_FOTO, LADO_FOTO), Image.Resampling.LANCZOS)
        cuadro = ImageOps.pad(img, (LADO_FOTO, LADO_FOTO), color="white")
    buf = io.BytesIO()
    cuadro.save(buf, "JPEG", quality=72, optimize=True)
    return buf.getvalue()

def renderizar_fotos_seccion(seccion_id, titulo, key_prefix, multiple=True, desc_default=""):
    """Dibuja el uploader de imágenes e incrusta las fotos directamente en la sección del PDF."""
    st.markdown(f"**{titulo}**")
    fotos_subidas = st.file_uploader("Seleccionar Imágenes", type=['png', 'jpg', 'jpeg'], accept_multiple_files=multiple, key=f"up_{key_prefix}")
    if not fotos_subidas: return
    lista_fotos = fotos_subidas if multiple else [fotos_subidas]
    with st.container(key=f"galeria_{key_prefix}"):
        # una fila de columnas por cada tres fotos: una descripción larga no se encima con las fotos de la fila siguiente
        for inicio in range(0, len(lista_fotos), 3):
            cols = st.columns(3, gap="medium")
            for col, foto in zip(cols, lista_fotos[inicio:inicio + 3]):
                with col:
                    try:
                        datos = procesar_foto(foto.getvalue())
                    except Exception:
                        st.warning(f"«{foto.name}» no es una imagen válida y no se incluirá en el reporte.")
                        continue
                    st.image(datos, use_container_width=True)
                    # la clave sigue al archivo (no a su posición) para que cada descripción se quede con su foto
                    ident = getattr(foto, "file_id", None) or f"{foto.name}_{foto.size}"
                    desc_foto = st.text_area("Descripción:", value=desc_default if not multiple else "", key=f"desc_fot_{key_prefix}_{ident}",
                                             placeholder="Ej. Detalle...", height="content")
                    _sec(seccion_id)["fotos"].append((datos, desc_foto))

# ==========================================
# 1. DATOS DEL ANALIZADOR
# ==========================================
with st.expander("🛠 DATOS DEL ANALIZADOR Y CONDICIONES AMBIENTALES", expanded=True):
    col_izq, col_der = st.columns([1, 1.2])
    with col_izq:
        kv(S_DAT, "Tipo de servicio", texto_servicio)
        estaciones = ["Selecciona una opción..."] + list(equipos_act.keys())
        if st.session_state.get("k_est") not in estaciones:  # p. ej. al cambiar a un equipo que no existe en esa estación
            st.session_state["k_est"] = estaciones[0]
        estacion_sel = kv(S_DAT, "Estación:", st.selectbox("Estación:", estaciones, key="k_est"))
        
        fab_final = "ACOEM" if es_gas else ("Met One" if es_bam else "Thermo Fisher")
        mod_final = modelo_analizador
        if gas_sel == "Monóxido de Carbono (CO)" and estacion_sel == "Águilas": mod_final = "ML9830"
        elif gas_sel == "Dióxido de Azufre (SO2)" and estacion_sel in ["Pintas", "Centro", "Oblatos", "Tlaquepaque"]: fab_final = "ECOTECH"
            
        fab_capturado = st.text_input("Fabricante", value=fab_final)
        kv(S_DAT, "Fabricante", fab_capturado)
        
        mod_capturado = st.text_input("Modelo", value=mod_final)
        kv(S_DAT, "Modelo", mod_capturado)
        
        num_serie_val = equipos_act.get(estacion_sel, "")
        ns_capturado = st.text_input("N/S (Automático)", value=num_serie_val, disabled=True)
        kv(S_DAT, "N/S (Automático)", ns_capturado)
        
        kv(S_DAT, "Presión ambiental ÚNICA (Torr)", st.number_input("Presión ambiental ÚNICA (Torr)", value=634.0, key="presion_unica"))
        
        falla = kv(S_DAT, "El analizador presenta Falla o Alarma", st.selectbox("El analizador presenta Falla o Alarma", ["-", "No 🟢", "Sí 🔴"], key="falla_alarma"))
        if falla == "Sí 🔴":
            desc_falla = st.text_area("Descripción de Falla o Alarma", key="desc_falla", height="content")
            _sec(S_DAT)["textos_final"].append(("Descripción de falla o alarma", desc_falla, ""))

        datos_resumen["Estación"] = estacion_sel
        datos_resumen["Gas Calibrado"] = gas_sel if es_gas else f"{gas_sel} ({pm_tipo})"
        
        if gas_sel == "Dióxido de Azufre (SO2)":
            marca_check = fab_capturado.upper()
            if "ML" in marca_check: flujo_ideal_vol = 500
            elif "ECOTECH" in marca_check: flujo_ideal_vol = 700
            elif "ACOEM" in marca_check: flujo_ideal_vol = 750

    with col_der:
        st.markdown("#### ")
        col_ini, col_fin = st.columns(2)
        with col_ini:
            st.markdown("### Inicial")
            fecha_ref = kv(S_DAT, "Fecha (Inicial)", st.date_input("Fecha (Inicial)", datetime.date.today(), max_value=datetime.date.today(), key="fecha_ini"), "Inicial")
            kv(S_DAT, "Hora (Inicial)", st.time_input("Hora (Inicial)", value=None, key="hora_ini"), "Inicial")
            kv(S_DAT, "Temp exterior (C°) - Ini", st.number_input("Temp exterior (C°) - Ini", value=None, key="temp_ext_ini"), "Inicial")
            kv(S_DAT, "Temp interior (C°) - Ini", st.number_input("Temp interior (C°) - Ini", value=None, key="temp_int_ini"), "Inicial")
            datos_resumen["Fecha de Servicio"] = str(fecha_ref)
            año_f, mes_f, dia_f = fecha_ref.strftime("%Y"), fecha_ref.strftime("%m"), fecha_ref.strftime("%d")
            
        with col_fin:
            st.markdown("### Final")
            kv(S_DAT, "Fecha (Final)", st.date_input("Fecha (Final)", datetime.date.today(), max_value=datetime.date.today(), key="fecha_fin"), "Final")
            kv(S_DAT, "Hora (Final)", st.time_input("Hora (Final)", value=None, key="hora_fin"), "Final")
            kv(S_DAT, "Temp exterior (C°) - Fin", st.number_input("Temp exterior (C°) - Fin", value=None, key="temp_ext_fin"), "Final")
            kv(S_DAT, "Temp interior (C°) - Fin", st.number_input("Temp interior (C°) - Fin", value=None, key="temp_int_fin"), "Final")

# ==========================================
# 2. HISTÓRICO (SE OCULTA EN MANTENIMIENTO EXTERNO)
# ==========================================
req_basico = req_cs = req_comp = True
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
            with c2: fecha_ult = st.date_input(f"Fecha {key_fecha}", value=fecha_default, max_value=datetime.date.today(), label_visibility="collapsed", key=f"hist_{key_fecha}")
            with c3: st.write(str(periodicidad_meses))
            with c4:
                es_req = (fecha_ref - fecha_ult).days > (periodicidad_meses * 30)
                tabla_pdf(S_HIS, "", ["Mantenimiento", "Fecha de último registro", "Periodicidad (Mes)", "Mantenimiento Requerido"],
                          [nombre_mant, Caja(fecha_ult), periodicidad_meses, Alerta("Requerido" if es_req else "No Requerido", not es_req)], [2, 1.5, 1, 1.5])
                if es_req: st.error("Requerido")
                else: st.success("No Requerido")
                return es_req

        req_basico = fila_historico("Mantenimiento Básico", "basico", datetime.date(2026, 5, 10), 1)
        req_cs = fila_historico("Verificación Cero-Span", "cero_span", datetime.date(2026, 1, 1), 3)
        req_comp = fila_historico("Mantenimiento Completo", "completo", datetime.date(2025, 1, 1), 6)

if es_gas: nomenclatura_tipo = "CM" if req_comp else ("CS" if req_cs else "VA")
else: nomenclatura_tipo = "CM" if req_comp else "VC"

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
        fila_libre("Flujo Estándar", "scc/min", "500", "o3_f_est")
        procesar_resultado(*fila_regla("Flujo Volumétrico", "cc/min", "500", 487.5, 512.5, "o3_f_vol"))
        procesar_resultado(*fila_regla("Presión de gas", "Torr", "629", 619.0, 630.0, "o3_p_gas"))
        procesar_resultado(*fila_regla("Voltaje de referencia", "Volts", "1.4 - 4", 1.4, 4.0, "o3_v_ref"))
        procesar_resultado(*fila_regla("Corriente de la lámpara", "mA", "9.5 - 10.5", 9.5, 10.5, "o3_c_lamp"))
        procesar_resultado(*fila_regla("Temperatura de la lámpara", "°C", "45 - 55", 45.0, 55.0, "o3_t_lamp"))
        procesar_resultado(*fila_regla("Pot de la lámpara UV", "N/A", "255", 255.0, 255.0, "o3_pot"))
        procesar_resultado(*fila_regla("Temperatura del Chassis", "°C", "0 - 50", 0.0, 50.0, "o3_t_chas"))
        procesar_resultado(*fila_regla("Temperatura del flujo", "°C", "10 - 90", 10.0, 90.0, "o3_t_flujo"))
        procesar_resultado(*fila_regla("INPUT (Pots)", "N/A", "50-200", 50.0, 200.0, "o3_in"))
        fila_libre("Ganancia", "N/A", "N/A", "o3_gan")
        
    elif gas_sel == "Óxidos de Nitrógeno (NOx)":
        fila_libre("Flujo Estándar", "scc/min", "650", "nox_f_est")
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
        fila_libre("Flujo Estándar", "scc/min", "1000", "co_f_est")
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
        fila_libre("Flujo Estándar", "scc/min", str(flujo_ideal_vol), "so2_f_vol")
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
        fila_libre("Rango de operación", "ug/m3", "0 - 1000", "th_rango")
        fila_libre("Tiempo de integración", "Minutos", "20", "th_tint")
        procesar_resultado(*fila_regla("Flujo Nominal", "L/min", "16.67", 16.00, 17.34, "th_fnom"))
        procesar_resultado(*fila_regla("Braw", "N/A", "5000 - 20000", 5000.0, 20000.0, "th_braw"))
        procesar_resultado(*fila_regla("Bzero", "N/A", "0", -500.0, 500.0, "th_bzero")) 
        procesar_resultado(*fila_regla("Alpha", "N/A", "0 - 100", 0.0, 100.0, "th_alpha"))
        procesar_resultado(*fila_regla("Temperatura Ambiental", "°C", "4 - 50", 4.0, 50.0, "th_tamb"))
        procesar_resultado(*fila_regla("Presión Barométrica", "mmHg", "400 - 800", 400.0, 800.0, "th_pbaro"))
        procesar_resultado(*fila_regla("Humedad relativa ambiental", "%", "5 - 95", 5.0, 95.0, "th_hr_amb"))
        procesar_resultado(*fila_regla("Humedad relativa de la muestra", "%", "5 - 95", 5.0, 95.0, "th_hr_mues"))
        procesar_resultado(*fila_regla("Presión de vacío de la muestra", "mmHg", "-5 a 250", -5.0, 250.0, "th_pvac"))
        procesar_resultado(*fila_regla("Temperatura de flujo", "°C", "5 - 60", 5.0, 60.0, "th_tflujo"))
        procesar_resultado(*fila_regla("Temperatura de la tarjeta", "°C", "5 - 60", 5.0, 60.0, "th_ttarj"))

    if len(resultados_pg) > 0:
        datos_resumen["Parámetros Generales"] = "Cumple" if all(resultados_pg) else "NO CUMPLE"
    else:
        datos_resumen["Parámetros Generales"] = "Sin datos calculables"

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
            st.date_input("Fecha de calibración/certificado", fecha_cal_pm_def, key="pm_cal_fecha")
            st.text_input("No de certificado", value="E252677468" if not es_externo else "", key="pm_cal_cert")
        for etiqueta, k, grupo in [("Marca", "pm_cal_mca", "Calibrador (Sensores y Flujo)"), ("Modelo", "pm_cal_mod", "Calibrador (Sensores y Flujo)"),
                                   ("N/S", "pm_cal_ns", "Calibrador (Sensores y Flujo)"), ("Laboratorio", "pm_cal_lab", "Certificación"),
                                   ("Fecha de calibración/certificado", "pm_cal_fecha", "Certificación"), ("No de certificado", "pm_cal_cert", "Certificación")]:
            kv(S_SENS, etiqueta, st.session_state.get(k), grupo)

        st.divider()

        def comentario(key, columna=None):
            destino = columna or st
            return destino.text_area("Comentarios", label_visibility="collapsed", key=key, placeholder="Comentarios...", height="content")

        if es_thermo:
            def sensor_3p(titulo, limite_dif, val_ideal_desc):
                """Verificación de un sensor con tres lecturas calibrador/monitor y su promedio."""
                pesos = [1, 1, 1, 2]
                enc = ["Calibrador", "Monitor", "Diferencia", "Comentarios"]
                st.markdown(f"#### {titulo}")
                c1, c2, c3, c4 = st.columns(pesos)
                c1.write("**Calibrador**"); c2.write("**Monitor**"); c3.write("**Diferencia**"); c4.write("**Comentarios**")

                cal_v, mon_v = [], []
                for i in range(1, 4):
                    c1, c2, c3, c4 = st.columns(pesos)
                    c_val = c1.number_input(f"c{i}", key=f"{titulo}_c{i}", label_visibility="collapsed", value=None)
                    m_val = c2.number_input(f"m{i}", key=f"{titulo}_m{i}", label_visibility="collapsed", value=None)
                    dif_txt = f"{(m_val - c_val):.2f}" if c_val is not None and m_val is not None else "-"
                    c3.write(dif_txt)
                    tabla_pdf(S_SENS, titulo, enc, [Caja(c_val), Caja(m_val), dif_txt, ""], pesos)
                    if c_val is not None: cal_v.append(c_val)
                    if m_val is not None: mon_v.append(m_val)

                prom_c = sum(cal_v) / len(cal_v) if cal_v else None
                prom_m = sum(mon_v) / len(mon_v) if mon_v else None
                c1, c2, c3, c4 = st.columns(pesos, vertical_alignment="top")
                c1.write(f"**{prom_c:.2f}**" if prom_c is not None else "Promedio")
                c2.write(f"**{prom_m:.2f}**" if prom_m is not None else "Promedio")
                dif_pdf = "-"
                if prom_c is not None and prom_m is not None:
                    dif_prom = prom_m - prom_c
                    ok = abs(dif_prom) <= limite_dif
                    (c3.success if ok else c3.error)(f"{dif_prom:.2f} " + ("✅" if ok else "❌"))
                    dif_pdf = Alerta(f"{dif_prom:.2f} - " + ("Cumple" if ok else "NO CUMPLE"), ok)
                else:
                    c3.write("-")
                obs_sensor = comentario(f"{titulo}_obs", c4)
                tabla_pdf(S_SENS, titulo, enc, [Neg(f"{prom_c:.2f}" if prom_c is not None else "Promedio"),
                                                Neg(f"{prom_m:.2f}" if prom_m is not None else "Promedio"), dif_pdf,
                                                Caja(obs_sensor, "Comentarios...")], pesos)
                nota_pdf(S_SENS, f"{titulo}: {val_ideal_desc}")
                st.write(f"<small>{val_ideal_desc}</small>", unsafe_allow_html=True)

            sensor_3p("Temperatura Ambiente", 2.0, "La diferencia debe ser menor a ± 2 °C")
            sensor_3p("Humedad Relativa", 2.0, "La diferencia debe ser menor a ± 2 %")
            sensor_3p("Temperatura de flujo", 2.0, "La diferencia debe ser menor a ± 2 °C")
            st.divider()

            pesos_baro = [1.1, 1, 1, 1, 2.2]
            enc_baro = ["", "Calibrador", "Monitor", "Diferencia (mmHg)", "Comentarios"]
            st.markdown("#### Presión Barométrica")
            c1, c2, c3, c4, c5 = st.columns(pesos_baro)
            c1.write(""); c2.write("**Calibrador**"); c3.write("**Monitor**"); c4.write("**Diferencia (mmHg)**"); c5.write("**Comentarios**")
            for fila_baro, k_cal, k_mon, k_obs, limite in [("Lectura", "C_bar_l", "M_bar_l", "obs_bar1", 10), ("Calibración", "C_bar_c", "M_bar_c", "obs_bar2", 2)]:
                c1, c2, c3, c4, c5 = st.columns(pesos_baro, vertical_alignment="top")
                c1.write(fila_baro)
                c_bar = c2.number_input(k_cal, label_visibility="collapsed", value=None, key=k_cal)
                m_bar = c3.number_input(k_mon, label_visibility="collapsed", value=None, key=k_mon)
                dif_bar = f"{abs(m_bar - c_bar):.1f}" if c_bar is not None and m_bar is not None else ""
                c4.write(dif_bar or "-")
                obs_bar = comentario(k_obs, c5)
                st.write(f"<small>{fila_baro}: la diferencia debe ser menor a ± {limite} mmHg</small>", unsafe_allow_html=True)
                tabla_pdf(S_SENS, "Presión Barométrica", enc_baro, [fila_baro, Caja(c_bar), Caja(m_bar), dif_bar, Caja(obs_bar)], pesos_baro)
            nota_pdf(S_SENS, "Presión barométrica: diferencia menor a ± 10 mmHg en la lectura y menor a ± 2 mmHg después de la calibración.")

            pesos_pfs = [1, 1.4, 1, 1, 2]
            st.markdown("#### Presión de Flujo de span (mmHg)")
            c1, c2, c3, c4, c5 = st.columns(pesos_pfs)
            c1.write(""); c2.write("**Manómetro Certificado**"); c3.write("**Monitor Inicial**"); c4.write("**Monitor Final**"); c5.write("**Comentarios**")

            c1, c2, c3, c4, c5 = st.columns(pesos_pfs, vertical_alignment="top")
            c1.write("Lectura")
            man_dif = c2.number_input("man_dif", label_visibility="collapsed", value=None, key="pfs_man")
            mon_ini = c3.number_input("mon_ini", label_visibility="collapsed", value=None, key="pfs_mini")
            mon_fin = c4.number_input("mon_fin", label_visibility="collapsed", value=None, key="pfs_mfin")
            obs_pfs = comentario("obs_pfs", c5)

            enc_pfs = ["", "Manómetro Certificado", "Monitor Inicial", "Monitor Final", "Comentarios"]
            tabla_pdf(S_SENS, "Presión de Flujo de span (mmHg)", enc_pfs, ["Lectura", Caja(man_dif), Caja(mon_ini), Caja(mon_fin), Caja(obs_pfs)], pesos_pfs)

            def render_flujo_thermo(titulo, key_prefix):
                pesos_flujo = [1, 1, 1, 1, 2]
                st.markdown(f"#### {titulo} (Lpm)")
                c1, c2, c3, c4, c5 = st.columns(pesos_flujo)
                c1.write(""); c2.write("**Calibrador**"); c3.write("**Monitor**"); c4.write("**% Desviación**"); c5.write("**Comentarios**")

                c1, c2, c3, c4, c5 = st.columns(pesos_flujo, vertical_alignment="top")
                c1.write("Lectura")
                f_cal = c2.number_input("f_cal", label_visibility="collapsed", value=None, key=f"{key_prefix}_cal")
                f_mon = c3.number_input("f_mon", label_visibility="collapsed", value=None, key=f"{key_prefix}_mon")
                obs_flujo = comentario(f"{key_prefix}_obs", c5)

                desv_str = ""
                if f_cal and f_mon is not None:
                    desv = ((f_mon - f_cal) / f_cal) * 100
                    desv_str = f"{desv:.2f}%"
                c4.write(f"**{desv_str}**" if desv_str else "-")

                st.write("<small>El valor promedio debe estar entre 16.00 y 17.34 Lpm. Si sale de límites, calibrar sensor.</small>", unsafe_allow_html=True)

                enc_flujo = ["", "Calibrador", "Monitor", "% Desviación", "Comentarios"]
                tabla_pdf(S_SENS, f"{titulo} (Lpm)", enc_flujo, ["Lectura", Caja(f_cal), Caja(f_mon), desv_str, Caja(obs_flujo)], pesos_flujo)

            render_flujo_thermo("Flujo Automático", "fauto")
            render_flujo_thermo("Flujo Manual", "fman")
            nota_pdf(S_SENS, "Flujo: el valor promedio debe estar entre 16.00 y 17.34 Lpm. Si sale de límites, calibrar sensor.")

        elif es_bam:
            # Criterio existente del formato: el flujo debe ser 16.67 ± 0.67 lpm (16.00 a 17.34)
            FLUJO_BAM_NOMINAL, FLUJO_BAM_MIN, FLUJO_BAM_MAX = 16.67, 16.00, 17.34

            # --- Etapa 1: verificación en el punto nominal ---
            pesos_verif = [1, 1, 1.2, 2.3]
            st.markdown("#### Verificación de flujo (lpm)")
            c1, c2, c3, c4 = st.columns(pesos_verif)
            c1.write("**Calibrador (lpm)**"); c2.write("**Monitor (lpm)**"); c3.write("**Resultado**"); c4.write("**Comentarios**")
            c1, c2, c3, c4 = st.columns(pesos_verif, vertical_alignment="top")
            c1.number_input("Calibrador verificación", value=FLUJO_BAM_NOMINAL, disabled=True, label_visibility="collapsed", key=f"bam_fv_cal_{pm_tipo}")
            verif_mon = c2.number_input("Monitor verificación", value=None, label_visibility="collapsed", key=f"bam_fv_mon_{pm_tipo}")
            cumple_verif = None if verif_mon is None else FLUJO_BAM_MIN <= verif_mon <= FLUJO_BAM_MAX
            with c3: evaluar_y_mostrar(verif_mon, FLUJO_BAM_MIN, FLUJO_BAM_MAX)
            obs_verif = comentario(f"bam_fv_obs_{pm_tipo}", c4)
            tabla_pdf(S_SENS, "Verificación de flujo (lpm)", ["Calibrador (lpm)", "Monitor (lpm)", "Resultado", "Comentarios"],
                      [Caja(FLUJO_BAM_NOMINAL), Caja(verif_mon), _res(cumple_verif), Caja(obs_verif)], pesos_verif)
            st.write("<small>El valor del flujo debe ser 16.67 ±0.67 lpm</small>", unsafe_allow_html=True)

            # --- Etapa 2: ajuste en tres puntos, solo si la verificación no cumple ---
            cumple_final_bam = cumple_verif
            if cumple_verif is None:
                st.info("Captura la lectura del monitor para saber si se requiere ajuste de flujo.")
            else:
                st.markdown(f"#### ¿Requiere ajuste de flujo?: **{'No' if cumple_verif else 'SÍ'}**")
                nota_pdf(S_SENS, f"¿Requiere ajuste de flujo?: {'No' if cumple_verif else 'SÍ'}")

            if cumple_verif is False:
                pesos_ajuste = [1, 1, 1.2]
                enc_ajuste = ["Calibrador (lpm)", "Monitor (lpm)", "Resultado"]
                st.markdown("#### Ajuste de flujo (lpm)")
                c1, c2, c3 = st.columns(pesos_ajuste)
                c1.write("**Calibrador (lpm)**"); c2.write("**Monitor (lpm)**"); c3.write("")

                cal_targets = [15.0, 18.43, 16.67]
                monitor_vals = []
                for idx, target in enumerate(cal_targets):
                    c1, c2, c3 = st.columns(pesos_ajuste)
                    c1.number_input(f"Target {idx}", value=target, disabled=True, label_visibility="collapsed", key=f"bam_ft_{idx}_{pm_tipo}")
                    m_val = c2.number_input(f"Monitor {idx}", value=None, label_visibility="collapsed", key=f"bam_fm_{idx}_{pm_tipo}")
                    if m_val is not None: monitor_vals.append(m_val)
                    tabla_pdf(S_SENS, "Ajuste de flujo (lpm)", enc_ajuste, [Caja(target), Caja(m_val), ""], pesos_ajuste)

                # el promedio se evalúa cuando están las tres lecturas del ajuste
                promedio_bam = sum(monitor_vals) / len(monitor_vals) if len(monitor_vals) == len(cal_targets) else None
                c1, c2, c3 = st.columns(pesos_ajuste)
                c1.write("**Promedio:**")
                cumple_final_bam = None
                if promedio_bam is not None:
                    c2.write(f"**{promedio_bam:.2f}**")
                    with c3: cumple_final_bam = evaluar_y_mostrar(promedio_bam, FLUJO_BAM_MIN, FLUJO_BAM_MAX)
                    tabla_pdf(S_SENS, "Ajuste de flujo (lpm)", enc_ajuste, [Neg("Promedio"), Neg(f"{promedio_bam:.2f}"), _res(cumple_final_bam)], pesos_ajuste)
                else:
                    c2.write("-")
                    c3.caption("Captura las tres lecturas del monitor.")

                st.markdown("**Observaciones del ajuste**")
                obs_ajuste = st.text_area("Observaciones del ajuste", key=f"bam_f_obs_{pm_tipo}", label_visibility="collapsed",
                                          placeholder="Comentarios...", height="content")
                tabla_pdf(S_SENS, "Observaciones del ajuste", None, [Caja(obs_ajuste, "Comentarios...")], [1])

            if cumple_final_bam is not None:
                texto_final = "Cumple" if cumple_final_bam else "NO CUMPLE"
                if cumple_verif is False: texto_final += " (después del ajuste)"
                (st.success if cumple_final_bam else st.error)(f"Resultado final del flujo: {texto_final}")
                nota_pdf(S_SENS, f"Resultado final del flujo: {texto_final}")
            nota_pdf(S_SENS, "El valor del flujo debe ser 16.67 ±0.67 lpm")

        if es_externo:
            st.divider()
            renderizar_fotos_seccion(S_SENS, "📷 Evidencias de Sensores y Flujo", "fot_sens", multiple=True)

    with st.expander("⚖️ CALIBRACIÓN DE MASAS (FOILS)", expanded=req_comp):
        if es_bam:
            # BAM-1020 (manual Met One, 3.4.7 "Span Membrane" y 6.9 "Zero Filter Background Test"):
            # se compara la masa medida de la membrana span contra su valor de fábrica; criterio < ±5 %.
            ERROR_SPAN_MAX = 5.0
            st.markdown("#### Ingreso de datos de la Membrana Span")
            col_cm1, col_cm2 = st.columns(2)
            with col_cm1:
                st.text_input("Equipo de Calibración (Foils)", placeholder="Ej. Foil Set CM3534", key="cm_eq")
                st.text_input("Reference No. / Certificado", placeholder="Ej. FH125C14", key="cm_ref")
                st.date_input("Fecha de Certificación de Foils", value=None, key="cm_fecha", format="YYYY/MM/DD")
            with col_cm2:
                background = st.number_input("Background (mg/m³)", value=0.0, format="%.4f", step=0.0001, key="cm_bkg")
                span_esperado = st.number_input("Expected Span Membrane (mg/cm²)", value=0.8, format="%.4f", step=0.0001, key="cm_span_esp",
                                                help="Valor de la membrana span del certificado de fábrica del BAM (usualmente cerca de 0.800).")

            st.markdown("---")
            pesos_mas = [1.2, 1, 1.4]
            c1, c2, c3 = st.columns(pesos_mas)
            with c1: st.write("**Lectura**")
            with c2: st.write("**Valor Ideal**")
            with c3: st.write("**Lectura del equipo**")

            c1, c2, c3 = st.columns(pesos_mas)
            with c1: st.write("Zero Count (I1)")
            with c2: st.write("N/A")
            with c3: i1 = st.number_input("Zero Count (I1)", value=None, min_value=0, step=1, format="%d", key="cm_i1", label_visibility="collapsed",
                                          help="Valores típicos entre 600,000 y 2,200,000.")

            c1, c2, c3 = st.columns(pesos_mas)
            with c1: st.write("Span Count (I2)")
            with c2: st.write("N/A")
            with c3: i2 = st.number_input("Span Count (I2)", value=None, min_value=0, step=1, format="%d", key="cm_i2", label_visibility="collapsed")

            c1, c2, c3 = st.columns(pesos_mas)
            with c1: st.write("Measured Mass (mg/cm²)")
            with c2: st.write(f"{span_esperado:.4f}" if span_esperado is not None else "-")
            with c3: masa_medida = st.number_input("Measured Mass (mg/cm²)", value=None, format="%.4f", step=0.0001, key="cm_masa_med",
                                                   label_visibility="collapsed")

            # % Error = ((Measured Mass - Expected Span Membrane) / Expected Span Membrane) * 100
            error_span = cumple_span = None
            if masa_medida is not None and span_esperado:
                error_span = (masa_medida - span_esperado) / span_esperado * 100
                cumple_span = abs(error_span) <= ERROR_SPAN_MAX
            c1, c2, c3 = st.columns(pesos_mas)
            with c1: st.write("**% Error**")
            with c2: st.write(f"< ±{ERROR_SPAN_MAX:g}%")
            with c3:
                if error_span is None: st.write("-")
                elif cumple_span: st.success(f"{error_span:.2f}% — Cumple ✅")
                else: st.error(f"{error_span:.2f}% — NO CUMPLE ❌")

            def _cuatro(v): return f"{v:.4f}" if v is not None else None
            for etiqueta, valor in [("Equipo de calibración (foils)", st.session_state.get("cm_eq")), ("Reference No. / Certificado", st.session_state.get("cm_ref")),
                                    ("Fecha de certificación de foils", st.session_state.get("cm_fecha")), ("Background (mg/m³)", _cuatro(background)),
                                    ("Expected Span Membrane (mg/cm²)", _cuatro(span_esperado))]:
                kv(S_MAS, etiqueta, valor)
            enc_masas = ["Lectura", "Valor Ideal", "Lectura del equipo"]
            tabla_pdf(S_MAS, "", enc_masas, ["Zero Count (I1)", "N/A", Caja(i1)], pesos_mas)
            tabla_pdf(S_MAS, "", enc_masas, ["Span Count (I2)", "N/A", Caja(i2)], pesos_mas)
            tabla_pdf(S_MAS, "", enc_masas, ["Measured Mass (mg/cm²)", _cuatro(span_esperado), Caja(_cuatro(masa_medida))], pesos_mas)
            tabla_pdf(S_MAS, "", enc_masas, [Neg("% Error"), f"< ±{ERROR_SPAN_MAX:g}%",
                                             Alerta(f"{error_span:.2f}% - " + ("Cumple" if cumple_span else "NO CUMPLE"), cumple_span) if error_span is not None else ""], pesos_mas)
            nota_pdf(S_MAS, "% Error = ((Measured Mass - Expected Span Membrane) / Expected Span Membrane) x 100. Criterio de aceptación: < ±5%.")
        else:
            st.markdown("#### Ingreso de datos de Foils de Calibración")
            col_cm1, col_cm2 = st.columns(2)
            with col_cm1:
                st.text_input("Equipo de Calibración (Foils)", placeholder="Ej. Foil Set CM3534", key="cm_eq")
                st.text_input("Reference No. / Certificado", placeholder="Ej. FH125C14", key="cm_ref")
            with col_cm2:
                # Sin fecha ni coeficiente predeterminados: dependen del juego de foils y del equipo. Se capturan o se
                # recuperan con el borrador de esta estación/equipo (botón Cargar).
                st.date_input("Fecha de Certificación de Foils", value=None, key="cm_fecha", format="YYYY/MM/DD")
                st.number_input("Mass Coefficient Inicial", value=None, key="cm_mass_ini", placeholder="Valor actual del equipo",
                                help="Es propio de cada equipo: captúralo de la pantalla del monitor o de su registro anterior.")

            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            with c1: st.write("**Lectura**")
            with c2: st.write("**Foil Value Span (Ideal)**")
            with c3: st.write("**Beta Average (Lectura del equipo)**")

            c1, c2, c3 = st.columns(3)
            with c1: st.write("Calibración Cero")
            with c2: st.write("N/A")
            with c3: st.number_input("Beta Cero", value=None, key="cm_beta_cero", label_visibility="collapsed")

            c1, c2, c3 = st.columns(3)
            with c1: st.write("Calibración Span")
            with c2: st.number_input("Span Ideal", value=1000.0, key="cm_span_ideal", label_visibility="collapsed")
            with c3: st.number_input("Beta Span", value=None, key="cm_beta_span", label_visibility="collapsed")

            for etiqueta, k in [("Equipo de calibración (foils)", "cm_eq"), ("Reference No. / Certificado", "cm_ref"),
                                ("Fecha de certificación de foils", "cm_fecha"), ("Mass Coefficient inicial", "cm_mass_ini")]:
                kv(S_MAS, etiqueta, st.session_state.get(k))
            enc_masas = ["Lectura", "Foil Value Span (Ideal)", "Beta Average (Lectura del equipo)"]
            tabla_pdf(S_MAS, "", enc_masas, ["Calibración Cero", "N/A", Caja(st.session_state.get("cm_beta_cero"))])
            tabla_pdf(S_MAS, "", enc_masas, ["Calibración Span", Caja(st.session_state.get("cm_span_ideal")), Caja(st.session_state.get("cm_beta_span"))])

        if es_externo:
            st.divider()
            renderizar_fotos_seccion(S_MAS, "📷 Evidencia de Calibración de Masas", "fot_mas", multiple=True)

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
            st.date_input("Fecha de calibración/certificado", fecha_cal1_def, key="vig_cal1")
            st.text_input("No de certificado", value=cert_cal1_def, key="cert_cal1")

        for etiqueta, k, grupo in [("Fabricante", "fab_cal1", "Calibrador de Flujo"), ("Modelo", "mod_cal1", "Calibrador de Flujo"),
                                   ("N/S Calibrador de Flujo", "ns_cal1", "Calibrador de Flujo"), ("Laboratorio", "lab_cal1", "Certificación"),
                                   ("Técnico", "tec_cal1", "Certificación"), ("Fecha de calibración/certificado", "vig_cal1", "Certificación"),
                                   ("No de certificado", "cert_cal1", "Certificación")]:
            kv(S_FLU, etiqueta, st.session_state.get(k), grupo)

        def render_tabla_flujo_gases(titulo, key_prefix):
            """Devuelve (lectura volumétrica, cumple). Sin lectura no hay evaluación (None)."""
            pesos_flujo = [2, 1, 1.5, 1.5, 1.5]
            enc_flujo = ["Parámetro", "Ideal", "Medición", "% Desviación", "Resultado"]
            st.markdown(f"#### {titulo}")
            c1, c2, c3, c4, c5 = st.columns(pesos_flujo)
            with c1: st.write("Flujo Estandar (scc/min)")
            with c2: st.write("-")
            with c3: val_est = st.number_input("val_est", key=f"{key_prefix}_est", label_visibility="collapsed", value=None)
            with c4: st.write("-")
            with c5: st.write("-")

            c1, c2, c3, c4, c5 = st.columns(pesos_flujo)
            with c1: st.write("Flujo Volumétrico (cc/min)")
            with c2: st.write(str(flujo_ideal_vol))
            with c3: val = st.number_input("val_vol", key=f"{key_prefix}_vol", label_visibility="collapsed", value=None)

            resultado_cumple, desv_txt = None, ""
            if val is not None:
                desv = (val - flujo_ideal_vol) / flujo_ideal_vol
                resultado_cumple = abs(desv) <= flujo_tol
                desv_txt = f"{desv * 100:.2f}%"
            with c4: st.write(desv_txt or "-")
            with c5:
                if resultado_cumple is not None:
                    if resultado_cumple: st.success("Cumple ✅")
                    else: st.error("NO CUMPLE ❌")
                else: st.write("-")

            tabla_pdf(S_FLU, titulo, enc_flujo, ["Flujo Estandar (scc/min)", "-", Caja(val_est), "", ""], pesos_flujo)
            tabla_pdf(S_FLU, titulo, enc_flujo, ["Flujo Volumétrico (cc/min)", str(flujo_ideal_vol), Caja(val), desv_txt, _res(resultado_cumple)], pesos_flujo)
            return val, resultado_cumple

        st.caption(f"Tolerancia del flujo volumétrico: ± {flujo_tol * 100:g}% respecto a {flujo_ideal_vol} cc/min.")
        _, cumple_verif_gas = render_tabla_flujo_gases("Verificación", "verif")
        if cumple_verif_gas is None:
            st.info("Captura el flujo volumétrico para saber si se requiere ajuste.")
        else:
            req_ajuste_final = "No" if cumple_verif_gas else "SÍ"
            st.markdown(f"#### ¿Requiere ajuste volumétrico?: **{req_ajuste_final}**")
            nota_pdf(S_FLU, f"¿Requiere ajuste volumétrico?: {req_ajuste_final}")

        # El ajuste solo se muestra (y solo llega al PDF) cuando la verificación no cumple
        if cumple_verif_gas is False:
            _, cumple_ajuste_gas = render_tabla_flujo_gases("Ajuste", "ajus")
            if cumple_ajuste_gas is not None:
                nota_pdf(S_FLU, f"Resultado final del flujo: {'Cumple' if cumple_ajuste_gas else 'NO CUMPLE'} (después del ajuste)")

# ==========================================
# DEFINICIÓN FUNCIÓN DE REVISIÓN DETALLADA
# ==========================================
def bloque_revision_detallada():
    """Función para encapsular la sección Detallada y moverla dinámicamente."""
    with st.expander("🔍 REVISIÓN DETALLADA DE COMPONENTES", expanded=req_comp):
        pdf_ctx["sec"], pdf_ctx["sub"] = S_DET, ""
        
        if es_externo:
            renderizar_fotos_seccion(S_DET, "📷 Evidencias de Mantenimiento y Componentes", "fot_lim", multiple=True)
            st.divider()
            
        c1, c2, c3, c4, c5 = st.columns([2.2, 1.1, 1.1, 1.1, 3])
        with c1: st.write("**Componente**")
        with c2: st.write("**Estado**")
        with c3: st.markdown("<b>Limpieza</b>", unsafe_allow_html=True)
        with c4: st.markdown("<b>Reemplazo</b>", unsafe_allow_html=True)
        with c5: st.write("**Observaciones**")

        if es_gas:
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
            else: 
                fila_comp("Bomba de Vacío externa", "d_bomba_gn")
                fila_comp("Generador de Ozono", "d_gen_gn")
                fila_comp("Permapure", "d_perm_gn")
        elif es_particulas:
            fila_comp("Sensores de humedad / temperatura", "d_sensores")
            fila_comp("Sistema neumático y O-rings", "d_orings_pm")

# ==========================================
# 6. LIMPIEZA, REVISIÓN Y REEMPLAZO
# ==========================================
with st.expander("🔍 LIMPIEZA, REVISIÓN Y REEMPLAZO", expanded=req_basico):
    pdf_ctx["sec"], pdf_ctx["sub"] = S_LIM, ""
    if es_gas:
        c1, c2, c3, c4, c5 = st.columns([2.2, 1.1, 1.1, 1.1, 3])
        with c1: st.write("**Componente**")
        with c2: st.write("**Estado**")
        with c3: st.markdown("<b>Limpieza</b>", unsafe_allow_html=True)
        with c4: st.markdown("<b>Reemplazo</b>", unsafe_allow_html=True)
        with c5: st.write("**Observaciones**")

        if gas_sel == "Ozono (O3)":
            fila_comp("Lámpara UV (revisión electrónica)", "b_lamp")
            fila_comp("Mangueras", "b_mang")
            fila_comp("Válvulas de calibración", "b_valv")
            fila_comp("Filtro externo de 47 mm", "b_fil")
        elif gas_sel == "Óxidos de Nitrógeno (NOx)":
            fila_comp("Tubería", "b_tub")
            fila_comp("Mangueras", "b_mang_nox")
            fila_comp("Generador de Ozono", "b_gen")
        elif gas_sel == "Monóxido de Carbono (CO)":
            fila_comp("Tubería", "b_tub_co")
            fila_comp("Mangueras", "b_mang_co")
            fila_comp("Filtro externo de 47 mm", "b_fil_co")
        elif gas_sel == "Dióxido de Azufre (SO2)":
            fila_comp("Tubería", "b_tub_so2")
            fila_comp("Mangueras", "b_mang_so2")
            fila_comp("Lámpara UV", "b_lamp_so2")
    
    elif es_particulas:
        st.markdown("<div class='header-tabla'>Limpieza de:</div>", unsafe_allow_html=True)
        pdf_ctx["sub"] = "Limpieza de:"
        fila_simple("Gabinete", "limp_gab")
        fila_simple("Tubo de la traza", "limp_tub")
        fila_simple("Cabezal", "limp_cab")
        if es_thermo: fila_simple("Cortador de Partículas", "limp_cort")
        fila_simple("Tarjetas Electrónicas" if es_thermo else "Tarjetas", "limp_tarj")
        fila_simple("Ventiladores" if es_thermo else "Ventilador", "limp_vent")
        fila_simple("Celda de medición", "limp_celd")

        st.markdown("<div class='header-tabla'>Revisión de:</div>", unsafe_allow_html=True)
        pdf_ctx["sub"] = "Revisión de:"
        fila_simple("Display", "rev_disp", "En óptimas condiciones")
        fila_simple("Calefactor de la Traza / factor de la Traza", "rev_calf", "Opera correctamente")
        fila_simple("Traza", "rev_traza", "En óptimas condiciones")
        fila_simple("Fugas", "rev_fugas", "Ninguna")
        fila_simple("Fuente de voltaje", "rev_fvolt", "Opera correctamente")
        fila_simple("Cinta de vidrio / filtro", "rev_cinta", "Tiene 1/2 de cinta disponible")
        if es_thermo: fila_simple("Rodamiento de celda", "rev_rod", "En óptimas condiciones")
        fila_simple("Bomba", "rev_bomba", "Opera correctamente")

        st.markdown("<div class='header-tabla'>Reemplazo (en caso de ser necesario) de:</div>", unsafe_allow_html=True)
        pdf_ctx["sub"] = "Reemplazo (en caso de ser necesario) de:"
        if es_thermo: fila_simple("Ventilador de fuente", "reemp_vent")
        fila_simple("Cinta de vidrio / filtro", "reemp_cinta")
        if es_bam: fila_simple("O-rings", "reemp_orings")
        fila_simple("Bomba de Vacío", "reemp_bomba")

# (!!!) LÓGICA CONDICIONAL DE LA SECCIÓN DETALLADA
if es_externo:
    bloque_revision_detallada()

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
            st.date_input("Fecha de calibración/certificado", fecha_cal2_def, key="vig_calib2")
        for etiqueta, k, grupo in [("Fabricante", "fab_calib2", ""), ("Modelo", "mod_calib2", ""), ("N/S Calibrador de Gases", "ns_calib2", ""),
                                   ("Laboratorio", "lab_calib2", "Certificación"), ("Técnico", "tec_calib2", "Certificación"),
                                   ("Fecha de calibración/certificado", "vig_calib2", "Certificación")]:
            kv(S_CAL, etiqueta, st.session_state.get(k), grupo)

    with st.expander("⚖️ VERIFICACIÓN CERO-SPAN", expanded=req_cs):
        col_cs_izq, col_cs_der = st.columns(2)
        with col_cs_izq:
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1: st.write("")
            with c2: st.write("**Inicial**")
            with c3: st.write("**Final**")
            
            if gas_sel in ["Ozono (O3)", "Monóxido de Carbono (CO)", "Dióxido de Azufre (SO2)"]:
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1: st.write("Ganancia")
                with c2: st.number_input("ini", key="cs_g_i", label_visibility="collapsed", value=None)
                with c3: st.number_input("fin", key="cs_g_f", label_visibility="collapsed", value=None)
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1: st.write("Zero Offset (ppb/ppm)")
                with c2: st.number_input("ini", key="cs_z_i", label_visibility="collapsed", value=None)
                with c3: st.number_input("fin", key="cs_z_f", label_visibility="collapsed", value=None)
                for param, kp in [("Ganancia", "cs_g_"), ("Zero Offset (ppb/ppm)", "cs_z_")]:
                    tabla_pdf(S_CS, "", ["", "Inicial", "Final"], [param, Caja(st.session_state.get(f"{kp}i")), Caja(st.session_state.get(f"{kp}f"))], [2, 1, 1])
            else:
                for param, kp in [("Ganancia NO", "cs_gn_"), ("Ganancia Aux (NOx)", "cs_gax_"), ("Zero Offset NO", "cs_zno_"), ("Zero Offset NO2", "cs_zno2_")]:
                    c1, c2, c3 = st.columns([2, 1, 1])
                    with c1: st.write(param)
                    with c2: st.number_input("ini", key=f"{kp}i", label_visibility="collapsed", value=None)
                    with c3: st.number_input("fin", key=f"{kp}f", label_visibility="collapsed", value=None)
                    tabla_pdf(S_CS, "", ["", "Inicial", "Final"], [param, Caja(st.session_state.get(f"{kp}i")), Caja(st.session_state.get(f"{kp}f"))], [2, 1, 1])

        with col_cs_der:
            st.markdown("**Tiempo de respuesta al suministrar gas**")
            for gas, kp in [("Cero", "tr_c"), ("Span", "tr_s")]:
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1: st.write(gas)
                with c2: st.number_input("val", key=kp, label_visibility="collapsed", value=None)
                with c3: st.write("min")
                tabla_pdf(S_CS, "Tiempo de respuesta al suministrar gas", None, [gas, Caja(st.session_state.get(kp)), "min"], [1, 2, 1])

        col_cs_cero, col_cs_span = st.columns(2)
        dif_c = desv_s = None
        
        with col_cs_cero:
            st.markdown("#### Concentración Cero")
            c1, c2, c3 = st.columns(3)
            val_cg_ideal = 0.0
            with c1: val_cg = st.number_input("Cero Gen", value=val_cg_ideal, disabled=True, key="vcg")
            with c2: resp_c = st.number_input("Resp Cero", value=None, format="%.4f", key="rac")
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
            with c2: resp_s = st.number_input("Resp Span", value=None, format="%.4f", key="ras")
            with c3:
                if resp_s is not None and val_sg != 0:
                    desv_s = (resp_s - val_sg) / val_sg
                    st.write(f"% desv: **{desv_s * 100:.2f}%**")
                    if -0.03 <= desv_s <= 0.03: st.success("Cumple ✅")
                    else: st.error("NO CUMPLE ❌")

        tabla_pdf(S_CS, "Concentración Cero", ["Cero Gen", "Resp Cero", "Diferencia", "Resultado"],
                  [Caja(val_cg), Caja(resp_c), f"{dif_c:.4f}" if dif_c is not None else "",
                   _res(-cero_tol <= dif_c <= cero_tol if dif_c is not None else None)])
        tabla_pdf(S_CS, "Concentración Span", ["Span Gen", "Resp Span", "% desv", "Resultado"],
                  [Caja(val_sg), Caja(resp_s), f"{desv_s * 100:.2f}%" if desv_s is not None else "",
                   _res(-0.03 <= desv_s <= 0.03 if desv_s is not None else None)])
                   
        if es_externo:
            st.divider()
            renderizar_fotos_seccion(S_CS, "📷 Evidencia de Cero-Span", "fot_cs", multiple=False, desc_default="Pantalla Cero-Span")

    with st.expander("📈 CALIBRACIÓN MULTIPUNTO", expanded=req_comp):
        col_pts, col_res = st.columns([1.5, 1])
        with col_pts:
            x_vals, y_vals, desviaciones = [], [], []
            for i, cal_val in enumerate(puntos_multipunto):
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.number_input("cal", value=cal_val, disabled=True, key=f"mc_{i}_{gas_sel}", label_visibility="collapsed")
                with c2: ana_val = st.number_input("ana", value=None, key=f"ma_{i}_{gas_sel}", format="%.4f", label_visibility="collapsed")
                with c3:
                    if ana_val is not None:
                        dif = ana_val - cal_val
                        st.write(f"**{dif:.4f}**")
                        if cal_val != 0:
                            desviaciones.append(dif / cal_val)
                            st.write(f"{(dif/cal_val)*100:.2f}%")
                if ana_val is not None: x_vals.append(cal_val); y_vals.append(ana_val)
                tabla_pdf(S_MUL, "", ["Calibrador", "Analizador", "Diferencia", "% Desviación"],
                          [Caja(cal_val), Caja(ana_val), f"{ana_val - cal_val:.4f}" if ana_val is not None else "",
                           f"{(ana_val - cal_val) / cal_val * 100:.2f}%" if ana_val is not None and cal_val else ""])

        m = b = r2 = promedio = None
        if len(x_vals) > 1:
            try:
                m, b = np.polyfit(np.array(x_vals), np.array(y_vals), 1)
                r_matrix = np.corrcoef(x_vals, y_vals)
                r2 = r_matrix[0,1]**2
                if desviaciones: promedio = sum(desviaciones) / len(desviaciones)
            except: pass

        with col_res:
            if m is not None:
                lim_b = 2.0 if gas_sel == "Monóxido de Carbono (CO)" else 0.02
                
                cond_m = 0.98 <= m <= 1.02
                cond_b = -lim_b <= b <= lim_b
                cond_r2 = r2 > 0.99
                
                st.write("**Pendiente (m)**")
                c1, c2 = st.columns([1, 4])
                with c1: st.write("✅" if cond_m else "❌")
                with c2: st.markdown(f"#### {m:.5f}")
                
                st.write("**Intercepto (b)**")
                c1, c2 = st.columns([1, 4])
                with c1: st.write("✅" if cond_b else "❌")
                with c2: st.markdown(f"#### {b:.5f}")
                
                st.write("**R²**")
                c1, c2 = st.columns([1, 4])
                with c1: st.write("✅" if cond_r2 else "❌")
                with c2: st.markdown(f"#### {r2:.6f}")
                
                aprobado = cond_m and cond_b and cond_r2
                
                for etiqueta, valor in [("Pendiente (m)", f"{m:.5f}"), ("Intercepto (b)", f"{b:.5f}"), ("R2", f"{r2:.6f}")]:
                    tabla_pdf(S_MUL, "Regresión", None, [etiqueta, Caja(valor)], [1, 1])
                tabla_pdf(S_MUL, "Regresión", None, ["Resultado", Alerta("MULTIPUNTO APROBADO" if aprobado else "MULTIPUNTO RECHAZADO", aprobado)], [1, 1])
                if aprobado: st.success("✅ MULTIPUNTO APROBADO")
                else: st.error("❌ MULTIPUNTO RECHAZADO")

            else:
                st.info("Ingresa los datos para regresión.")

        if m is not None:
            st.divider()
            col_graf, col_ley = st.columns([1.5, 1], gap="medium")
            
            with col_ley:
                st.write("<br>", unsafe_allow_html=True)
                st.markdown("""
                <div style='background-color:#f0f2f6; padding:15px; border-radius:5px; border:1px solid #ccc;'>
                    <b style='font-size: 16px;'>Análisis de resultados y criterios de aceptación</b><br>
                    <span style='font-size: 14px;'>
                    <br>La calibración será aceptada sí: <i>(Depende de la marca y modelo de equipo estos criterios)</i><br><br>
                    • El gradiente (m) se encuentra entre los valores de 0.98 y 1.02<br>
                    • La intercepción (b) esté entre - 2 a + 2<br>
                    • La correlación (R²) es mayor que 0.99.<br><br>
                    <b>Rechazar la calibración si el criterio de arriba no se obtiene. La calibración puede fallar por fugas o por el depurador.</b>
                    </span>
                </div>
                """, unsafe_allow_html=True)

            with col_graf:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='markers', name='Datos', marker=dict(color='#00B2A9', size=10)))
                x_line = np.linspace(min(x_vals), max(x_vals), 100)
                y_line = m * x_line + b
                fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', name='Ajuste Lineal', line=dict(color='#F37021')))
                fig.update_layout(title="Regresión Lineal: Calibrador vs Analizador", xaxis_title="Calibrador", yaxis_title="Analizador", 
                                  height=350, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)

            # La gráfica del PDF se dibuja con reportlab a partir de los mismos datos (no depende de kaleido ni de un navegador)
            _sec(S_MUL)["regresion"] = {"x": list(x_vals), "y": list(y_vals), "m": float(m), "b": float(b)}

        if es_externo:
            st.divider()
            renderizar_fotos_seccion(S_MUL, "📷 Gráfica de Calibración Multipunto (Envidas y analizador)", "fot_mul", multiple=False, desc_default="Gráfica Multipunto Envidas")

# (!!!) LÓGICA CONDICIONAL DE LA SECCIÓN DETALLADA
if not es_externo:
    bloque_revision_detallada()

# ==========================================
# 10. RESUMEN Y FIRMAS
# ==========================================
with st.expander("✍ RESUMEN Y FIRMAS FINALES", expanded=True):
    st.markdown("**Observaciones Generales**")
    obs_gen = st.text_area("Obs Gen", placeholder="Mencionar anomalías...", label_visibility="collapsed", key="res_obs", height="content")
    st.markdown("**Conclusiones**")
    conclusiones = st.text_area("Conclusiones", placeholder="Mencionar conclusiones...", label_visibility="collapsed", key="res_conc", height="content")

    st.write("<br>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        st.markdown("<div class='header-firma'>Técnico / Operador</div>", unsafe_allow_html=True)
        st.text_input(etq_empresa_tec, value=tec_empresa_def, key="e_tec")
        st.text_input("Nombre", value=tec_nombre_def, key="n_tec")
        st.date_input("Fecha", datetime.date.today(), key="f_tec")
        st.markdown("""<div style="display: flex; align-items: flex-end; margin-top: 30px;"><span style="font-weight: bold; margin-right: 15px;">Firma:</span><div class="linea-firma"></div></div>""", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='header-firma'>Supervisado / Revisado por</div>", unsafe_allow_html=True)
        st.text_input("Institución", value="SEMADET", disabled=es_externo, key="e_sup")
        st.text_input("Nombre", value=sup_nombre_def if not es_externo else "", key="n_sup")
        st.date_input("Fecha", datetime.date.today(), key="f_sup")
        st.markdown("""<div style="display: flex; align-items: flex-end; margin-top: 30px;"><span style="font-weight: bold; margin-right: 15px;">Firma:</span><div class="linea-firma"></div></div>""", unsafe_allow_html=True)

    with c3:
        st.markdown("<div class='header-firma'>Supervisor SEMADET</div>", unsafe_allow_html=True)
        st.text_input("Cargo", value="Coordinador Especializado", key="c_sema")
        st.text_input("Nombre", value="Beatriz Rodriguez Perez", key="n_sema", placeholder="Nombre del supervisor...")
        st.date_input("Fecha", datetime.date.today(), key="f_sema")
        st.markdown("""<div style="display: flex; align-items: flex-end; margin-top: 30px;"><span style="font-weight: bold; margin-right: 15px;">Firma:</span><div class="linea-firma"></div></div>""", unsafe_allow_html=True)

st.divider()

# ==========================================
# ENVÍO DE DATOS A GOOGLE DRIVE Y PDF
# ==========================================
def preparar_resumen():
    """Agrega a pdf_secciones el resumen y las firmas con los valores capturados en esta ejecución."""
    pdf_secciones.pop(S_RES, None)
    _sec(S_RES)["firmas"] = True
    _sec(S_RES)["textos"] = [("Observaciones Generales", st.session_state.get("res_obs"), "Mencionar anomalías..."),
                             ("Conclusiones", st.session_state.get("res_conc"), "Mencionar conclusiones...")]

    for grupo, campos in [("Técnico / Operador", [(etq_empresa_tec, "e_tec"), ("Nombre", "n_tec"), ("Fecha", "f_tec")]),
                          ("Supervisado / Revisado por", [("Institución", "e_sup"), ("Nombre", "n_sup"), ("Fecha", "f_sup")]),
                          ("Supervisor SEMADET", [("Cargo", "c_sema"), ("Nombre", "n_sema"), ("Fecha", "f_sema")])]:
        for etiqueta, k in campos: kv(S_RES, etiqueta, st.session_state.get(k), grupo)

preparar_resumen()
# Fotografía de los datos de esta ejecución: el PDF descargado y el enviado se construyen con exactamente lo mismo
_titulo_pdf = f"FORMATO DE CALIBRACIÓN {gas_sel}" if es_gas else f"FORMATO DE CALIBRACIÓN {gas_sel} ({pm_tipo})"
_subtitulo_pdf = "Parámetros Generales - Monitor de " + ("Gases" if es_gas else "Partículas")
_logo_pdf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "simaj.png")
_secciones_pdf = [(s, pdf_secciones[s]) for s in ORDEN_PDF if s in pdf_secciones]

def generar_pdf():
    return construir_pdf(_titulo_pdf, _subtitulo_pdf, _secciones_pdf, _logo_pdf)

def _segmento_archivo(texto, vacio):
    """Parte del nombre sin caracteres no válidos en Windows, Drive o adjuntos de correo."""
    limpio = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "-", str(texto)).strip(" .-")
    return limpio or vacio

def nombre_base_archivo():
    estaciones_abrev = {
        "Pintas": "PIN", "Santa Fe": "SFE", "Miravalle": "MIR", "Centro": "CEN",
        "Country": "CTY", "Atemajac": "ATM", "Oblatos": "OBL", "Santa Margarita": "SGM",
        "Vallarta": "VAL", "Loma Dorada": "LDO", "Águilas": "AGU", "Santa Anita": "SAN",
        "Tlaquepaque": "TLA"
    }
    est_cod = estaciones_abrev.get(estacion_sel, "XXX")

    if es_gas: gas_cod = {"Ozono (O3)": "O3", "Óxidos de Nitrógeno (NOx)": "NOx", "Monóxido de Carbono (CO)": "CO", "Dióxido de Azufre (SO2)": "SO2"}.get(gas_sel, "")
    else:
        marca_pm = "BAM" if es_bam else "Thermo"
        gas_cod = f"{pm_tipo}_{marca_pm}"

    # estaciones sin número de serie registrado: se marca en lugar de dejar un segmento vacío ("__")
    serie = _segmento_archivo(num_serie_val, "SIN-NS")
    return f"{año_f}.{mes_f}.{dia_f}_{nomenclatura_tipo}_{gas_cod}_{est_cod}_{serie}_{origen_archivo}"

def nombre_pdf(): return f"{nombre_base_archivo()}.pdf"

col_imprimir, col_pdf, col_drive = st.columns(3, vertical_alignment="center")
mensajes = st.columns(3)[2].container()

with col_imprimir:
    components.html(
        """
        <style>body { margin: 0; }</style>
        <div style="display: flex; align-items: center; justify-content: center; height: 80px;" id="btn-imprimir">
            <button onclick="window.parent.print()" style="padding: 14px 28px; font-size: 16px; font-weight: bold; background-color: #00B2A9; color: white; border: none; border-radius: 8px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
                🖨️ Imprimir / Guardar PDF Visual
            </button>
        </div>
        """, height=80
    )

with col_pdf:
    sin_estacion = estacion_sel == "Selecciona una opción..."
    # El PDF se construye al pulsar el botón (no en cada cambio del formulario) con los datos de esta ejecución
    st.download_button("📄 Descargar PDF del formato", data=b"" if sin_estacion else generar_pdf, file_name=nombre_pdf(),
                       mime="application/pdf", use_container_width=True, disabled=sin_estacion, on_click="ignore",
                       help="Selecciona la Estación para habilitar la descarga" if sin_estacion else None)

def subir_a_drive(servicio, nombre, datos, mimetype, carpeta_id):
    media = MediaIoBaseUpload(io.BytesIO(datos), mimetype=mimetype, resumable=True)
    # create siempre agrega un archivo nuevo: los reportes anteriores con el mismo nombre se conservan
    return servicio.files().create(body={"name": nombre, "parents": [carpeta_id]}, media_body=media, fields="id,webViewLink").execute()

def enviar_correo(servicio, destinatario, asunto, cuerpo, adjuntos):
    mensaje = EmailMessage()
    mensaje["To"], mensaje["Subject"] = destinatario, asunto
    mensaje.set_content(cuerpo)
    for nombre, datos, mimetype in adjuntos:
        tipo, subtipo = mimetype.split("/")
        mensaje.add_attachment(datos, maintype=tipo, subtype=subtipo, filename=nombre)
    crudo = base64.urlsafe_b64encode(mensaje.as_bytes()).decode()
    servicio.users().messages().send(userId="me", body={"raw": crudo}).execute()

with col_drive:
    if st.button("☁️ Respaldar en Drive y enviar al coordinador", use_container_width=True):
        faltan = secrets_faltantes()
        if sin_estacion:
            mensajes.error("⚠️ Falla: Selecciona la Estación de Monitoreo al inicio del formato.")
        elif faltan:
            mensajes.error(f"⚠️ Faltan datos en Secrets: {', '.join(faltan)}")
        else:
            # un solo PDF para Drive y para el correo: ambos reciben exactamente los mismos bytes y el mismo nombre
            pdf_bytes, nombre_del_pdf = generar_pdf(), nombre_pdf()
            enlace = ""
            with mensajes, st.spinner("Subiendo el reporte a Google Drive..."):
                try:
                    servicio_drive = build("drive", "v3", credentials=credenciales_google())
                    pdf_subido = subir_a_drive(servicio_drive, nombre_del_pdf, pdf_bytes, "application/pdf", st.secrets["drive_carpeta_id"])
                    enlace = pdf_subido.get("webViewLink", "")
                    st.success(f"✅ PDF guardado en Drive como: {nombre_del_pdf}")
                except Exception as e:
                    st.error(f"❌ No se pudo guardar en Drive: {error_google(e)}")
            with mensajes, st.spinner("Enviando el PDF al coordinador..."):
                try:
                    servicio_gmail = build("gmail", "v1", credentials=credenciales_google())
                    gas_txt = gas_sel if es_gas else f"{gas_sel} ({pm_tipo})"
                    cuerpo = (f"Buen día,\n\nSe adjunta el formato de calibración de {gas_txt} de la estación {estacion_sel}, "
                              f"con fecha de servicio {fecha_ref}.\n"
                              + (f"\nTambién está respaldado en Drive: {enlace}\n" if enlace else "")
                              + "\nSaludos.")
                    enviar_correo(servicio_gmail, st.secrets["correo_coordinador"],
                                  f"Formato de calibración {gas_txt} - {estacion_sel} - {fecha_ref} - {origen_archivo}", cuerpo,
                                  [(nombre_del_pdf, pdf_bytes, "application/pdf")])
                    st.success("✅ Correo enviado al coordinador.")
                except Exception as e:
                    st.error(f"❌ No se pudo enviar el correo: {error_google(e)}")
