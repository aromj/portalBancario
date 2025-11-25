from fastapi import FastAPI, Request, Depends, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from database import Base, engine, get_db
from models import User, Account, Transaction
from crud import (
    authenticate_user, get_user, get_accounts_by_user, get_account_by_number,
    transfer, list_recent_transactions, create_user, get_user_by_email,
    get_transactions_by_account
)
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Optional
from security import get_password_hash
from seed import seed
import re
import os

app = FastAPI(title="Portal Bancario - Los Olivos")
# Mejorar seguridad: usar variable de entorno o valor más seguro
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_USE_RANDOM_STRING")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2
env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize demo data on startup
@app.on_event("startup")
def startup_event():
    try:
        seed()
    except Exception as e:
        print(f"Info: Database already initialized or error: {e}")

def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Obtiene el usuario actual desde la sesión"""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return get_user(db, user_id)

def require_auth(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependencia que requiere autenticación"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    return user

# Validaciones
def validate_email(email: str) -> bool:
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_password(password: str) -> tuple[bool, str]:
    """Valida contraseña: mínimo 6 caracteres"""
    if len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres"
    return True, ""

def validate_amount(amount: float) -> tuple[bool, str]:
    """Valida monto: debe ser positivo y con máximo 2 decimales"""
    if amount <= 0:
        return False, "El monto debe ser mayor que 0"
    if amount > 1000000:
        return False, "El monto excede el límite permitido"
    return True, ""

# ============================================================================
# RUTAS PÚBLICAS
# ============================================================================

@app.get("/", response_class=HTMLResponse)
def root(request: Request, db: Session = Depends(get_db)):
    """Página de inicio - redirige a dashboard si está autenticado"""
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    template = env.get_template("landing.html")
    return template.render()

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Página de login"""
    # Si ya está autenticado, redirigir al dashboard
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    template = env.get_template("login.html")
    error = request.query_params.get("error")
    success = request.query_params.get("success")
    return template.render(error=error, success=success)

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Procesa el login"""
    # Validar email
    if not validate_email(email):
        return RedirectResponse(
            url="/login?error=Email%20inválido",
            status_code=status.HTTP_302_FOUND
        )
    
    user = authenticate_user(db, email=email, password=password)
    if not user:
        return RedirectResponse(
            url="/login?error=Credenciales%20inválidas",
            status_code=status.HTTP_302_FOUND
        )
    
    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    """Página de registro"""
    # Si ya está autenticado, redirigir al dashboard
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    template = env.get_template("register.html")
    error = request.query_params.get("error")
    return template.render(error=error)

@app.post("/register", response_class=HTMLResponse)
def register_user(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Procesa el registro de nuevo usuario"""
    template = env.get_template("register.html")
    
    # Validaciones
    if not full_name or len(full_name.strip()) < 3:
        return template.render(error="El nombre debe tener al menos 3 caracteres")
    
    if not validate_email(email):
        return template.render(error="Email inválido")
    
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        return template.render(error=error_msg)
    
    # Verificar si el email ya existe
    existing = get_user_by_email(db, email)
    if existing:
        return template.render(error="El correo ya está registrado")
    
    # Crear usuario (esto también crea las cuentas por defecto)
    try:
        create_user(db, full_name=full_name.strip(), email=email.lower().strip(), password=password)
        user = get_user_by_email(db, email.lower().strip())
        if user:
            request.session["user_id"] = user.id
            return RedirectResponse(
                url="/login?success=Cuenta%20creada%20exitosamente",
                status_code=status.HTTP_302_FOUND
            )
    except Exception as e:
        return template.render(error=f"Error al crear la cuenta: {str(e)}")
    
    return template.render(error="Error desconocido al crear la cuenta")

