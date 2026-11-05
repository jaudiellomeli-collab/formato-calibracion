# Instalación en el servidor Ubuntu

Cómo dejar el formato de calibración SIMAJ corriendo en el servidor Ubuntu
(22.04 o 24.04), junto al Validador de Calidad del Aire, el Padrón de
Ladrilleras y Numeralia.

Al terminar queda en:

- **Con dominio:** `https://<dominio>/formato-calibracion/`
- **Sin dominio:** `http://<ip-del-servidor>:8084/`

## Cómo queda armado

```
Internet ──HTTPS──> nginx del servidor ──/formato-calibracion/──> 127.0.0.1:8084 ──> contenedor (Streamlit :8501)
                                                                                      └─ lee .streamlit/secrets.toml (solo lectura)
```

- Un solo contenedor con Streamlit. **No usa MySQL ni guarda nada en disco**:
  borradores, reportes y la base del asistente viven en Google Drive. Se
  puede borrar y reconstruir el contenedor sin perder datos.
- El puerto se publica solo en `127.0.0.1`; nginx es la única entrada desde la
  red.
- Si nginx ya tiene un sitio para el dominio (el del Validador), el formato se
  agrega ahí como carpeta y usa el mismo certificado.

| Puerto | Lo usa |
|---|---|
| 8080 | Tablero de aire |
| 8081 | Validador |
| 8082 | Padrón de Ladrilleras |
| 8083 | Numeralia |
| **8084** | **Formato de calibración** |

## Requisitos

- Un usuario con `sudo` en el servidor.
- Que el servidor pueda bajar el repositorio de GitHub sin pedir contraseña
  (para la actualización automática): una llave de despliegue o
  `git config --global credential.helper store` y un `git pull` hecho a mano.
- Los datos de Google: `client_id`, `client_secret` y `refresh_token` de la
  cuenta que sube a Drive y manda el correo, el ID de la carpeta de Drive y el
  correo del coordinador.
- Si se usa dominio: que ya apunte a la IP del servidor (para el certificado).

## Pasos

### 1. Clonar el repositorio

```bash
cd ~
git clone https://github.com/jaudiellomeli-collab/formato-calibracion.git
cd formato-calibracion
```

### 2. Llenar los secretos

```bash
mkdir -p .streamlit
cp secrets.toml.example .streamlit/secrets.toml
nano .streamlit/secrets.toml
```

Llena `drive_carpeta_id`, `correo_coordinador` y el bloque `[google_oauth]`.
El `refresh_token` se obtiene **una sola vez, en tu computadora** (abre el
navegador para autorizar):

```bash
python obtener_token_google.py client_secret.json
```

Si te saltas este paso el script crea el archivo vacío y avisa. La app abre,
pero no guarda borradores, no sube a Drive ni manda el correo.

### 3. Correr el instalador

Con dominio (lo normal):

```bash
bash scripts/servidor-ubuntu.sh --dominio inspeccionsemadet.jalisco.gob.mx --correo tu@correo.mx
```

Sin dominio, para probar por IP:

```bash
bash scripts/servidor-ubuntu.sh
```

Opciones:

| Opción | Para qué |
|---|---|
| `--dominio <nombre>` | Pone nginx delante con HTTPS (Let's Encrypt). |
| `--correo <correo>` | Correo para los avisos de Let's Encrypt. |
| `--ruta /otra` | Otra carpeta en lugar de `/formato-calibracion`. |
| `--puerto 8090` | Otro puerto si el 8084 está ocupado. |
| `--rama <rama>` | Rama que sigue la actualización automática (por omisión `main`). |
| `--sin-actualizacion` | No instala la actualización automática. |

El script se puede repetir: cada paso revisa qué falta y no rehace lo que ya
está. Lo que hace, en orden:

1. Instala Docker y el plugin compose (repositorio oficial de Docker).
2. Crea `.env` con el puerto (`FORMATO_PUBLICAR`) y la carpeta (`RUTA_BASE`),
   y revisa `.streamlit/secrets.toml`.
3. Activa UFW con SSH, 80 y 443.
4. Compila la imagen, levanta el contenedor y espera a que quede sano.
5. Con `--dominio`: configura nginx y saca el certificado si el sitio aún no
   tiene HTTPS.
6. Instala `formato-actualizar.timer`, que cada 3 minutos revisa GitHub.

### 4. Comprobar

Abre la dirección que imprime el script al final. Debe aparecer
«Selecciona el Tipo de Servicio».

```bash
docker compose ps                 # debe decir (healthy)
docker compose logs -f formato    # bitácora de la app
```

## Actualizaciones

Cada 3 minutos `scripts/actualizar.sh` revisa la rama en GitHub. Si hay
commits nuevos: los baja, recompila, levanta y espera a que quede sano. Si la
versión nueva no levanta, **regresa sola a la anterior** y no la reintenta
hasta que llegue otro commit.

```bash
journalctl -u formato-actualizar -f     # ver qué hizo
bash scripts/actualizar.sh              # forzar una revisión ahora
systemctl list-timers formato-actualizar.timer
```

No edites archivos del repositorio en el servidor: la actualización solo
avanza (`--ff-only`) y se detiene si encuentra cambios locales.

## Tareas comunes

**Cambiar un secreto** (el archivo es del usuario del contenedor, por eso va
con `sudo`):

```bash
sudo nano .streamlit/secrets.toml
docker compose restart formato
```

**Reiniciar / detener / levantar:**

```bash
docker compose restart formato
docker compose down
docker compose up -d
```

**Reconstruir a mano:**

```bash
docker compose up -d --build
```

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| La página se queda en «Please wait...» | nginx no deja pasar el WebSocket. Revisa que `/etc/nginx/snippets/formato-calibracion.conf` tenga `Upgrade` y `Connection "upgrade"` y que el sitio lo incluya: `sudo nginx -t && sudo systemctl reload nginx`. |
| 404 en `/formato-calibracion/` | `RUTA_BASE` en `.env` no coincide con la carpeta de nginx (va sin diagonal: `RUTA_BASE=formato-calibracion`). Corrige y `docker compose up -d`. |
| 502 Bad Gateway | El contenedor no está arriba: `docker compose ps` y `docker compose logs formato`. |
| «Faltan credenciales de Google en Secrets.» o no sube a Drive | `.streamlit/secrets.toml` vacío o con datos mal. Revisa y reinicia. Si el `refresh_token` caducó, vuelve a generarlo con `obtener_token_google.py`. |
| El contenedor no arranca: «is a directory» | No existía `.streamlit/secrets.toml` y Docker creó una carpeta. Bórrala (`sudo rm -r .streamlit/secrets.toml`), copia la plantilla y repite el paso 3. |
| Fotos que no suben | Pesan más de 50 MB (límite de nginx y de Streamlit). |

## Archivos de la instalación

| Archivo | Qué es |
|---|---|
| `Dockerfile` | Imagen de la app (Python 3.12 + Streamlit, usuario sin privilegios). |
| `docker-compose.yml` | El servicio, su puerto y el montaje de los secretos. |
| `secrets.toml.example` | Plantilla de `.streamlit/secrets.toml`. |
| `deploy/nginx/formato-ubicacion.conf` | La carpeta en nginx (WebSocket, tiempos, tamaño de subida). |
| `deploy/nginx/formato.conf` | Sitio propio, solo si el dominio no tiene uno. |
| `scripts/servidor-ubuntu.sh` | Instalador. |
| `scripts/actualizar.sh` | Actualización automática con regreso a la versión anterior. |
| `.env` | Puerto y carpeta. Lo crea el instalador; no se versiona. |
