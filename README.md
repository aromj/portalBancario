
> **Stack**: FastAPI + SQLite + SQLAlchemy + Jinja2 (sin JS extra).  
> **Usuarios demo**: `demo@bank.com` / `123456`

## 1) Crear y activar entorno
```bash
python -m venv .venv

.venv\Scripts\activate
```

## 2) Instalar dependencias
```bash
pip install -r requirements.txt
```

## 3) Inicializar base de datos con datos de prueba
```bash
python seed.py
```

## 4) Ejecutar el servidor
```bash
uvicorn main:app --reload
C:/Users/Admin/AppData/Local/Programs/Python/Python311/python.exe -m uvicorn main:app --reload
```
Abrir: http://127.0.0.1:8000

## 5) Funcionalidad incluida
- Login (email/contraseña) con sesión de servidor.
- Dashboard con **cuentas** y **últimos movimientos**.
- Formulario de **transferencias** internas/externas (entre cuentas por número).
- Datos en **SQLite (`bank.db`)** para hacerlo portable.

## 6) Usuarios y cuentas de prueba
- Usuario: `demo@bank.com` / `123456`
  - Cuentas: `2200112233` (Ahorros), `1100223344` (Corriente)
- Beneficiario: `beneficiario@bank.com` / `123456`
  - Cuenta: `3300330044` (Ahorros)

## 7) Notas de seguridad (para exposición)
- Proyecto **académico**. No apto para producción.  
- Contraseñas **hasheadas** con `bcrypt` (via Passlib).  
- Sesiones con `SessionMiddleware`. Cambia la `secret_key` en `main.py` si lo publicas en red local.

## 8) Estructura
```
portal_bancario_fastapi/
├─ main.py
├─ database.py
├─ models.py
├─ crud.py
├─ security.py
├─ seed.py
├─ requirements.txt
├─ templates/
│  ├─ base.html
│  ├─ landing.html
│  ├─ login.html
│  ├─ dashboard.html
│  └─ transfer.html
└─ static/
   └─ style.css
```

C:/Users/Admin/AppData/Local/Programs/Python/Python311/python.exe -m uvicorn main:app --reload
