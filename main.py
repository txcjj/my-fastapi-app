import os
from fastapi import FastAPI
from sqlalchemy import create_engine, text

app = FastAPI()

# 从 Render 的环境变量里读连接串
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
        # 把 instruments 换成你在 Supabase 里实际建的表名
        result = conn.execute(text("SELECT * FROM instruments LIMIT 5"))
        rows = [dict(row._mapping) for row in result]
    return {"data": rows}