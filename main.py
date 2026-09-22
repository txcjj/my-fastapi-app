import os
from fastapi import FastAPI
from sqlalchemy import create_engine, text

app = FastAPI()

database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(database_url, pool_pre_ping=True)

@app.get("/")
def read_root():
    return {"message": "Hello, Render!"}

@app.get("/db-test")
def db_test():
    with engine.connect() as conn:
        # 查询 public schema 下所有表名
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
    return {"tables": tables}