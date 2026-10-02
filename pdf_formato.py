"""Genera un PDF ligero del formato de calibración, con el mismo aspecto que la página impresa (reportlab, sin navegador)."""
import io
import re
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import CondPageBreak, HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

MARGEN = 1.0 * cm
ANCHO = letter[0] - 2 * MARGEN
PAD_SEC = 8
ANCHO_INT = ANCHO - 2 * PAD_SEC  # ancho útil dentro del recuadro de cada sección

TEAL = colors.HexColor("#00B2A9")
TEXTO = colors.HexColor("#31333f")
GRIS_CAJA = colors.HexColor("#f0f2f6")
BORDE_CAJA = colors.HexColor("#9a9a9a")
BORDE_SEC = colors.HexColor("#d0d0d0")
FONDO_ENC = colors.HexColor("#f5f5f5")
BARRA = colors.HexColor("#e0e0e0")
BARRA_FIRMA = colors.HexColor("#A6A6A6")
VERDE = colors.HexColor("#dff5e8")
ROJO = colors.HexColor("#f5e3e1")

_base = getSampleStyleSheet()["Normal"]
EST = ParagraphStyle("celda", parent=_base, fontName="Helvetica", fontSize=7.5, leading=9, textColor=TEXTO)
EST_C = ParagraphStyle("centro", parent=EST, fontName="Helvetica-Bold", alignment=1)
EST_ENC = ParagraphStyle("enc", parent=EST, fontSize=7.5, leading=9)
EST_TITULO = ParagraphStyle("titulo", parent=_base, fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=colors.black)
EST_NOTA = ParagraphStyle("nota", parent=EST, fontName="Helvetica-Bold", fontSize=8.5, leading=11)


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


def limpiar(valor):
    """Texto seguro para Helvetica: sin emojis ni caracteres fuera de latin-1. Vacío si no hay dato."""
    if valor is None:
        return ""
    if isinstance(valor, float):
        valor = f"{valor:g}"
    return re.sub(r"[^\x00-\xff]", "", str(valor)).strip()


def _par(texto, estilo=EST):
    return Paragraph(escape(limpiar(texto)).replace("\n", "<br/>") or "&nbsp;", estilo)


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
        par = Paragraph(f'<font color="#9a9a9a">{escape(limpiar(c.placeholder))}</font>', EST)
    else:
        par = _par("")
    t = Table([[par]], colWidths=[ancho], hAlign="LEFT")
    t.setStyle(_estilo(("BACKGROUND", (0, 0), (-1, -1), GRIS_CAJA), ("BOX", (0, 0), (-1, -1), 0.6, BORDE_CAJA), pad=(4, 4, 3, 3)))
    return t


def _alerta(a, ancho):
    texto = limpiar(a.texto)
    if not texto or a.ok is None:
        return _par("")
    t = Table([[_par(texto)]], colWidths=[ancho], hAlign="LEFT")
    t.setStyle(_estilo(("BACKGROUND", (0, 0), (-1, -1), VERDE if a.ok else ROJO), ("LINEBEFORE", (0, 0), (0, -1), 1.6, TEAL), pad=(6, 4, 3, 3)))
    return t


def _celda(valor, ancho):
    if isinstance(valor, Caja):
        return _caja(valor, ancho)
    if isinstance(valor, Alerta):
        return _alerta(valor, ancho)
    if isinstance(valor, Neg):
        return Paragraph(f"<b>{escape(limpiar(valor.texto))}</b>", EST)
    return _par(valor)


def _barra(texto, ancho, color=BARRA):
    t = Table([[Paragraph(escape(limpiar(texto)), EST_C)]], colWidths=[ancho])
    t.setStyle(_estilo(("BACKGROUND", (0, 0), (-1, -1), color), ("BOX", (0, 0), (-1, -1), 0.5, BORDE_CAJA), pad=(3, 3, 3, 3)))
    return t


