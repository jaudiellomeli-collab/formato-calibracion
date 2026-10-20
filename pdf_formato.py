"""Genera un PDF ligero del formato de calibración, con el mismo aspecto que la página impresa (reportlab, sin navegador)."""
import io
import re
from decimal import Decimal, InvalidOperation
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Circle, Drawing, Group, Line, String
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.platypus import CondPageBreak, HRFlowable, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

MARGEN = 1.0 * cm
ANCHO = letter[0] - 2 * MARGEN
PAD_SEC = 8
ANCHO_INT = ANCHO - 2 * PAD_SEC  # ancho útil de los bloques de cada sección
MARGEN_INF = 1.3 * cm
ALTO_UTIL = letter[1] - MARGEN - MARGEN_INF  # alto del área de contenido de una página

TEAL = colors.HexColor("#00B2A9")
NARANJA = colors.HexColor("#F37021")
TEXTO = colors.HexColor("#31333f")
GRIS_CAJA = colors.HexColor("#f0f2f6")
BORDE_CAJA = colors.HexColor("#9a9a9a")
BORDE_SEC = colors.HexColor("#d0d0d0")
FONDO_ENC = colors.HexColor("#f5f5f5")
LINEA_FILA = colors.HexColor("#e6e6e6")
BARRA = colors.HexColor("#e0e0e0")
BARRA_FIRMA = colors.HexColor("#A6A6A6")
VERDE = colors.HexColor("#dff5e8")
ROJO = colors.HexColor("#f5e3e1")

_base = getSampleStyleSheet()["Normal"]
EST = ParagraphStyle("celda", parent=_base, fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=TEXTO)
EST_C = ParagraphStyle("centro", parent=EST, fontName="Helvetica-Bold", alignment=1)
EST_ENC = ParagraphStyle("enc", parent=EST, fontName="Helvetica-Bold", fontSize=8, leading=10)
EST_TITULO = ParagraphStyle("titulo", parent=_base, fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=colors.black)
EST_NOTA = ParagraphStyle("nota", parent=EST, fontName="Helvetica-Bold", fontSize=8.5, leading=11, spaceBefore=2, spaceAfter=2, leftIndent=PAD_SEC)
EST_ETQ = ParagraphStyle("etiqueta", parent=EST, fontName="Helvetica-Bold", spaceBefore=4, spaceAfter=3, leftIndent=PAD_SEC)
# Caja de texto largo (observaciones, conclusiones): un párrafo con fondo y borde que sí se puede partir entre páginas
EST_TEXTO_LARGO = ParagraphStyle("texto_largo", parent=EST, backColor=GRIS_CAJA, borderColor=BORDE_CAJA, borderWidth=0.6,
                                 borderPadding=(4, 5, 4, 5), leftIndent=PAD_SEC + 5, rightIndent=PAD_SEC + 5, spaceBefore=4, spaceAfter=8)

PAD_TABLA = (3, 3, 2, 2)


class Caja:
    """Campo de captura (caja gris). Con placeholder se muestra en gris cuando está vacío."""
    def __init__(self, valor=None, placeholder=""):
        self.valor, self.placeholder = valor, placeholder


class Alerta:
    """Aviso de resultado: verde si ok es True, rojo si es False; sin texto o ok None no se dibuja."""
    def __init__(self, texto, ok):
        self.texto, self.ok = texto, ok


class Neg:
    """Texto en negritas."""
    def __init__(self, texto):
        self.texto = texto


# Caracteres que Helvetica (WinAnsi) no tiene pero que tienen un equivalente legible
_SUSTITUTOS = str.maketrans({"≤": "<=", "≥": ">=", "≈": "~", "−": "-", "✓": "", "✔": "", "✅": "", "❌": ""})


def _imprimible(c):
    if c in "\n\t":
        return True
    try:
        c.encode("cp1252")
        return True
    except UnicodeEncodeError:
        return False


def _numero(valor):
    """Número tal como se capturó: sin notación científica ni redondeo a 6 cifras."""
    try:
        texto = format(Decimal(repr(valor)), "f")
    except (InvalidOperation, ValueError):
        return str(valor)
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return "0" if texto in ("-0", "") else texto


def limpiar(valor):
    """Texto seguro para Helvetica: sin emojis ni caracteres que la fuente no tenga. Vacío si no hay dato."""
    if valor is None:
        return ""
    if isinstance(valor, float):
        valor = _numero(valor)
    texto = str(valor).translate(_SUSTITUTOS)
    texto = "".join(c for c in texto if _imprimible(c))
    texto = re.sub(r"[ \t]+\n", "\n", texto)
    return texto.strip()


