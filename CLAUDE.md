# CLAUDE.md

## Proyecto

Aplicacion Streamlit para generar formatos de calibracion de equipos de monitoreo de calidad del aire SIMAJ. La interfaz y los textos de usuario estan principalmente en espanol.

## Estructura

- `app.py`: interfaz Streamlit, logica de calculo, formularios y exportacion/integracion con Google APIs.
- `requirements.txt`: dependencias Python.
- `simaj.png`: logo usado por la interfaz.

## Desarrollo

Instalar dependencias:

```powershell
python -m pip install -r requirements.txt
```

Ejecutar localmente:

```powershell
streamlit run app.py
```

## Convenciones

- Mantener los cambios enfocados en `app.py` y conservar la interfaz en espanol.
- Seguir los patrones y claves existentes de Streamlit para evitar perder valores en `st.session_state`.
- No eliminar ni modificar datos de equipos sin una razon funcional verificable.
- Mantener la compatibilidad con los formatos de impresion y exportacion existentes.
- No guardar credenciales, secretos ni archivos de servicio de Google en el repositorio.
- Usar ASCII en archivos nuevos salvo que el texto de usuario requiera caracteres espanoles.

## Validacion

Antes de entregar cambios, comprobar que la aplicacion puede iniciar con:

```powershell
streamlit run app.py
```

Para cambios de logica, probar al menos los tipos de servicio SIMAJ y Mantenimiento Externo, y una opcion de gases y otra de particulas.
