"""Se corre una sola vez en tu computadora para obtener el refresh token de Google (Drive + Gmail).

Uso:
    python obtener_token_google.py client_secret.json

Abre el navegador, inicias sesión con la cuenta que subirá los archivos y enviará el correo,
y al final imprime el bloque que debes pegar en Secrets de Streamlit.
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/gmail.send"]

if len(sys.argv) != 2:
    sys.exit(__doc__)

flujo = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
creds = flujo.run_local_server(port=0, access_type="offline", prompt="consent")

print("\nPega esto en Secrets de Streamlit (completa las dos primeras líneas):\n")
print('correo_coordinador = "correo@del-coordinador.com"')
print('drive_carpeta_id = "ID_DE_LA_CARPETA_DE_DRIVE"')
print("\n[google_oauth]")
print(f"client_id = {json.dumps(creds.client_id)}")
print(f"client_secret = {json.dumps(creds.client_secret)}")
print(f"refresh_token = {json.dumps(creds.refresh_token)}")