def _html(texto):
    """Escapa el texto para Paragraph conservando los saltos de línea."""
    return escape(limpiar(texto)).replace("\n", "<br/>")


def _par(texto, estilo=EST):
    return Paragraph(_html(texto) or "&nbsp;", estilo)


def _estilo(*extra, pad=(3, 3, 3, 3)):
    izq, der, arr, aba = pad
    return TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), izq),
                       ("RIGHTPADDING", (0, 0), (-1, -1), der), ("TOPPADDING", (0, 0), (-1, -1), arr),
                       ("BOTTOMPADDING", (0, 0), (-1, -1), aba), *extra])


def _caja(c, ancho):
    texto = limpiar(c.valor)
    if texto:
        par = _par(texto)
    elif c.placeholder:
        par = Paragraph(f'<font color="#9a9a9a">{_html(c.placeholder)}</font>', EST)
    else:
        par = _par("")
    t = Table([[par]], colWidths=[ancho], hAlign="LEFT", splitInRow=1)
    t.setStyle(_estilo(("BACKGROUND", (0, 0), (-1, -1), GRIS_CAJA), ("BOX", (0, 0), (-1, -1), 0.6, BORDE_CAJA), pad=(4, 4, 3, 3)))
    return t


def _alerta(a, ancho):
    texto = limpiar(a.texto)
    if not texto or a.ok is None:
        return _par("")
    t = Table([[_par(texto)]], colWidths=[ancho], hAlign="LEFT")
    t.setStyle(_estilo(("BACKGROUND", (0, 0), (-1, -1), VERDE if a.ok else ROJO),
                       ("LINEBEFORE", (0, 0), (0, -1), 1.6, TEAL if a.ok else NARANJA), pad=(6, 4, 3, 3)))
    return t


def _celda(valor, ancho):
    if isinstance(valor, Caja):
        return _caja(valor, ancho)
    if isinstance(valor, Alerta):
        return _alerta(valor, ancho)
    if isinstance(valor, Neg):
        return Paragraph(f"<b>{_html(valor.texto)}</b>", EST)
    return _par(valor)


def _barra(texto, ancho, color=BARRA):
    t = Table([[Paragraph(_html(texto), EST_C)]], colWidths=[ancho])
    t.setStyle(_estilo(("BACKGROUND", (0, 0), (-1, -1), color), ("BOX", (0, 0), (-1, -1), 0.5, BORDE_CAJA), pad=(3, 3, 3, 3)))
    return t


def _tabla(enc, filas, pesos, titulo="", barra=False):
    """Tabla de datos de primer nivel: se divide entre páginas por fila y, si una fila no cabe en una página
    completa, también dentro de la fila. El título y el encabezado son filas de la tabla, así que nunca quedan
    separados de sus datos y se repiten en la página siguiente."""
    n = max(len(f) for f in filas)
    pesos = pesos or [1] * n
    anchos = [ANCHO_INT * p / sum(pesos) for p in pesos]
    datos, extra = [], []
    if titulo:
        datos.append([Paragraph(_html(titulo), EST_C) if barra else Paragraph(f"<b>{_html(titulo)}</b>", EST)] + [""] * (n - 1))
        extra.append(("SPAN", (0, 0), (-1, 0)))
        if barra:
            extra += [("BACKGROUND", (0, 0), (-1, 0), BARRA), ("BOX", (0, 0), (-1, 0), 0.5, BORDE_CAJA)]
    if enc:
        f = len(datos)
        datos.append([Paragraph(f"<b>{_html(h)}</b>", EST) for h in enc])
        extra += [("BACKGROUND", (0, f), (-1, f), FONDO_ENC), ("LINEBELOW", (0, f), (-1, f), 0.6, BORDE_SEC)]
    fijas = len(datos)
    datos += [[_celda(c, anchos[i] - PAD_TABLA[0] - PAD_TABLA[1]) for i, c in enumerate(fila)] for fila in filas]
    if len(datos) - fijas > 1:
        extra.append(("LINEBELOW", (0, fijas), (-1, -2), 0.25, LINEA_FILA))
    t = Table(datos, colWidths=anchos, repeatRows=fijas)
    t.setStyle(_estilo(*extra, pad=PAD_TABLA))
    # Una fila normal pasa completa a la página siguiente; solo una fila más alta que media página (p. ej. una
    # observación muy extensa) se parte dentro de la fila para no provocar un error de maquetación.
    t.wrap(ANCHO_INT, ALTO_UTIL)
    if max(t._rowHeights) > ALTO_UTIL / 2:
        t.splitInRow = 1
    t._divisible = True
    return t


