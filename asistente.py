"""Sistema experto de dudas del formato de calibración SIMAJ.

Responde con una base de preguntas y respuestas (sin IA de pago): busca la pregunta más parecida a lo que escribió el
técnico ignorando acentos, mayúsculas y errores de escritura. La base inicial está aquí; lo que la coordinación agrega
desde el panel se guarda en Drive y se combina con ella (ver combinar_base)."""
import difflib
import math
import re
import unicodedata

# Cada entrada: id estable, pregunta tal como se muestra, palabras clave o formas en que alguien lo preguntaría, respuesta.
BASE_INICIAL = [
    {"id": "inicio", "pregunta": "¿Cómo empiezo a llenar el formato?",
     "claves": "empezar iniciar llenar formato primer paso como uso app comenzar",
     "respuesta": "1. Elige el tipo de servicio (SIMAJ, Mantenimiento Externo o Diagnóstico de equipo).\n"
                  "2. Si es externo o diagnóstico, indica quién lo realiza (Proveedor o SIMAJ).\n"
                  "3. Elige el equipo y, en partículas, el parámetro (PM10 o PM2.5).\n"
                  "4. Elige la estación (o escribe el N/S en diagnóstico).\n"
                  "5. Escribe tu correo en «Progreso en la Nube» para que tu avance y tus fotos se guarden."},
    {"id": "tipo_servicio", "pregunta": "¿Qué tipo de servicio elijo?",
     "claves": "tipo servicio simaj externo proveedor diagnostico cual elijo opcion",
     "respuesta": "• SIMAJ: mantenimiento que hace el personal de SIMAJ en una estación.\n"
                  "• Mantenimiento Externo: lo hace un proveedor (o SIMAJ como externo) en una estación.\n"
                  "• Diagnóstico de equipo (sin estación): para equipos descompuestos o en laboratorio, que no están en una estación."},
    {"id": "pm_separados", "pregunta": "Hice PM10 y PM2.5 en la misma estación, ¿va en un solo formato?",
     "claves": "pm10 pm25 pm2.5 mismo formato juntos dos parametros misma estacion",
     "respuesta": "No. Cada parámetro es un formato distinto: llena y envía uno para PM10 y otro para PM2.5."},
    {"id": "guardar_avance", "pregunta": "¿Cómo guardo mi avance y lo continúo en otro dispositivo?",
     "claves": "guardar guardo avance borrador lo que llevo continuar seguir despues otro dispositivo celular computadora compu cargar progreso nube",
     "respuesta": "En el panel lateral «Progreso en la Nube» escribe tu correo y pulsa 📥 Guardar. En el otro dispositivo "
                  "elige el mismo servicio, equipo, parámetro y estación (o N/S), escribe el mismo correo y pulsa 📤 Cargar."},
    {"id": "no_carga", "pregunta": "Pulsé Cargar y no aparece lo que guardé",
     "claves": "cargar no aparece mi informacion guardada borrador no encontro perdi lo guardado",
     "respuesta": "Revisa que el tipo de servicio, el equipo, el parámetro y la estación (o el N/S en diagnóstico) sean los mismos "
                  "que cuando guardaste, y que el correo esté escrito exactamente igual. Si no recuerdas el correo, pide a la "
                  "coordinación que lo busque en la carpeta Borradores."},
    {"id": "cambio_equipo", "pregunta": "Cambié de equipo o de servicio y se borró lo que había capturado",
     "claves": "cambie cambio de equipo servicio parametro se borro borraron perdi lo capturado limpio formulario nuevo",
     "respuesta": "Cambiar el tipo de servicio, el equipo o el parámetro inicia un formato nuevo para no mezclar datos. Si habías "
                  "guardado, vuelve a elegir lo de antes y pulsa 📤 Cargar. Guarda siempre antes de cambiar."},
    {"id": "fotos_guardar", "pregunta": "¿Las fotos se guardan?",
     "claves": "fotos imagenes evidencias se guardan pierden recargar subir guardar donde poner agregar",
     "respuesta": "Sí. Con tu correo escrito en «Progreso en la Nube», cada foto que subes, quitas o describes se guarda sola en "
                  "tu borrador. Escribe el correo antes de subir fotos: sin correo se pierden si se recarga la página. "
                  "Se aceptan JPG y PNG; no hace falta girarlas ni recortarlas."},
    {"id": "fotos_quitar", "pregunta": "¿Cómo quito una foto que subí por error?",
     "claves": "quitar borrar eliminar foto imagen error equivocada",
     "respuesta": "En «Fotos guardadas en tu borrador», pulsa 🗑️ Quitar debajo de la foto. Si todavía está en el selector de "
                  "archivos, quítala con la X junto a su nombre."},
    {"id": "boton_gris", "pregunta": "¿Por qué no puedo descargar ni enviar el formato? El botón está gris",
     "claves": "boton gris bloqueado no puedo no deja descargar pdf deshabilitado obligatorio falta campo",
     "respuesta": "Falta algún dato obligatorio. Arriba de los botones aparece la lista: nombres del técnico, de quien supervisa y "
                  "del supervisor SEMADET, Observaciones Generales y Conclusiones. En diagnóstico también N/S, falla reportada, "
                  "falla encontrada, si queda funcionando y el motivo."},
    {"id": "no_cumple", "pregunta": "Un valor me sale NO CUMPLE, ¿qué hago?",
     "claves": "no cumple rojo fuera de rango valor mal que hago",
     "respuesta": "No lo cambies para que pase. Captura la lectura real tal como aparece en el equipo y explica en Observaciones "
                  "Generales qué hiciste o qué falta. La columna Comentarios la llena el formato solo con Cumple o NO CUMPLE."},
    {"id": "aviso_amarillo", "pregunta": "¿Qué significa el aviso amarillo junto a un valor?",
     "claves": "aviso amarillo advertencia valor raro revisa fuera normal",
     "respuesta": "Que el valor está fuera de lo normal para la zona (por ejemplo, presión ambiental fuera de 600–680 Torr) o que "
                  "las fechas u horas no cuadran. No bloquea el formato: revisa que lo capturaste bien y corrígelo si fue un error."},
    {"id": "valor_no_aparece", "pregunta": "El equipo no tiene o no muestra un dato, ¿qué hago?",
     "claves": "no encuentro valor dato pantalla equipo no aparece no tiene no muestra parametro falta lectura",
     "respuesta": "No lo inventes. Déjalo vacío y explícalo en Observaciones Generales."},
    {"id": "valores_pantalla", "pregunta": "¿De dónde saco los valores de los parámetros?",
     "claves": "valores parametros donde saco lectura pantalla equipo inicial final",
     "respuesta": "Cópialos tal como aparecen en la pantalla del analizador: el valor Inicial cuando llegas y el Final cuando "
                  "terminas. La coordinación revisa que coincidan con la pantalla (por ejemplo, la Presión sobre filtro del BAM)."},
    {"id": "presion_ambiental", "pregunta": "¿Qué valor pongo en la presión ambiental?",
     "claves": "presion ambiental unica torr barometrica valor normal",
     "respuesta": "La presión ambiental medida en la estación, en Torr. En la zona metropolitana de Guadalajara suele estar cerca "
                  "de 630–650 Torr; el formato avisa si escribes algo fuera de 600–680 Torr."},
    {"id": "bam_vacios", "pregunta": "¿Qué parámetros del BAM se quedan vacíos con más frecuencia?",
     "claves": "bam traza heater temperatura traza presion vacio muestra filtro vacios faltan",
     "respuesta": "• Presión sobre filtro (AP): 0 – 500 mmHg.\n• Presión de vacío de la muestra: -5 a 250 mmHg.\n"
                  "• Traza (Heater): 1 – 99 °C.\nCaptura siempre el valor inicial y el final."},
    {"id": "bam_flujo", "pregunta": "¿Cómo se hace la verificación y el ajuste de flujo del BAM?",
     "claves": "bam flujo verificacion ajuste 16.67 lpm tres puntos 15 18.43 promedio dar medir mide marcar valor",
     "respuesta": "Verificación: el calibrador está en 16.67 lpm y capturas la lectura del monitor; debe estar entre 16.00 y "
                  "17.34 lpm. Si no cumple, aparece el Ajuste de flujo: captura el monitor en 15.0, 18.43 y 16.67 lpm; el "
                  "promedio debe quedar entre 16.00 y 17.34."},
    {"id": "bam_membrana", "pregunta": "¿Cómo lleno la membrana span del BAM?",
     "claves": "bam membrana span i1 i2 zero count span count measured mass expected foils error 5",
     "respuesta": "Captura Zero Count (I1), Span Count (I2) y Measured Mass. En Valor Ideal va el Expected Span Membrane del "
                  "certificado de fábrica del equipo (usualmente 0.8000 mg/cm²). El % de error debe ser menor a ±5%."},
    {"id": "thermo_sensores", "pregunta": "¿Cuáles son los criterios del Thermo para sensores y flujo?",
     "claves": "thermo 5014i sensores temperatura humedad diferencia 2 barometrica flujo automatico manual",
     "respuesta": "• Temperatura ambiente, humedad relativa y temperatura de flujo: la diferencia del promedio debe ser menor a ±2.\n"
                  "• Presión barométrica: menor a ±10 mmHg en la lectura y ±2 mmHg después de calibrar.\n"
                  "• Flujo automático y manual: entre 16.00 y 17.34 Lpm."},
    {"id": "gases_flujo", "pregunta": "¿Cuál es la tolerancia del flujo volumétrico en gases?",
     "claves": "gases flujo volumetrico tolerancia o3 ozono nox co so2 ajuste cc min",
     "respuesta": "• O3: 500 cc/min ± 2.5%.\n• NOx: 650 cc/min ± 5%.\n• CO: 1000 cc/min ± 2.5%.\n"
                  "• SO2: ± 2.5% sobre 700 (Ecotech), 750 (Acoem) o 500 (ML) cc/min.\nSi sale fuera, aparece la tabla de Ajuste."},
    {"id": "cero_span", "pregunta": "¿Cuál es el criterio de la verificación cero-span?",
     "claves": "cero span criterio respuesta tolerancia 3 por ciento ganancia zero offset",
     "respuesta": "Span: la respuesta debe quedar dentro de ±3% del valor generado. Cero: la diferencia debe estar dentro de "
                  "±0.003 ppm (±0.5 ppm en CO). Registra también ganancia y zero offset inicial y final."},
    {"id": "multipunto", "pregunta": "¿Cuándo se aprueba la calibración multipunto?",
     "claves": "multipunto aprobado rechazado pendiente intercepto r2 regresion 5 puntos",
     "respuesta": "Se capturan los 5 puntos. Se aprueba con pendiente (m) entre 0.98 y 1.02, intercepto (b) dentro de ±0.02 "
                  "(±2 en CO) y R² mayor a 0.99. Si no, revisa fugas o el depurador antes de repetir."},
    {"id": "o3_pot", "pregunta": "¿Qué valor debe tener el Pot de la lámpara UV del ozono?",
     "claves": "pot lampara uv ozono o3 255 254 potenciometro",
     "respuesta": "255. Es el criterio del formato para el Pot de la lámpara UV en O3."},
    {"id": "decimales", "pregunta": "¿Cuántos decimales lleva cada valor?",
     "claves": "decimales cuatro 4 formato numeros 0.4000",
     "respuesta": "Todas las cantidades llevan 4 decimales (por ejemplo 0.4000). Los porcentajes llevan 2 y los conteos enteros "
                  "(I1, I2) ninguno."},
    {"id": "calibrador_vacio", "pregunta": "¿Por qué los datos del calibrador vienen vacíos?",
     "claves": "calibrador datos vacios certificado laboratorio marca modelo proveedor",
     "respuesta": "En mantenimiento externo o de proveedor vienen vacíos a propósito: llena los datos de tu calibrador (marca, "
                  "modelo, N/S, laboratorio, fecha y número de certificado)."},
    {"id": "conclusiones", "pregunta": "¿Cómo escribo las conclusiones?",
     "claves": "conclusiones como escribo redactar observacion concluido pendiente en observacion",
     "respuesta": "Di claramente si el servicio terminó. Ejemplo: «Mantenimiento concluido. El equipo queda operando dentro de "
                  "especificaciones». Si falta algo: «Mantenimiento pendiente: falta reemplazar la bomba; se instalará el "
                  "28/10/2026». No basta con «se mantiene en observación»."},
    {"id": "diagnostico", "pregunta": "¿Cuándo uso el formato de diagnóstico y cómo se llena?",
     "claves": "diagnostico sin estacion descompuesto laboratorio falla pruebas queda funcionando thermo",
     "respuesta": "Para equipos que no están en una estación (descompuestos o en laboratorio). Escribe el N/S del equipo, la "
                  "falla reportada y la encontrada, registra cada prueba con su resultado (Normal/Anormal) y al final indica "
                  "si queda funcionando, el motivo y las refacciones requeridas. Por ahora es solo para PM Thermo."},
    {"id": "enviar", "pregunta": "¿Cómo entrego el formato terminado?",
     "claves": "entregar enviar mandar mando terminar terminado formato coordinador drive whatsapp grupo pdf",
     "respuesta": "1. Pulsa 📄 Descargar PDF y revísalo.\n2. Pulsa ☁️ Respaldar en Drive y enviar al coordinador y espera los dos "
                  "mensajes verdes.\n3. Envía el PDF por el grupo de WhatsApp de Mantenimiento SIMAJ: así se considera concluido."},
    {"id": "mensaje_rojo", "pregunta": "Al enviar me salió un mensaje rojo",
     "claves": "mensaje rojo error enviar drive correo fallo no se envio",
     "respuesta": "El envío no se completó. Toma captura del mensaje, mándala al grupo y envía el PDF descargado por WhatsApp "
                  "para no retrasar la entrega."},
    {"id": "corregir_enviado", "pregunta": "Me equivoqué después de enviar el formato",
     "claves": "equivoque error despues enviar corregir reenviar version corregida",
     "respuesta": "Corrige el formato y vuelve a enviarlo por el grupo indicando que es la versión corregida. La anterior no se "
                  "borra de Drive."},
    {"id": "imprimir", "pregunta": "¿Cuál es la diferencia entre Imprimir y Descargar PDF?",
     "claves": "imprimir descargar pdf visual diferencia cual uso",
     "respuesta": "📄 Descargar PDF genera el reporte oficial, ordenado y con fotos; es el que se entrega. 🖨️ Imprimir guarda la "
                  "página tal como se ve en el navegador."},
]

