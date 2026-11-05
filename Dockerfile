# Formato de calibracion SIMAJ - imagen para el servidor Ubuntu.
#
# Un solo contenedor con Streamlit. No guarda nada en disco: los borradores,
# los reportes y la base del asistente viven en Google Drive, asi que se puede
# borrar y reconstruir la imagen sin perder datos.
#
# Los secretos (cuenta de Google, carpeta de Drive, correo del coordinador) NO
# van en la imagen: se montan desde .streamlit/secrets.toml del servidor (ver
# docker-compose.yml).

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=America/Mexico_City

WORKDIR /app

# Las dependencias primero: mientras requirements.txt no cambie, Docker reusa
# esta capa y la reconstruccion tarda segundos. tzdata porque la imagen slim no
# trae las zonas horarias y las fechas del formato van en hora de Guadalajara.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt 'tzdata'

COPY . .

# Sin privilegios. HOME propio porque Streamlit escribe ahi su configuracion.
RUN useradd --create-home --uid 10001 formato \
    && mkdir -p /app/.streamlit \
    && chown -R formato:formato /app
USER formato
ENV HOME=/home/formato

# Configuracion de Streamlit para correr detras de nginx. La carpeta del sitio
# (p. ej. /formato-calibracion) llega en STREAMLIT_SERVER_BASE_URL_PATH desde el
# compose; vacia = la raiz.
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_FILE_WATCHER_TYPE=none \
    STREAMLIT_SERVER_MAX_UPLOAD_SIZE=50

EXPOSE 8501

# /_stcore/health responde «ok» cuando Streamlit ya puede atender. Con carpeta,
# la ruta va debajo de ella.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import os,urllib.request; b=os.environ.get('STREAMLIT_SERVER_BASE_URL_PATH','').strip('/'); urllib.request.urlopen('http://127.0.0.1:8501/'+(b+'/' if b else '')+'_stcore/health', timeout=4)"

CMD ["streamlit", "run", "app.py"]
