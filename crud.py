from sqlalchemy.orm import Session
from sqlalchemy import select
from models import User, Account, Transaction, TxType
from security import verify_password, get_password_hash
from typing import Optional, List

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()

def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)

def create_user(db: Session, full_name: str, email: str, password: str) -> User:
    """Crea un nuevo usuario y le asigna cuentas por defecto con saldos iniciales"""
    user = User(full_name=full_name, email=email, hashed_password=get_password_hash(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Cuentas iniciales automáticas con saldos por defecto
    acc1 = Account(
        user_id=user.id,
        number=f"CR{user.id:06d}",
        type="Ahorros",
        balance=2000.0  # Saldo inicial por defecto
    )
    acc2 = Account(
        user_id=user.id,
        number=f"DB{user.id:06d}",
        type="Corriente",
        balance=1000.0  # Saldo inicial por defecto
    )
    db.add_all([acc1, acc2])
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_account(db: Session, user: User, number: str, type_: str = "Ahorros", balance: float = 0.0) -> Account:
    acc = Account(user_id=user.id, number=number, type=type_, balance=balance)
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc

def get_accounts_by_user(db: Session, user_id: int) -> list[Account]:
    stmt = select(Account).where(Account.user_id == user_id).order_by(Account.id.asc())
    return list(db.execute(stmt).scalars().all())

def get_account_by_number(db: Session, number: str) -> Optional[Account]:
    return db.execute(select(Account).where(Account.number == number)).scalar_one_or_none()

def add_transaction(db: Session, account: Account, tx_type: TxType, amount: float, description: str = "", counterparty: str = "") -> Transaction:
    tx = Transaction(account_id=account.id, type=tx_type, amount=amount, description=description, counterparty=counterparty)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx

def list_recent_transactions(db: Session, account_ids: list[int], limit: int = 10) -> list[Transaction]:
    """Lista las transacciones más recientes de las cuentas especificadas"""
    if not account_ids:
        return []
    from sqlalchemy import select, desc
    stmt = select(Transaction).where(Transaction.account_id.in_(account_ids)).order_by(desc(Transaction.created_at)).limit(limit)
    return list(db.execute(stmt).scalars().all())

def get_transactions_by_account(db: Session, account_id: int, limit: int = 100) -> list[Transaction]:
    """Obtiene todas las transacciones de una cuenta específica"""
    from sqlalchemy import select, desc
    stmt = select(Transaction).where(Transaction.account_id == account_id).order_by(desc(Transaction.created_at)).limit(limit)
    return list(db.execute(stmt).scalars().all())

def transfer(db: Session, from_acc: Account, to_acc: Account, amount: float, description: str = "") -> bool:
    """Realiza una transferencia entre dos cuentas"""
    if amount <= 0:
        raise ValueError("El monto debe ser positivo")
    if from_acc.balance < amount:
        return False
    
    # Actualizar saldos
    from_acc.balance -= amount
    to_acc.balance += amount
    
    # Registrar transacciones
    add_transaction(
        db, from_acc, TxType.DEBIT, amount,
        description or "Transferencia enviada",
        counterparty=to_acc.number
    )
    add_transaction(
        db, to_acc, TxType.CREDIT, amount,
        description or "Transferencia recibida",
        counterparty=from_acc.number
    )
    
    # Guardar cambios
    db.add(from_acc)
    db.add(to_acc)
    db.commit()
    return True