def _campo(etiqueta, valor, ancho):
    if not isinstance(valor, (Caja, Alerta)):
        valor = Caja(valor)
    t = Table([[_par(etiqueta)], [_celda(valor, ancho)]], colWidths=[ancho])
    t.setStyle(_estilo(("TOPPADDING", (0, 0), (-1, 0), 5), ("TOPPADDING", (0, 1), (-1, 1), 1), pad=(0, 0, 0, 1)))
    return t


def _columna(titulo, campos, ancho, firmas):
    filas = []
    if titulo:
        filas.append([_barra(titulo, ancho, BARRA_FIRMA) if firmas else Paragraph(f"<b>{_html(titulo)}</b>", EST)])
    filas += [[_campo(etiqueta, valor, ancho)] for etiqueta, valor in campos]
    if firmas:
        filas.append([_firma(ancho)])
    t = Table(filas, colWidths=[ancho])
    t.setStyle(_estilo(("VALIGN", (0, 0), (-1, -1), "TOP"), pad=(0, 0, 2, 2)))
    return t


def _firma(ancho):
    t = Table([[Paragraph("<b>Firma:</b>", EST), ""]], colWidths=[1.3 * cm, ancho - 1.3 * cm], rowHeights=[1.4 * cm])
    t.setStyle(_estilo(("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LINEBELOW", (1, 0), (1, 0), 0.8, colors.black), pad=(0, 0, 0, 2)))
    return t


def _firmas(grupos):
    """Bloque de firmas en cuadrícula: cada campo ocupa la misma fila en las tres columnas, así etiquetas, datos y
    líneas de firma quedan alineados aunque un dato ocupe varias líneas. Es un solo bloque: nombre, cargo y línea
    de firma no se separan entre páginas."""
    columnas = list(grupos.items())
    ancho = ANCHO_INT / len(columnas)
    interno = ancho - 12
    filas = [[_barra(titulo, interno, BARRA_FIRMA) for titulo, _ in columnas]]
    for i in range(max(len(campos) for _, campos in columnas)):
        filas.append([_campo(*campos[i], interno) if i < len(campos) else "" for _, campos in columnas])
    filas.append([_firma(interno) for _ in columnas])
    t = Table(filas, colWidths=[ancho] * len(columnas), hAlign="CENTER")
    t.setStyle(_estilo(("VALIGN", (0, 0), (-1, -1), "TOP"), pad=(6, 6, 2, 2)))
    return KeepTogether([t])


def _pares(pares, firmas):
    """Campos con etiqueta arriba. Con grupos distintos van en columnas lado a lado; con uno solo, en dos columnas."""
    grupos = {}
    for etiqueta, valor, grupo in pares:
        grupos.setdefault(grupo, []).append((etiqueta, valor))
    if firmas:
        return _firmas(grupos)
    if len(grupos) == 1:
        lista = next(iter(grupos.values()))
        mitad = (len(lista) + 1) // 2
        columnas = [("", c) for c in (lista[:mitad], lista[mitad:]) if c]
    else:
        columnas = list(grupos.items())
    pesos = [1.5 if (i == 0 and not t and len(columnas) >= 3) else 1 for i, (t, _) in enumerate(columnas)]
    anchos = [ANCHO_INT * p / sum(pesos) for p in pesos]
    t = Table([[_columna(titulo, campos, anchos[i] - 12, firmas) for i, (titulo, campos) in enumerate(columnas)]],
              colWidths=anchos, hAlign="CENTER")
    t.setStyle(_estilo(("VALIGN", (0, 0), (-1, -1), "TOP"), pad=(6, 6, 0, 0)))
    return t


def _ajustar(datos, lado_w, lado_h):
    """Image de reportlab que cabe en lado_w x lado_h sin deformar la imagen original."""
    w, h = ImageReader(io.BytesIO(datos)).getSize()
    esc = min(lado_w / w, lado_h / h)
    return Image(io.BytesIO(datos), width=w * esc, height=h * esc)


