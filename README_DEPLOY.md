Despliegue - Instrucciones rápidas
=================================

Este archivo explica cómo desplegar la aplicación FastAPI `portal_bancario_fastapi` en un servidor (SiteGround) y alternativas recomendadas.

Contenido recomendado para subir
------------------------------
- Archivos de código: `*.py` (por ejemplo `main.py`, `auth.py`, `crud.py`, `models.py`, `security.py`, `database.py`)
- Carpetas: `templates/`, `static/`
- `requirements.txt`
- `Procfile` (opcional, útil en plataformas tipo Heroku)
- `README.md` (útil)

No subir
--------
- `bank.db` u otras bases locales
- Carpetas de entorno virtual (`venv/`, `.venv/`)
- Archivos de configuración local (`.env`) con secretos
- `__pycache__/`, `*.pyc`, `.idea/`, `.vscode/`

Requisitos en servidor
----------------------
- Acceso SFTP/FTP para subir archivos
- (Recomendado) Acceso SSH para instalar dependencias y ejecutar servicios
- Python 3.10+ (según lo soporte la app)

Comandos (asumiendo acceso SSH al servidor)
------------------------------------------
# Ir al directorio del despliegue
cd /ruta/al/proyecto

# Crear virtualenv
python3 -m venv venv
# Activar (Linux)
source venv/bin/activate
# En Windows (si se usa)
# venv\Scripts\activate

# Actualizar pip e instalar dependencias
python -m pip install --upgrade pip
pip install -r requirements.txt

# Variables de entorno (no crear .env con secretos en el repo)
export SECRET_KEY="reemplaza_con_tu_secreto"
# Si usas DB remota (recomendado):
# export DATABASE_URL="postgresql://user:pass@host:port/dbname"

# Iniciar con gunicorn + uvicorn workers (ejemplo)
# Cambia PORT según la configuración del hosting
gunicorn -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000 --workers 2

Nota: en servidores compartidos el proceso puede no permanecer activo cuando cierres la terminal. Usa `screen` o `tmux` para mantenerlo, o configura un servicio systemd si tienes privilegios.

SiteGround - notas específicas
------------------------------
- Algunos planes SiteGround permiten crear aplicaciones Python desde cPanel y manejan virtualenv e inicio de procesos (ver "Setup Python App"). Si tu plan lo soporta, usa la interfaz para crear el entorno, subir los archivos y configurar el comando de inicio (puede pedir un WSGI entrypoint).
- FastAPI es ASGI; Passenger (mucho usado en cPanel) es WSGI. En planes que sólo soportan Passenger, FastAPI no funciona directamente sin una capa adaptadora. Por eso las opciones:
  - Ejecuta `gunicorn -k uvicorn.workers.UvicornWorker main:app` si el panel permite procesos persistentes.
  - Si SiteGround no admite procesos persistentes, considera desplegar en un proveedor más moderno para aplicaciones Python (Render, Fly.io, Railway, PythonAnywhere, DigitalOcean App Platform).

Alternativas recomendadas (más sencillas para ASGI)
--------------------------------------------------
- Render (deploy directo desde GitHub, soporte auto HTTPS, servicio para procesos ASGI)
- Railway
- Fly.io
- PythonAnywhere (soporta apps WSGI principalmente; revisar compatibilidad)
- DigitalOcean App Platform

Ejemplo de flujo con SFTP + SSH (resumido)
-----------------------------------------
1. Subir archivos por SFTP (templates, static, *.py, requirements.txt, Procfile).
2. Conectar por SSH y crear virtualenv + pip install -r requirements.txt.
3. Configurar variables de entorno (export SECRET_KEY=...)
4. Ejecutar la app con gunicorn o `python -m uvicorn main:app --host 0.0.0.0 --port 8000`.
5. Mantener proceso con `screen -S app` o `tmux` o crear un servicio `systemd`.

Archivo `Procfile` (ejemplo)
----------------------------
web: gunicorn -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT --workers 2

Seguridad y buenas prácticas
----------------------------
- No subir bases de datos locales con datos reales.
- Usa variables de entorno para claves y contraseñas.
- Revisa permisos de archivos y evita exponer `static/uploads` si contiene archivos privados.
- Configura HTTPS en el hosting.

Consejos rápidos para SiteGround sin soporte Python permanente
-------------------------------------------------------------
- Usa un servicio externo para la app (Render, Fly.io, Railway) y en SiteGround mantén solo una web estática o el frontend que consuma la API remota.
- Si insistes en SiteGround, contacta soporte para confirmar si tu plan soporta procesos persistentes o aplicaciones Python en cPanel.

¿Quieres que también genere un `start.sh` para iniciar la app con `screen` y un ejemplo de `systemd` unit file? (Puedo generarlos y probar los comandos a nivel de texto).