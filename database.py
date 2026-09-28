import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

if not database_url:
    # 本地开发兜底：未注入 DATABASE_URL 时回退到 SQLite，避免启动即崩溃
    database_url = "sqlite:///./inventory.db"
    print("[database] 未设置 DATABASE_URL，已回退到本地 SQLite: inventory.db")

# SQLite 在多线程（FastAPI 默认线程池）下需要关闭 check_same_thread
_connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()