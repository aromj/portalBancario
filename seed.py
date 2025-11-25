from database import Base, engine, SessionLocal
from models import User, Account
from security import get_password_hash
from crud import create_account
from sqlalchemy import text

def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Demo user
        demo = User(full_name="Cliente Demo", email="demo@bank.com", hashed_password=get_password_hash("123456"))
        db.add(demo)
        db.commit()
        db.refresh(demo)

        # Accounts
        acc1 = create_account(db, demo, number="2200112233", type_="Ahorros", balance=1200.50)
        acc2 = create_account(db, demo, number="1100223344", type_="Corriente", balance=500.00)

        # Another user to allow transfers
        other = User(full_name="Beneficiario Prueba", email="beneficiario@bank.com", hashed_password=get_password_hash("123456"))
        db.add(other); db.commit(); db.refresh(other)
        create_account(db, other, number="3300330044", type_="Ahorros", balance=250.00)

        print("Base de datos inicializada.")
        print("Usuario demo: demo@bank.com / 123456")
        print("Cuentas: 2200112233 (Ahorros), 1100223344 (Corriente)")
        print("Cuenta destino de prueba: 3300330044 (Ahorros)")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