@app.get("/logout")
def logout(request: Request):
    """Cierra la sesión"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

# ============================================================================
# RUTAS PROTEGIDAS (requieren autenticación)
# ============================================================================

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    """Dashboard principal con resumen de cuentas y movimientos recientes"""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    accounts = get_accounts_by_user(db, user.id)
    account_ids = [a.id for a in accounts]
    recent = list_recent_transactions(db, account_ids, limit=10) if account_ids else []
    
    # Calcular totales
    total_balance = sum(acc.balance for acc in accounts)
    
    template = env.get_template("dashboard.html")
    return template.render(
        user=user,
        accounts=accounts,
        transactions=recent,
        total_balance=total_balance
    )

@app.get("/cuentas", response_class=HTMLResponse)
def accounts_page(request: Request, db: Session = Depends(get_db)):
    """Página de gestión de cuentas"""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    accounts = get_accounts_by_user(db, user.id)
    template = env.get_template("accounts.html")
    return template.render(user=user, accounts=accounts)

@app.get("/movimientos", response_class=HTMLResponse)
def transactions_page(request: Request, db: Session = Depends(get_db), account_id: Optional[int] = None):
    """Página de movimientos/transacciones"""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    accounts = get_accounts_by_user(db, user.id)
    
    # Si se especifica una cuenta, filtrar transacciones
    if account_id:
        # Verificar que la cuenta pertenece al usuario
        account = next((a for a in accounts if a.id == account_id), None)
        if account:
            transactions = get_transactions_by_account(db, account_id)
        else:
            transactions = []
    else:
        # Todas las transacciones de todas las cuentas
        account_ids = [a.id for a in accounts]
        transactions = list_recent_transactions(db, account_ids, limit=100) if account_ids else []
    
    template = env.get_template("transactions.html")
    return template.render(
        user=user,
        accounts=accounts,
        transactions=transactions,
        selected_account_id=account_id
    )

@app.get("/transferencias", response_class=HTMLResponse)
def transfer_page(request: Request, db: Session = Depends(get_db)):
    """Página de transferencias"""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    accounts = get_accounts_by_user(db, user.id)
    template = env.get_template("transfer.html")
    return template.render(user=user, accounts=accounts, message=None, error=None)

@app.post("/transferencias", response_class=HTMLResponse)
def do_transfer(
    request: Request,
    from_account: str = Form(...),
    to_account: str = Form(...),
    amount: float = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    """Procesa una transferencia"""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    template = env.get_template("transfer.html")
    my_accounts = {a.number: a for a in get_accounts_by_user(db, user.id)}
    
    # Validaciones
    from_acc = my_accounts.get(from_account)
    if not from_acc:
        return template.render(
            user=user,
            accounts=my_accounts.values(),
            error="Cuenta de origen inválida",
            message=None
        )
    
    to_acc = get_account_by_number(db, to_account)
    if not to_acc:
        return template.render(
            user=user,
            accounts=my_accounts.values(),
            error="Cuenta destino no encontrada",
            message=None
        )
    
    if from_acc.number == to_acc.number:
        return template.render(
            user=user,
            accounts=my_accounts.values(),
            error="No puede transferir a la misma cuenta",
            message=None
        )
    
    # Validar monto
    is_valid, error_msg = validate_amount(amount)
    if not is_valid:
        return template.render(
            user=user,
            accounts=my_accounts.values(),
            error=error_msg,
            message=None
        )
    
    # Realizar transferencia
    try:
        ok = transfer(db, from_acc, to_acc, amount, description=description.strip() or "Transferencia")
        if not ok:
            return template.render(
                user=user,
                accounts=my_accounts.values(),
                error="Fondos insuficientes",
                message=None
            )
        
        return template.render(
            user=user,
            accounts=my_accounts.values(),
            error=None,
            message=f"Transferencia de ${amount:,.2f} realizada exitosamente"
        )
    except Exception as e:
        return template.render(
            user=user,
            accounts=my_accounts.values(),
            error=f"Error al procesar la transferencia: {str(e)}",
            message=None
        )

# Mantener compatibilidad con ruta anterior
@app.get("/transfer", response_class=HTMLResponse)
def transfer_page_old(request: Request, db: Session = Depends(get_db)):
    return RedirectResponse(url="/transferencias", status_code=status.HTTP_301_MOVED_PERMANENTLY)

@app.post("/transfer", response_class=HTMLResponse)
def do_transfer_old(request: Request, **kwargs):
    return RedirectResponse(url="/transferencias", status_code=status.HTTP_301_MOVED_PERMANENTLY)

@app.get("/perfil", response_class=HTMLResponse)
def profile_page(request: Request, db: Session = Depends(get_db)):
    """Página de perfil del usuario"""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    accounts = get_accounts_by_user(db, user.id)
    template = env.get_template("profile.html")
    return template.render(user=user, accounts=accounts)