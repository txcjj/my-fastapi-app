"""
餐饮进销存系统 · 后端主程序（Render 云端部署版）
FastAPI + SQLAlchemy + PostgreSQL
"""
import os
import logging
from fastapi.responses import FileResponse
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import (
    Column, BigInteger, Integer, String, Numeric, Boolean,
    Date, DateTime, JSON, text
)
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, Session
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel

from database import engine, get_db
import schemas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inventory-api")

Base = declarative_base()

# ============================================================
#  模型定义（27 张表）
# ============================================================
class Store(Base):
    __tablename__ = "stores"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    address = Column(String(255))
    tax_rate = Column(Numeric(5, 4), default=0.01)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    auth_uid = Column(String(64), unique=True)
    name = Column(String(50), nullable=False)
    role = Column(String(20), default="staff")
    phone = Column(String(20))
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    name = Column(String(100), nullable=False)
    contact = Column(String(50))
    phone = Column(String(20))
    address = Column(String(255))
    bank_account = Column(String(50))
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    name = Column(String(50), nullable=False)
    type = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Category(Base):
    __tablename__ = "categories"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    name = Column(String(50), nullable=False)
    parent_id = Column(BigInteger)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Material(Base):
    __tablename__ = "materials"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    name = Column(String(100), nullable=False)
    category_id = Column(BigInteger)
    unit = Column(String(20), nullable=False, default="kg")
    spec = Column(String(100))
    purchase_unit = Column(String(20))
    purchase_to_base_ratio = Column(Numeric(10, 4), default=1)
    safety_stock = Column(Numeric(10, 4), default=0)
    shelf_life_days = Column(Integer, default=0)
    is_perishable = Column(Boolean, default=False)
    latest_purchase_price = Column(Numeric(10, 4), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Dish(Base):
    __tablename__ = "dishes"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    name = Column(String(100), nullable=False)
    category_id = Column(BigInteger)
    selling_price = Column(Numeric(10, 2), nullable=False, default=0)
    pos_sku = Column(String(50))
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Bom(Base):
    __tablename__ = "bom"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    dish_id = Column(BigInteger, index=True)
    material_id = Column(BigInteger, index=True)
    quantity = Column(Numeric(10, 4), nullable=False)
    unit = Column(String(20))
    loss_rate = Column(Numeric(5, 4), default=0)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    supplier_id = Column(BigInteger, index=True)
    order_no = Column(String(50), unique=True, nullable=False)
    status = Column(String(20), default="pending")
    created_by = Column(BigInteger)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    purchase_order_id = Column(BigInteger, index=True)
    material_id = Column(BigInteger, index=True)
    quantity = Column(Numeric(10, 4), nullable=False)
    unit_price = Column(Numeric(10, 4), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class StockIn(Base):
    __tablename__ = "stock_in"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    warehouse_id = Column(BigInteger, index=True)
    source_type = Column(String(20), default="采购")
    source_id = Column(BigInteger)
    operator_id = Column(BigInteger)
    status = Column(String(20),default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class StockInItem(Base):
    __tablename__ = "stock_in_items"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stock_in_id = Column(BigInteger, index=True)
    material_id = Column(BigInteger, index=True)
    quantity = Column(Numeric(10, 4), nullable=False)
    unit_cost = Column(Numeric(10, 4), nullable=False)
    batch_no = Column(String(50))
    production_date = Column(Date)
    expire_date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    warehouse_id = Column(BigInteger, index=True)
    material_id = Column(BigInteger, index=True)
    quantity = Column(Numeric(12, 4), default=0)
    avg_cost = Column(Numeric(10, 4), default=0)
    last_used_date = Column(Date)                                    # ← 新增
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class StockOut(Base):
    __tablename__ = "stock_out"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    warehouse_id = Column(BigInteger, index=True)
    out_type = Column(String(20), default="销售自动扣减")
    source_id = Column(BigInteger)
    operator_id = Column(BigInteger)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class StockOutItem(Base):
    __tablename__ = "stock_out_items"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stock_out_id = Column(BigInteger, index=True)
    material_id = Column(BigInteger, index=True)
    quantity = Column(Numeric(10, 4), nullable=False)
    cost_amount = Column(Numeric(12, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class StockTake(Base):
    __tablename__ = "stock_take"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    warehouse_id = Column(BigInteger, index=True)
    take_date = Column(Date, nullable=False)
    status = Column(String(20), default="pending")
    operator_id = Column(BigInteger)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class StockTakeItem(Base):
    __tablename__ = "stock_take_items"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stock_take_id = Column(BigInteger, index=True)
    material_id = Column(BigInteger, index=True)
    book_quantity = Column(Numeric(10, 4), nullable=False)
    actual_quantity = Column(Numeric(10, 4), nullable=False)
    diff_quantity = Column(Numeric(10, 4))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PosTemplate(Base):
    __tablename__ = "pos_templates"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    pos_brand = Column(String(50), nullable=False)
    field_mapping = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PosImportBatch(Base):
    __tablename__ = "pos_import_batches"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    file_name = Column(String(255), nullable=False)
    import_date = Column(Date, nullable=False)
    status = Column(String(20), default="pending")
    total_rows = Column(Integer, default=0)
    matched_rows = Column(Integer, default=0)
    unmatched_rows = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SalesRecord(Base):
    __tablename__ = "sales_records"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    batch_id = Column(BigInteger, index=True)
    sale_date = Column(Date, nullable=False)
    dish_pos_sku = Column(String(50))
    dish_id = Column(BigInteger, index=True)
    quantity = Column(Numeric(10, 2), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    order_no = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Asset(Base):
    __tablename__ = "assets"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    name = Column(String(100), nullable=False)
    purchase_amount = Column(Numeric(12, 2), nullable=False)
    purchase_date = Column(Date, nullable=False)
    depreciation_method = Column(String(20), default="直线法")
    useful_life_months = Column(Integer, nullable=False)
    residual_rate = Column(Numeric(5, 4), default=0.05)
    monthly_depreciation = Column(Numeric(10, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CostDaily(Base):
    __tablename__ = "cost_daily"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    cost_date = Column(Date, nullable=False)
    material_cost = Column(Numeric(12, 2), default=0)
    labor_cost = Column(Numeric(12, 2), default=0)
    rent_cost = Column(Numeric(12, 2), default=0)
    utility_cost = Column(Numeric(12, 2), default=0)
    depreciation_cost = Column(Numeric(12, 2), default=0)
    other_cost = Column(Numeric(12, 2), default=0)
    total_cost = Column(Numeric(12, 2), default=0)

class RevenueDaily(Base):
    __tablename__ = "revenue_daily"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    revenue_date = Column(Date, nullable=False)
    total_revenue = Column(Numeric(12, 2), default=0)
    total_orders = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ProfitDaily(Base):
    __tablename__ = "profit_daily"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    profit_date = Column(Date, nullable=False)
    revenue = Column(Numeric(12, 2), default=0)
    cost = Column(Numeric(12, 2), default=0)
    gross_profit = Column(Numeric(12, 2), default=0)
    pretax_profit = Column(Numeric(12, 2), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TaxSetting(Base):
    __tablename__ = "tax_settings"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    tax_type = Column(String(50), nullable=False)
    rate = Column(Numeric(6, 4), nullable=False)
    effective_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TaxMonthly(Base):
    __tablename__ = "tax_monthly"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    period = Column(String(7), nullable=False)
    taxable_income = Column(Numeric(12, 2), default=0)
    tax_payable = Column(Numeric(12, 2), default=0)
    calculation_detail = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TaxYearly(Base):
    __tablename__ = "tax_yearly"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(BigInteger, index=True)
    period = Column(String(4), nullable=False)
    taxable_income = Column(Numeric(12, 2), default=0)
    tax_payable = Column(Numeric(12, 2), default=0)
    calculation_detail = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
#  补充 Pydantic 模型
# ============================================================
class PosTemplateIn(BaseModel):
    store_id: int
    pos_brand: str
    field_mapping: Optional[dict] = None

class PosImportBatchIn(BaseModel):
    store_id: int
    file_name: str
    import_date: date
    status: str = "pending"
    total_rows: int = 0
    matched_rows: int = 0
    unmatched_rows: int = 0

class SalesRecordIn(BaseModel):
    store_id: int
    batch_id: Optional[int] = None
    sale_date: date
    dish_pos_sku: Optional[str] = None
    dish_id: Optional[int] = None
    quantity: float
    amount: float
    order_no: Optional[str] = None

class TaxSettingIn(BaseModel):
    store_id: int
    tax_type: str
    rate: float
    effective_date: date

class TaxMonthlyIn(BaseModel):
    store_id: int
    period: str
    taxable_income: float = 0
    tax_payable: float = 0
    calculation_detail: Optional[dict] = None

class TaxYearlyIn(BaseModel):
    store_id: int
    period: str
    taxable_income: float = 0
    tax_payable: float = 0
    calculation_detail: Optional[dict] = None


# ============================================================
#  FastAPI 应用
# ============================================================
app = FastAPI(
    title="餐饮进销存系统 API",
    description="27 张业务表的 RESTful 接口 · 部署于 Render",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---- CORS：允许所有来源（前端可能部署在 Vercel / Netlify 等） ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- 启动时建表（带容错，避免冷启动阻塞） ----
@app.on_event("startup")
def on_startup():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 数据库表结构已就绪（27 张表）")
    except Exception as e:
        logger.error(f"❌ 建表失败：{e}")


# ============================================================
#  通用 CRUD 注册器
# ============================================================
def register_crud(model, schema_in, prefix: str, tag: str, search_field: str = None):
    @app.get(f"/api{prefix}", tags=[tag], summary=f"获取 {tag} 列表")
    def list_items(
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 200,
        db: Session = Depends(get_db),
    ):
        q = db.query(model)
        if keyword and search_field and hasattr(model, search_field):
            q = q.filter(getattr(model, search_field).ilike(f"%{keyword}%"))
        return q.offset(skip).limit(limit).all()

    @app.get(f"/api{prefix}/{{item_id}}", tags=[tag], summary=f"获取 {tag} 详情")
    def get_item(item_id: int, db: Session = Depends(get_db)):
        obj = db.query(model).filter(model.id == item_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail=f"{tag} 记录不存在")
        return obj

    @app.post(f"/api{prefix}", tags=[tag], summary=f"新增 {tag}", status_code=201)
    def create_item(payload: schema_in, db: Session = Depends(get_db)):
        obj = model(**payload.model_dump(exclude_unset=True))
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @app.put(f"/api{prefix}/{{item_id}}", tags=[tag], summary=f"更新 {tag}")
    def update_item(item_id: int, payload: schema_in, db: Session = Depends(get_db)):
        obj = db.query(model).filter(model.id == item_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail=f"{tag} 记录不存在")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return obj

    @app.delete(f"/api{prefix}/{{item_id}}", tags=[tag], summary=f"删除 {tag}")
    def delete_item(item_id: int, db: Session = Depends(get_db)):
        obj = db.query(model).filter(model.id == item_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail=f"{tag} 记录不存在")
        db.delete(obj)
        db.commit()
        return {"ok": True, "deleted_id": item_id}


# ============================================================
#  注册全部 27 张表
# ============================================================
register_crud(Store,             schemas.StoreIn,             "/stores",              "门店",        "name")
register_crud(User,              schemas.UserIn,              "/users",               "用户",        "name")
register_crud(Supplier,          schemas.SupplierIn,          "/suppliers",           "供应商",      "name")
register_crud(Warehouse,         schemas.WarehouseIn,         "/warehouses",          "仓库",        "name")
register_crud(Category,          schemas.CategoryIn,          "/categories",          "分类",        "name")
register_crud(Material,          schemas.MaterialIn,          "/materials",           "原材料",      "name")
register_crud(Dish,              schemas.DishIn,              "/dishes",              "菜品",        "name")
register_crud(Bom,               schemas.BomItemIn,           "/bom",                 "配方")
register_crud(PurchaseOrder,     schemas.PurchaseOrderIn,     "/purchase-orders",     "采购单",      "order_no")
register_crud(PurchaseOrderItem, schemas.PurchaseItemIn,      "/purchase-order-items","采购单明细")
register_crud(StockIn,           schemas.StockInIn,           "/stock-in",            "入库单")
register_crud(StockInItem,       schemas.StockInItemIn,       "/stock-in-items",      "入库明细",    "batch_no")
register_crud(Inventory,         schemas.MaterialIn,          "/inventory",           "库存")
register_crud(StockOut,          schemas.StockOutIn,          "/stock-out",           "出库单")
register_crud(StockOutItem,      schemas.StockOutItemIn,      "/stock-out-items",     "出库明细")
register_crud(StockTake,         schemas.StockTakeIn,         "/stock-take",          "盘点单")
register_crud(StockTakeItem,     schemas.StockTakeItemIn,     "/stock-take-items",    "盘点明细")
register_crud(PosTemplate,       PosTemplateIn,               "/pos-templates",       "POS 模板",    "pos_brand")
register_crud(PosImportBatch,    PosImportBatchIn,            "/pos-import-batches",  "POS 导入批次", "file_name")
register_crud(SalesRecord,       SalesRecordIn,               "/sales-records",       "销售流水",    "order_no")
register_crud(Asset,             schemas.AssetIn,             "/assets",              "固定资产",    "name")
register_crud(CostDaily,         schemas.CostDailyIn,         "/cost-daily",          "每日成本")
register_crud(RevenueDaily,      schemas.RevenueDailyIn,      "/revenue-daily",       "每日营收")
register_crud(ProfitDaily,       schemas.ProfitDailyIn,       "/profit-daily",        "每日利润")
register_crud(TaxSetting,        TaxSettingIn,                "/tax-settings",        "税务参数",    "tax_type")
register_crud(TaxMonthly,        TaxMonthlyIn,                "/tax-monthly",         "月度税务",    "period")
register_crud(TaxYearly,         TaxYearlyIn,                 "/tax-yearly",          "年度税务",    "period")


# ============================================================
#  系统接口
# ============================================================
@app.get("/", include_in_schema=False)
def root():
    return FileResponse("static/index.html")




@app.get("/api/health", tags=["系统"])
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/api/seed-demo", tags=["系统"])
def seed_demo(db: Session = Depends(get_db)):
    """初始化演示数据：1 家门店 + 1 个用户。可在首次部署后调用一次。"""
    if db.query(Store).count() > 0:
        return {"ok": False, "message": "已有数据，跳过初始化"}

    store = Store(name="王记炒饭旗舰店", address="上海市静安区XX路88号", tax_rate=0.01)
    db.add(store); db.commit(); db.refresh(store)

    user = User(store_id=store.id, name="张店长", role="manager", phone="13800000000")
    db.add(user); db.commit()

    return {"ok": True, "store_id": store.id, "user_id": user.id}
# ============================================================
#  按名称确保原材料存在（采购时自动建档）
# ============================================================
class EnsureMaterialIn(BaseModel):
    store_id: int
    name: str
    unit: Optional[str] = "kg"
    latest_purchase_price: Optional[float] = 0


@app.post("/api/materials-ensure", tags=["原材料"])
def ensure_material(payload: EnsureMaterialIn, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="名称不能为空")

    exist = db.query(Material).filter(
        Material.store_id == payload.store_id,
        Material.name == name
    ).first()

    if exist:
        if payload.latest_purchase_price and payload.latest_purchase_price > 0:
            exist.latest_purchase_price = payload.latest_purchase_price
            db.commit()
            db.refresh(exist)
        return exist

    new_mat = Material(
        store_id=payload.store_id,
        name=name,
        unit=payload.unit or "kg",
        latest_purchase_price=payload.latest_purchase_price or 0,
    )
    db.add(new_mat)
    db.commit()
    db.refresh(new_mat)
    return new_mat

# ============================================================
#  Render 启动入口
#  本地调试：python main.py
#  Render：  uvicorn main:app --host 0.0.0.0 --port $PORT
# ============================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)