#!/usr/bin/env bash
# Instala y arranca el formato de calibracion SIMAJ en un servidor Ubuntu (22.04 o 24.04).
#
#   bash scripts/servidor-ubuntu.sh --dominio inspeccionsemadet.jalisco.gob.mx --correo tu@correo.mx
#   bash scripts/servidor-ubuntu.sh --dominio ... --ruta /calibracion   # otra carpeta (por omision /formato-calibracion)
#   bash scripts/servidor-ubuntu.sh                                     # sin dominio: http://<servidor>:8084
#   bash scripts/servidor-ubuntu.sh --puerto 8090                       # otro puerto si el 8084 esta ocupado
#   bash scripts/servidor-ubuntu.sh --sin-actualizacion                 # sin el paso 6
#
# Se corre con un usuario que tenga sudo, desde el repositorio ya clonado. Se
# puede repetir: cada paso revisa que falta y no rehace lo que ya esta.
#
# Pensado para convivir con el Validador y el Padron de Ladrilleras en el mismo
# servidor: si nginx ya tiene un sitio para el dominio, el formato se agrega a
# el como carpeta en lugar de crear otro. No usa MySQL: todo vive en Drive.
#
# Que hace:
#   1. Docker Engine y el plugin compose, del repositorio oficial de Docker.
#   2. .env (puerto y carpeta) y .streamlit/secrets.toml (llaves de Google).
#      Si los secretos estan vacios, avisa: la app abre pero no guarda en Drive.
#   3. UFW: SSH y la web. Lo activa.
#   4. Compila la imagen y levanta el contenedor.
#   5. Con --dominio: nginx delante y certificado de Let's Encrypt (certbot).
#   6. Actualizacion automatica: cada 3 minutos revisa la rama en GitHub y, si
#      hay cambios, los baja y recompila (scripts/actualizar.sh).

set -euo pipefail
trap 'echo "!! Fallo la linea $LINENO: $BASH_COMMAND" >&2' ERR

DOMINIO=""
CORREO=""
RUTA=/formato-calibracion
PUERTO=8084
RAMA=main
ACTUALIZACION=si
while [ $# -gt 0 ]; do
  case "$1" in
    --dominio) DOMINIO="${2:?falta el dominio}"; shift 2 ;;
    --correo)  CORREO="${2:?falta el correo}"; shift 2 ;;
    --ruta)    RUTA="${2:?falta la carpeta}"; shift 2 ;;
    --puerto)  PUERTO="${2:?falta el puerto}"; shift 2 ;;
    --rama)    RAMA="${2:?falta la rama}"; shift 2 ;;
    --sin-actualizacion) ACTUALIZACION=no; shift ;;
    -h|--help) sed -n '2,/^$/p' "$0"; exit 0 ;;
    *) echo "Opcion desconocida: $1" >&2; exit 1 ;;
  esac
done

cd "$(dirname "$0")/.."

paso() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
aviso() { printf '\033[33m!! %s\033[0m\n' "$*"; }

. /etc/os-release
if [ "${ID:-}" != "ubuntu" ]; then
  echo "Este script es para Ubuntu (encontre: ${PRETTY_NAME:-desconocido})." >&2
  exit 1
fi

# /carpeta con letras, digitos, _ y -. Sin dominio no hay nginx: va en la raiz.
if [ -n "$DOMINIO" ]; then
  RUTA="/$(printf '%s' "$RUTA" | sed -E 's|^/+||; s|/+$||')"
  if ! printf '%s' "$RUTA" | grep -qE '^/[A-Za-z0-9_-]+(/[A-Za-z0-9_-]+)*$'; then
    echo "--ruta debe ser una carpeta como /formato-calibracion (llego: $RUTA)." >&2
    exit 1
  fi
else
  RUTA=""
fi

# --- 1. Docker ----------------------------------------------------------------
paso "Docker"
if sudo docker compose version >/dev/null 2>&1; then
  echo "Ya instalado: $(sudo docker --version)"
else
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable --now docker
fi
# El dueno del repositorio entra al grupo docker: lo necesita la actualizacion
# automatica (paso 6), que corre como el.
DUENO=$(stat -c %U .)
id -nG "$DUENO" | grep -qw docker || sudo usermod -aG docker "$DUENO"

# --- 2. Configuracion ---------------------------------------------------------
paso "Configuracion (.env y secretos)"

poner() {
  VALOR="$2" awk -v k="$1" 'BEGIN { v = ENVIRON["VALOR"] }
    index($0, k "=") == 1 { print k "=" v; hecho = 1; next }
    { print }
    END { if (!hecho) print k "=" v }' .env > .env.nuevo
  cat .env.nuevo > .env && rm .env.nuevo
}
valor() { sed -n "s|^$1=||p" .env | tail -n1; }