# Palabras que no ayudan a distinguir una pregunta de otra
_VACIAS = set("""a al algo como con cual cuales cuando de del donde el ella en es esa ese eso esta este esto hay la las le lo
los me mi mis no o para pero por porque que se si sin su sus te tengo tiene un una uno y ya yo hago hacer debo puedo pongo
va van lleva llevan quien q k ayer hoy mañana manana dia oye hola gracias favor cuanto cuantos cuanta cuantas cada debe deben tiene tienen""".split())
# Sinónimos frecuentes: se reemplazan por una forma común antes de buscar
_SINONIMOS = {"imagen": "foto", "imagenes": "foto", "evidencia": "foto", "evidencias": "foto", "fotografia": "foto",
              "fotografias": "foto", "pm25": "pm2.5", "descompuesto": "diagnostico", "averiado": "diagnostico",
              "ozono": "o3", "monoxido": "co", "dioxido": "so2", "oxidos": "nox", "borrador": "avance",
              "progreso": "avance", "bloqueado": "gris", "deshabilitado": "gris", "rojo": "no cumple"}


def normalizar(texto):
    texto = unicodedata.normalize("NFD", str(texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9.%±]+", " ", texto).strip()


_SUFIJOS = ("amiento", "imiento", "aciones", "acion", "ando", "iendo", "ados", "idos", "ado", "ido",
            "ar", "er", "ir", "as", "es", "os", "an", "en", "a", "o", "e", "s")


def _raiz(palabra):
    """Raíz simple en español: plural, género y conjugaciones comunes cuentan como la misma palabra
    (fotos/foto, guardo/guardar/guardado, cambia/cambio)."""
    for sufijo in _SUFIJOS:
        if palabra.endswith(sufijo) and len(palabra) - len(sufijo) >= 4:
            return palabra[: -len(sufijo)]
    return palabra


def palabras(texto):
    salida = []
    for p in normalizar(texto).split():
        p = _SINONIMOS.get(p, p)
        for q in p.split():
            if q not in _VACIAS and len(q) > 1:
                salida.append(_raiz(q.strip(".")) if not re.match(r"^[\d.]+$", q) else q)
    return salida


def combinar_base(extra):
    """Base inicial + lo agregado desde el panel. extra = {"agregadas": [...], "eliminadas": [ids]}."""
    extra = extra or {}
    eliminadas = set(extra.get("eliminadas", []))
    agregadas = {e["id"]: e for e in extra.get("agregadas", [])}
    base = [agregadas.pop(e["id"], e) for e in BASE_INICIAL if e["id"] not in eliminadas]  # una agregada con el mismo id la reemplaza
    return base + [e for e in agregadas.values() if e["id"] not in eliminadas]


def buscar(pregunta, base, limite=3):
    """Devuelve [(confianza 0-1, entrada)] de las entradas más parecidas, de mayor a menor.

    La confianza es qué parte de lo importante de la pregunta cubre esa entrada: cada palabra pesa según qué tan
    distintiva es (IDF) y las palabras que la base no conoce pesan lo máximo, así que una pregunta sobre algo que no
    está en la base no alcanza el umbral aunque comparta una palabra común."""
    consulta = list(dict.fromkeys(palabras(pregunta)))
    if not consulta or not base:
        return []
    docs = [set(palabras(f"{e['pregunta']} {e.get('claves', '')}")) | set(palabras(e.get("respuesta", ""))[:25]) for e in base]
    vocabulario = sorted(set().union(*docs))
    n = len(docs)

    def idf(p):
        df = sum(1 for d in docs if p in d)
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    idf_max = math.log(1 + (n + 0.5) / 0.5)
    # cada palabra de la consulta: (palabra de la base con la que coincide o None, peso)
    terminos = []
    for p in consulta:
        if p in vocabulario:
            terminos.append((p, idf(p)))
            continue
        cerca = [c for c in difflib.get_close_matches(p, vocabulario, n=3, cutoff=0.82) if abs(len(c) - len(p)) <= 1] if len(p) >= 4 else []
        # tolerancia a errores de escritura ("menbrana" -> "membrana"); si no se reconoce, la palabra cuenta en contra
        terminos.append((cerca[0], idf(cerca[0]) * 0.8) if cerca else (None, idf_max))
    total = sum(w for _, w in terminos)
    resultados = []
    for e, d in zip(base, docs):
        cubierto = sum(w for p, w in terminos if p and p in d)
        if not cubierto:
            continue
        parecido = difflib.SequenceMatcher(None, normalizar(pregunta), normalizar(e["pregunta"])).ratio()
        resultados.append((min(1.0, cubierto / total * (0.85 + 0.3 * parecido)), e))
    resultados.sort(key=lambda x: x[0], reverse=True)
    return resultados[:limite]


UMBRAL_CONFIANZA = 0.45  # debajo de esto el asistente dice que no sabe y registra la pregunta para la coordinación
