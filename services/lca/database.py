from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = (BASE_DIR / ".." / ".." / "outputs").resolve()
DB_DIR.mkdir(exist_ok=True)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_DIR / 'lca.db'}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