if [ -n "$DOMINIO" ]; then PUBLICAR="127.0.0.1:$PUERTO"; else PUBLICAR="$PUERTO"; fi

if [ ! -f .env ]; then
  : > .env
  chmod 600 .env
  poner FORMATO_PUBLICAR "$PUBLICAR"
  # Streamlit la quiere sin diagonales: formato-calibracion.
  poner RUTA_BASE "${RUTA#/}"
  echo "Creado .env."
else
  echo ".env ya existe; solo agrego lo que le falte."
  grep -q '^FORMATO_PUBLICAR=' .env || poner FORMATO_PUBLICAR "$PUBLICAR"
  grep -q '^RUTA_BASE=' .env || poner RUTA_BASE "${RUTA#/}"
fi
if [ -n "$DOMINIO" ]; then
  [ "$(valor RUTA_BASE)" = "${RUTA#/}" ] \
    || aviso "RUTA_BASE en .env es \"$(valor RUTA_BASE)\" y nginx servira \"$RUTA\". Deben coincidir (sin la diagonal inicial)."
  case "$(valor FORMATO_PUBLICAR)" in
    127.0.0.1:*) ;;
    *) aviso "Con nginx delante conviene FORMATO_PUBLICAR=127.0.0.1:$PUERTO en .env; si no, el puerto queda abierto sin HTTPS." ;;
  esac
  PUERTO=$(valor FORMATO_PUBLICAR | sed -E 's|.*:||')
fi

# Sin el archivo, Docker montaria una carpeta vacia en su lugar y Streamlit no
# arrancaria. Se crea desde la plantilla y se avisa para llenarlo.
# Los secretos pueden ir en .env (GOOGLE_REFRESH_TOKEN, DRIVE_CARPETA_ID...) o en
# .streamlit/secrets.toml; la app usa primero .env. El archivo .toml se crea
# siempre (aunque quede vacio) porque docker-compose lo monta.
mkdir -p .streamlit
secretos_en_env=no
[ -n "$(valor GOOGLE_REFRESH_TOKEN)" ] && secretos_en_env=si
if [ ! -f .streamlit/secrets.toml ]; then
  cp secrets.toml.example .streamlit/secrets.toml
  chmod 600 .streamlit/secrets.toml
  if [ "$secretos_en_env" = no ]; then
    aviso "Cree .streamlit/secrets.toml desde la plantilla. Llena los secretos ahi o en .env (ver .env.example)"
    aviso "y luego: docker compose restart formato"
  fi
elif [ "$secretos_en_env" = no ] && grep -qE '^[[:space:]]*refresh_token[[:space:]]*=[[:space:]]*""' .streamlit/secrets.toml; then
  aviso "Sin refresh_token en .env ni en .streamlit/secrets.toml: la app no guardara en Drive ni mandara correo."
fi
# El contenedor corre como el usuario 10001 y tiene que poder leerlo.
sudo chown 10001 .streamlit/secrets.toml

# --- 3. Firewall --------------------------------------------------------------
paso "Firewall (UFW)"
command -v ufw >/dev/null 2>&1 || sudo apt-get install -y ufw
PUERTO_SSH=$(echo "${SSH_CONNECTION:-}" | awk '{print $4}')
if [ -z "$PUERTO_SSH" ]; then
  PUERTO_SSH=$( { sudo sshd -T 2>/dev/null || true; } | awk '$1=="port"{print $2; exit}')
fi
sudo ufw allow "${PUERTO_SSH:-22}/tcp" comment 'SSH'
if [ -n "$DOMINIO" ]; then
  sudo ufw allow 80/tcp comment 'HTTP (certbot y redireccion)'
  sudo ufw allow 443/tcp comment 'HTTPS'
fi
sudo ufw --force enable
sudo ufw status

# --- 4. Contenedor ------------------------------------------------------------
paso "Contenedor (puede tardar unos minutos la primera vez)"
sudo docker compose build
sudo docker compose up -d --remove-orphans

printf 'Esperando a que la app quede sana'
estado=ninguno
for _ in $(seq 1 60); do
  ID_APP=$(sudo docker compose ps -q formato 2>/dev/null || true)
  estado=$(sudo docker inspect -f '{{.State.Health.Status}}' "$ID_APP" 2>/dev/null || echo ninguno)
  [ "$estado" = healthy ] && break
  printf '.'; sleep 3
done
echo
if [ "$estado" != healthy ]; then
  echo "La app no quedo sana ($estado). Ultimas lineas:" >&2
  sudo docker compose logs --tail 30 formato >&2
  exit 1
fi
echo "App sana."