def _fotos(fotos):
    """Cuadrícula de tres columnas: miniaturas del mismo tamaño y la descripción completa debajo de cada una."""
    ancho_col = ANCHO_INT / 3
    lado = ancho_col - 12
    celdas = []
    for datos, descripcion in fotos:
        try:
            imagen = _ajustar(datos, lado - 2, lado - 2)
        except Exception:  # imagen dañada: se conserva la descripción para no perder la evidencia escrita
            imagen = _par("(imagen no disponible)")
        marco = Table([[imagen]], colWidths=[lado], rowHeights=[lado])  # mismo tamaño para todas las miniaturas
        marco.setStyle(_estilo(("ALIGN", (0, 0), (-1, -1), "CENTER"), ("BOX", (0, 0), (-1, -1), 0.5, BORDE_SEC), pad=(0, 0, 0, 0)))
        celdas.append([marco, Spacer(1, 3), _par(descripcion)])
    bloques = []
    for i in range(0, len(celdas), 3):
        fila = celdas[i:i + 3]
        fila += [""] * (3 - len(fila))
        t = Table([fila], colWidths=[ancho_col] * 3)
        t.setStyle(_estilo(("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER"), pad=(6, 6, 4, 8)))
        bloques.append(t)
    return bloques


def _grafica(datos, descripcion):
    try:
        imagen = _ajustar(datos, ANCHO_INT * 0.8, 9 * cm)
    except Exception:
        return []
    imagen.hAlign = "CENTER"
    return [imagen, Paragraph(_html(descripcion), EST_C), Spacer(1, 4)]


def _grafica_regresion(x, y, m, b, titulo="Regresión Lineal: Calibrador vs Analizador"):
    """Dispersión de puntos y recta ajustada dibujadas con reportlab (no requiere navegador ni kaleido)."""
    ancho, alto = ANCHO_INT * 0.75, 7.5 * cm
    d = Drawing(ancho, alto)
    lp = LinePlot()
    lp.x, lp.y = 50, 32
    lp.width, lp.height = ancho - 70, alto - 72
    x0, x1 = min(x), max(x)
    lp.data = [list(zip(x, y)), [(x0, m * x0 + b), (x1, m * x1 + b)]]
    lp.lines[0].strokeColor = None
    lp.lines[0].symbol = makeMarker("FilledCircle", size=5, fillColor=TEAL, strokeColor=TEAL)
    lp.lines[1].strokeColor = NARANJA
    lp.lines[1].strokeWidth = 1.4
    for eje in (lp.xValueAxis, lp.yValueAxis):
        eje.labels.fontName, eje.labels.fontSize = "Helvetica", 7
        eje.strokeColor = BORDE_CAJA
    lp.xValueAxis.labelTextFormat = lp.yValueAxis.labelTextFormat = lambda v: _numero(round(v, 9))
    lp.yValueAxis.visibleGrid = True
    lp.yValueAxis.gridStrokeColor = LINEA_FILA
    d.add(lp)
    d.add(String(ancho / 2, alto - 12, limpiar(titulo), fontName="Helvetica-Bold", fontSize=8.5, textAnchor="middle", fillColor=TEXTO))
    d.add(String(lp.x + lp.width / 2, 6, "Calibrador", fontName="Helvetica", fontSize=7.5, textAnchor="middle", fillColor=TEXTO))
    # etiqueta del eje Y girada 90°: transform = rotación + traslación al centro del eje
    d.add(Group(String(0, 0, "Analizador", fontName="Helvetica", fontSize=7.5, textAnchor="middle", fillColor=TEXTO),
                transform=(0, 1, -1, 0, 12, lp.y + lp.height / 2)))
    # leyenda
    lx, ly = lp.x + lp.width - 120, alto - 28
    d.add(Circle(lx, ly, 2.5, fillColor=TEAL, strokeColor=TEAL))
    d.add(String(lx + 6, ly - 2.5, "Datos", fontName="Helvetica", fontSize=7, fillColor=TEXTO))
    d.add(Line(lx + 40, ly, lx + 55, ly, strokeColor=NARANJA, strokeWidth=1.4))
    d.add(String(lx + 59, ly - 2.5, "Ajuste lineal", fontName="Helvetica", fontSize=7, fillColor=TEXTO))
    d.hAlign = "CENTER"
    return [d, Spacer(1, 4)]


def _textos(textos):
    salida = []
    for etiqueta, valor, placeholder in textos:
        cuerpo = _html(valor)
        if not cuerpo and placeholder:
            cuerpo = f'<font color="#9a9a9a">{_html(placeholder)}</font>'
        caja = Paragraph(cuerpo or "&nbsp;", EST_TEXTO_LARGO)
        caja._divisible = True
        # la etiqueta solo baja de página si no cabe junto con las primeras líneas del texto
        salida += [CondPageBreak(50), Paragraph(f"<b>{_html(etiqueta)}</b>", EST_ETQ), caja]
    return salida