def _tabla(enc, filas, pesos):
    n = len(filas[0])
    pesos = pesos or [1] * n
    anchos = [ANCHO_INT * p / sum(pesos) for p in pesos]
    datos = [[Paragraph(f"<b>{escape(limpiar(h))}</b>", EST) for h in enc]] if enc else []
    datos += [[_celda(c, anchos[i] - 6) for i, c in enumerate(fila)] for fila in filas]
    t = Table(datos, colWidths=anchos, repeatRows=1 if enc else 0)
    t.setStyle(_estilo(pad=(3, 3, 2, 2)))
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
        filas.append([_barra(titulo, ancho, BARRA_FIRMA) if firmas else Paragraph(f"<b>{escape(limpiar(titulo))}</b>", EST)])
    filas += [[_campo(etiqueta, valor, ancho)] for etiqueta, valor in campos]
    if firmas:
        filas.append([_firma(ancho)])
    t = Table(filas, colWidths=[ancho])
    t.setStyle(_estilo(pad=(0, 0, 2, 2)))
    return t


def _firma(ancho):
    t = Table([[Paragraph("<b>Firma:</b>", EST), ""]], colWidths=[1.3 * cm, ancho - 1.3 * cm], rowHeights=[1.4 * cm])
    t.setStyle(_estilo(("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LINEBELOW", (1, 0), (1, 0), 0.8, colors.black), pad=(0, 0, 0, 2)))
    return t


def _pares(pares, firmas):
    """Campos con etiqueta arriba. Con grupos distintos van en columnas lado a lado; con uno solo, en dos columnas."""
    grupos = {}
    for etiqueta, valor, grupo in pares:
        grupos.setdefault(grupo, []).append((etiqueta, valor))
    if len(grupos) == 1:
        lista = next(iter(grupos.values()))
        mitad = (len(lista) + 1) // 2
        columnas = [("", c) for c in (lista[:mitad], lista[mitad:]) if c]
    else:
        columnas = list(grupos.items())
    pesos = [1.5 if (i == 0 and not t and len(columnas) >= 3) else 1 for i, (t, _) in enumerate(columnas)]
    anchos = [ANCHO_INT * p / sum(pesos) for p in pesos]
    t = Table([[_columna(titulo, campos, anchos[i] - 12, firmas) for i, (titulo, campos) in enumerate(columnas)]],
              colWidths=anchos, hAlign="LEFT")
    t.setStyle(_estilo(("VALIGN", (0, 0), (-1, -1), "TOP"), pad=(6, 6, 0, 0)))
    return t


def _fotos(fotos):
    ancho = ANCHO_INT / 3 - 10
    celdas = []
    for datos, descripcion in fotos:
        w, h = ImageReader(io.BytesIO(datos)).getSize()
        celdas.append([Image(io.BytesIO(datos), width=ancho, height=ancho * h / w), _par(descripcion)])
    bloques = []
    for i in range(0, len(celdas), 3):
        fila = celdas[i:i + 3]
        fila += [""] * (3 - len(fila))
        t = Table([fila], colWidths=[ANCHO_INT / 3] * 3)
        t.setStyle(_estilo(("VALIGN", (0, 0), (-1, -1), "TOP")))
        bloques.append(t)
    return bloques


def _bloques(seccion):
    salida = []
    for etiqueta, valor, placeholder in seccion.get("textos", []):
        salida.append(Paragraph(f"<b>{escape(limpiar(etiqueta))}</b>", EST))
        salida.append(_caja(Caja(valor, placeholder), ANCHO_INT - 6))
    if seccion.get("pares"):
        salida.append(_pares(seccion["pares"], seccion.get("firmas", False)))
    for nombre, tabla in seccion.get("tablas", {}).items():
        cuerpo = _tabla(tabla["enc"], tabla["filas"], tabla.get("pesos"))
        if nombre:  # el título va en el mismo bloque que su tabla para que no se separen entre páginas
            titulo = _barra(nombre, ANCHO_INT) if tabla.get("barra") else Paragraph(f"<b>{escape(limpiar(nombre))}</b>", EST)
            cuerpo = Table([[titulo], [cuerpo]], colWidths=[ANCHO_INT])
            cuerpo.setStyle(_estilo(pad=(0, 0, 1, 1)))
        salida.append(cuerpo)
    for nota in seccion.get("notas", []):
        salida.append(Paragraph(escape(limpiar(nota)), EST_NOTA))
    if seccion.get("fotos"):
        salida += _fotos(seccion["fotos"])
    return salida