# --- 5. nginx + HTTPS ---------------------------------------------------------
if [ -n "$DOMINIO" ]; then
  paso "nginx y certificado para $DOMINIO$RUTA/"
  sudo apt-get install -y nginx certbot python3-certbot-nginx

  sed -e "s|RUTA|$RUTA|g" -e "s|PUERTO|$PUERTO|g" deploy/nginx/formato-ubicacion.conf \
    | sudo tee /etc/nginx/snippets/formato-calibracion.conf >/dev/null

  # Si ya hay un sitio para el dominio (el del Validador), la carpeta se agrega
  # ahi: nginx no admite dos bloques server con el mismo nombre.
  SITIO=""
  for f in /etc/nginx/sites-enabled/*; do
    [ -e "$f" ] || continue
    [ "$(readlink -f "$f")" = /etc/nginx/sites-available/formato-calibracion ] && continue
    if sudo grep -qE "^[[:space:]]*server_name[^;]*[[:space:]]$DOMINIO([[:space:]]|;)" "$f"; then
      SITIO=$(readlink -f "$f"); break
    fi
  done

  if [ -n "$SITIO" ]; then
    echo "Agrego $RUTA/ al sitio existente $SITIO."
    sudo rm -f /etc/nginx/sites-enabled/formato-calibracion
    if ! sudo grep -q 'include snippets/formato-calibracion.conf;' "$SITIO"; then
      sudo cp "$SITIO" "$SITIO.antes-formato"
      sudo sed -i -E "/^[[:space:]]*server_name[^;]*[[:space:]]$DOMINIO([[:space:]]|;)/a\\    include snippets/formato-calibracion.conf;   # Formato de calibracion" "$SITIO"
      echo "Respaldo en $SITIO.antes-formato."
    fi
  elif [ ! -f /etc/nginx/sites-available/formato-calibracion ]; then
    sed "s|DOMINIO|$DOMINIO|" deploy/nginx/formato.conf \
      | sudo tee /etc/nginx/sites-available/formato-calibracion >/dev/null
    sudo ln -sf /etc/nginx/sites-available/formato-calibracion /etc/nginx/sites-enabled/formato-calibracion
    sudo rm -f /etc/nginx/sites-enabled/default
    SITIO=/etc/nginx/sites-available/formato-calibracion
  else
    SITIO=/etc/nginx/sites-available/formato-calibracion
  fi
  sudo nginx -t
  sudo systemctl reload nginx

  if ! sudo grep -qE 'listen[^;]*443' "$SITIO"; then
    if [ -n "$CORREO" ]; then CUENTA=(-m "$CORREO"); else CUENTA=(--register-unsafely-without-email); fi
    sudo certbot --nginx -d "$DOMINIO" --redirect --agree-tos -n --keep-until-expiring "${CUENTA[@]}"
  fi
  URL="https://$DOMINIO$RUTA/"
else
  URL="http://$(hostname -I | awk '{print $1}'):$PUERTO/"
fi

# --- 6. Actualizacion automatica ----------------------------------------------
if [ "$ACTUALIZACION" = si ]; then
  paso "Actualizacion automatica desde GitHub ($RAMA)"
  REPO=$(pwd)
  if sudo -H -u "$DUENO" env GIT_TERMINAL_PROMPT=0 git -C "$REPO" fetch -q origin "$RAMA"; then
    sudo tee /etc/systemd/system/formato-actualizar.service >/dev/null <<UNIDAD
[Unit]
Description=Formato de calibracion: baja los cambios de $RAMA y recompila
Wants=network-online.target
After=network-online.target docker.service

[Service]
Type=oneshot
User=$DUENO
WorkingDirectory=$REPO
Environment=GIT_TERMINAL_PROMPT=0
Environment=RAMA=$RAMA
ExecStart=/usr/bin/env bash $REPO/scripts/actualizar.sh
UNIDAD
    sudo tee /etc/systemd/system/formato-actualizar.timer >/dev/null <<UNIDAD
[Unit]
Description=Formato de calibracion: revisa $RAMA cada 3 minutos

[Timer]
OnBootSec=2min
OnUnitActiveSec=3min
RandomizedDelaySec=30s

[Install]
WantedBy=timers.target
UNIDAD
    sudo systemctl daemon-reload
    sudo systemctl enable --now formato-actualizar.timer
    sudo systemctl restart formato-actualizar.timer
    echo "Activa: cada 3 minutos revisa $RAMA. Bitacora: journalctl -u formato-actualizar"
  else
    aviso "No pude bajar de GitHub sin contrasena, asi que no active la actualizacion automatica."
    aviso "Guarda la credencial (git config --global credential.helper store y un git pull)"
    aviso "o agrega una llave de despliegue al repositorio, y vuelve a correr este script."
  fi
fi

paso "Listo"
echo "Abre $URL"
