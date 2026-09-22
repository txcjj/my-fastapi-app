from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
import os

from database import engine, get_db
import models

app = FastAPI(title="超市进销存系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 商品 ----------
class GoodsIn(BaseModel):
    barcode: Optional[str] = None
    name: str
    category_id: Optional[int] = None
    unit: Optional[str] = "件"
    purchase_price: Optional[float] = 0
    sale_price: Optional[float] = 0
    stock: Optional[int] = 0
    stock_warn: Optional[int] = 10

@app.get("/api/goods")
def list_goods(keyword: str = "", db: Session = Depends(get_db)):
    sql = "SELECT * FROM goods WHERE is_active = TRUE"
    params = {}
    if keyword:
        sql += " AND (name ILIKE :kw OR barcode ILIKE :kw)"
        params["kw"] = f"%{keyword}%"
    sql += " ORDER BY id DESC"
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]

@app.post("/api/goods")
def create_goods(item: GoodsIn, db: Session = Depends(get_db)):
    sql = """INSERT INTO goods (barcode, name, category_id, unit, purchase_price, sale_price, stock, stock_warn)
             VALUES (:barcode, :name, :category_id, :unit, :purchase_price, :sale_price, :stock, :stock_warn)
             RETURNING id"""
    rid = db.execute(text(sql), item.dict()).scalar()
    db.commit()
    return {"id": rid, "message": "创建成功"}

@app.put("/api/goods/{goods_id}")
def update_goods(goods_id: int, item: GoodsIn, db: Session = Depends(get_db)):
    sql = """UPDATE goods SET barcode=:barcode, name=:name, category_id=:category_id,
             unit=:unit, purchase_price=:purchase_price, sale_price=:sale_price,
             stock=:stock, stock_warn=:stock_warn, updated_at=NOW() WHERE id=:id"""
    params = item.dict()
    params["id"] = goods_id
    db.execute(text(sql), params)
    db.commit()
    return {"message": "更新成功"}

@app.delete("/api/goods/{goods_id}")
def delete_goods(goods_id: int, db: Session = Depends(get_db)):
    db.execute(text("UPDATE goods SET is_active=FALSE WHERE id=:id"), {"id": goods_id})
    db.commit()
    return {"message": "删除成功"}

# ---------- 分类 ----------
@app.get("/api/categories")
def list_categories(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT * FROM categories ORDER BY id")).mappings().all()
    return [dict(r) for r in rows]

# ---------- 仓库 ----------
@app.get("/api/warehouses")
def list_warehouses(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT * FROM warehouses ORDER BY id")).mappings().all()
    return [dict(r) for r in rows]

# ---------- 统计看板 ----------
@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    total_goods = db.execute(text("SELECT COUNT(*) FROM goods WHERE is_active=TRUE")).scalar()
    total_stock = db.execute(text("SELECT COALESCE(SUM(stock),0) FROM goods WHERE is_active=TRUE")).scalar()
    warn_count  = db.execute(text("SELECT COUNT(*) FROM goods WHERE is_active=TRUE AND stock <= stock_warn")).scalar()
    total_value = db.execute(text("SELECT COALESCE(SUM(stock * purchase_price),0) FROM goods WHERE is_active=TRUE")).scalar()
    return {
        "total_goods": total_goods,
        "total_stock": total_stock,
        "warn_count": warn_count,
        "total_value": float(total_value or 0),
    }

# ---------- 库存预警 ----------
@app.get("/api/goods/warning")
def warning_goods(db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT * FROM goods WHERE is_active=TRUE AND stock <= stock_warn ORDER BY stock ASC"
    )).mappings().all()
    return [dict(r) for r in rows]

# ---------- 前端静态文件 ----------
# 确保 static 目录存在
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html")