def _seccion(nombre, bloques):
    """Recuadro con encabezado gris y los bloques de la sección, como los expanders de la página."""
    filas = [[Paragraph(escape(limpiar(nombre)).upper(), EST_ENC)]] + [[b] for b in bloques]
    t = Table(filas, colWidths=[ANCHO])
    estilo = [("BOX", (0, 0), (-1, -1), 0.6, BORDE_SEC), ("BACKGROUND", (0, 0), (-1, 0), FONDO_ENC),
              ("LINEBELOW", (0, 0), (-1, 0), 0.6, BORDE_SEC), ("LEFTPADDING", (0, 0), (-1, -1), PAD_SEC),
              ("RIGHTPADDING", (0, 0), (-1, -1), PAD_SEC), ("TOPPADDING", (0, 0), (-1, 0), 5),
              ("BOTTOMPADDING", (0, 0), (-1, 0), 5)]
    if bloques:
        estilo += [("TOPPADDING", (0, 1), (-1, -1), 3), ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
                   ("TOPPADDING", (0, 1), (-1, 1), 8), ("BOTTOMPADDING", (0, -1), (-1, -1), 8)]
    t.setStyle(TableStyle(estilo))
    return t


def _logo(ruta):
    """Logo reducido y en JPEG para que el PDF siga siendo ligero."""
    try:
        img = PILImage.open(ruta).convert("RGBA")
    except (OSError, TypeError):
        return None
    fondo = PILImage.new("RGB", img.size, "white")
    fondo.paste(img, mask=img.split()[3])
    fondo.thumbnail((420, 420))
    buf = io.BytesIO()
    fondo.save(buf, "JPEG", quality=80, optimize=True)
    ancho = 5.5 * cm
    return Image(io.BytesIO(buf.getvalue()), width=ancho, height=ancho * fondo.height / fondo.width, hAlign="LEFT")


def _pie(canvas, doc):
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(letter[0] - MARGEN, 0.6 * cm, f"Página {doc.page}")


def construir_pdf(titulo, subtitulo, secciones, logo=None):
    """secciones: [(nombre, {"textos": [(etiqueta, valor, placeholder)], "pares": [(etiqueta, valor, grupo)],
    "firmas": bool, "tablas": {nombre: {"enc", "filas", "pesos", "barra"}}, "notas": [texto],
    "fotos": [(bytes_jpeg, descripcion)]})]. Las celdas pueden ser texto, Caja, Alerta o Neg. Devuelve los bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=MARGEN, rightMargin=MARGEN, topMargin=MARGEN,
                            bottomMargin=1.3 * cm, title=limpiar(titulo), author="SIMAJ")
    linea = HRFlowable(width="100%", thickness=2.5, color=colors.HexColor("#e3e6ea"), spaceBefore=2, spaceAfter=4)
    historia = [linea]
    imagen = _logo(logo)
    if imagen:
        historia += [imagen, linea]
    historia += [Paragraph(escape(limpiar(titulo)), EST_TITULO), Paragraph(escape(limpiar(subtitulo)), EST_TITULO), Spacer(1, 6)]
    alto_pagina = letter[1] - 2 * MARGEN
    for nombre, seccion in secciones:
        bloques = _bloques(seccion)
        # evita que el encabezado quede solo al final de una página, separado de su primer bloque
        primero = bloques[0].wrap(ANCHO_INT, alto_pagina)[1] if bloques else 0
        historia += [CondPageBreak(min(primero + 50, alto_pagina)), _seccion(nombre, bloques), Spacer(1, 8)]
    doc.build(historia, onFirstPage=_pie, onLaterPages=_pie)
    return buffer.getvalue()