def _bloques(seccion):
    salida = []
    salida += _textos(seccion.get("textos", []))
    if seccion.get("pares"):
        salida.append(_pares(seccion["pares"], seccion.get("firmas", False)))
    salida += _textos(seccion.get("textos_final", []))
    for nombre, tabla in seccion.get("tablas", {}).items():
        salida.append(_tabla(tabla["enc"], tabla["filas"], tabla.get("pesos"), nombre, tabla.get("barra")))
        salida.append(Spacer(1, 4))
    for nota in seccion.get("notas", []):
        salida.append(Paragraph(_html(nota), EST_NOTA))
    if seccion.get("regresion"):
        salida += _grafica_regresion(**seccion["regresion"])
    for datos, descripcion in seccion.get("graficas", []):
        salida += _grafica(datos, descripcion)
    if seccion.get("fotos"):
        salida += _fotos(seccion["fotos"])
    return salida


def _encabezado_seccion(nombre):
    t = Table([[Paragraph(escape(limpiar(nombre)).upper(), EST_ENC)]], colWidths=[ANCHO])
    t.setStyle(_estilo(("BACKGROUND", (0, 0), (-1, -1), FONDO_ENC), ("BOX", (0, 0), (-1, -1), 0.6, BORDE_SEC),
                       ("LINEBEFORE", (0, 0), (0, -1), 3, TEAL), pad=(PAD_SEC, PAD_SEC, 5, 5)))
    return t


def _logo(ruta):
    """Logo reducido y en JPEG para que el PDF siga siendo ligero."""
    if not ruta:
        return None
    try:
        img = PILImage.open(ruta).convert("RGBA")
    except (OSError, TypeError, ValueError):
        return None
    fondo = PILImage.new("RGB", img.size, "white")
    fondo.paste(img, mask=img.split()[3])
    fondo.thumbnail((420, 420))
    buf = io.BytesIO()
    fondo.save(buf, "JPEG", quality=80, optimize=True)
    ancho = 5.5 * cm
    return Image(io.BytesIO(buf.getvalue()), width=ancho, height=ancho * fondo.height / fondo.width, hAlign="LEFT")


def construir_pdf(titulo, subtitulo, secciones, logo=None):
    """secciones: [(nombre, {"textos": [(etiqueta, valor, placeholder)], "pares": [(etiqueta, valor, grupo)],
    "textos_final": [(etiqueta, valor, placeholder)], "firmas": bool, "tablas": {nombre: {"enc", "filas", "pesos", "barra"}},
    "notas": [texto], "regresion": {"x", "y", "m", "b"}, "graficas": [(bytes_png, descripcion)],
    "fotos": [(bytes_jpeg, descripcion)]})].
    Las celdas pueden ser texto, Caja, Alerta o Neg. Devuelve los bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=MARGEN, rightMargin=MARGEN, topMargin=MARGEN,
                            bottomMargin=MARGEN_INF, title=limpiar(titulo), author="SIMAJ")
    titulo_pie = limpiar(titulo)

    def _pie(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(TEXTO)
        canvas.drawString(MARGEN, 0.6 * cm, titulo_pie)
        canvas.drawRightString(letter[0] - MARGEN, 0.6 * cm, f"Página {doc_.page}")
        canvas.restoreState()

    linea = HRFlowable(width="100%", thickness=2.5, color=colors.HexColor("#e3e6ea"), spaceBefore=2, spaceAfter=4)
    historia = [linea]
    imagen = _logo(logo)
    if imagen:
        historia += [imagen, linea]
    historia += [Paragraph(escape(limpiar(titulo)), EST_TITULO), Paragraph(escape(limpiar(subtitulo)), EST_TITULO), Spacer(1, 6)]
    alto_pagina = ALTO_UTIL
    for nombre, seccion in secciones:
        bloques = _bloques(seccion)
        encabezado = _encabezado_seccion(nombre)
        # evita que el encabezado quede solo al final de una página: pide espacio para él y el inicio del primer bloque
        alto = encabezado.wrap(ANCHO, alto_pagina)[1] + 6
        for b in bloques:
            if isinstance(b, CondPageBreak):
                continue
            h = b.wrap(ANCHO_INT, alto_pagina)[1]
            alto += min(h, 90) if getattr(b, "_divisible", False) else h
            if getattr(b, "style", None) is not EST_ETQ:  # una etiqueta cuenta junto con el texto que la sigue
                break
        historia += [CondPageBreak(min(alto, alto_pagina * 0.9)), encabezado, Spacer(1, 6), *bloques, Spacer(1, 10)]
    doc.build(historia, onFirstPage=_pie, onLaterPages=_pie)
    return buffer.getvalue()
