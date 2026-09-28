from pydantic import BaseModel
from typing import Optional, List
from datetime import date

# ---------- 门店 ----------
class StoreIn(BaseModel):
    name: str
    address: Optional[str] = None
    tax_rate: Optional[float] = 0.01

# ---------- 用户 ----------
class UserIn(BaseModel):
    store_id: int
    auth_uid: Optional[str] = None
    name: str
    role: str = "staff"
    phone: Optional[str] = None
    status: str = "active"

# ---------- 供应商 ----------
class SupplierIn(BaseModel):
    store_id: int
    name: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    bank_account: Optional[str] = None
    status: str = "active"

# ---------- 仓库 ----------
class WarehouseIn(BaseModel):
    store_id: int
    name: str
    type: Optional[str] = None

# ---------- 分类 ----------
class CategoryIn(BaseModel):
    store_id: int
    name: str
    parent_id: Optional[int] = None

# ---------- 原材料 ----------
class MaterialIn(BaseModel):
    store_id: int
    name: str
    category_id: Optional[int] = None
    unit: str = "kg"
    spec: Optional[str] = None
    purchase_unit: Optional[str] = None
    purchase_to_base_ratio: Optional[float] = 1
    safety_stock: Optional[float] = 0
    shelf_life_days: Optional[int] = 0
    is_perishable: Optional[bool] = False
    latest_purchase_price: Optional[float] = 0

# ---------- 菜品 ----------
class DishIn(BaseModel):
    store_id: int
    name: str
    category_id: Optional[int] = None
    selling_price: float = 0
    pos_sku: Optional[str] = None
    status: str = "active"

# ---------- BOM 配方 ----------
class BomItemIn(BaseModel):
    dish_id: int
    material_id: int
    quantity: float
    unit: str = "kg"
    loss_rate: float = 0
    version: int = 1
    is_active: bool = True

# ---------- 采购单 ----------
class PurchaseOrderIn(BaseModel):
    store_id: int
    supplier_id: int
    order_no: str
    status: str = "pending"
    created_by: Optional[int] = None

class PurchaseItemIn(BaseModel):
    purchase_order_id: int
    material_id: int
    quantity: float
    unit_price: float
    amount: float
    tax_amount: float = 0

# ---------- 入库单 ----------
class StockInIn(BaseModel):
    store_id: int
    warehouse_id: int
    source_type: str = "采购"
    source_id: Optional[int] = None
    operator_id: Optional[int] = None
    status: str = "pending"

class StockInItemIn(BaseModel):
    stock_in_id: int
    material_id: int
    quantity: float
    unit_cost: float
    batch_no: Optional[str] = None
    production_date: Optional[date] = None
    expire_date: Optional[date] = None

# ---------- 出库单 ----------
class StockOutIn(BaseModel):
    store_id: int
    warehouse_id: int
    out_type: str = "销售自动扣减"
    source_id: Optional[int] = None
    operator_id: Optional[int] = None

class StockOutItemIn(BaseModel):
    stock_out_id: int
    material_id: int
    quantity: float
    cost_amount: float

# ---------- 盘点单 ----------
class StockTakeIn(BaseModel):
    store_id: int
    warehouse_id: int
    take_date: date
    status: str = "pending"          # 与 StockTake 模型默认值保持一致
    operator_id: Optional[int] = None

class StockTakeItemIn(BaseModel):
    stock_take_id: int
    material_id: int
    book_quantity: float
    actual_quantity: float

# ---------- POS 导入 ----------
# 说明：main.py 使用的是其内部定义的 PosImportBatchIn（含 file_hash / total_amount 等增强字段），
# 这里保留一个等价定义供其它模块引用，字段与 PosImportBatch 模型保持一致。
class PosImportIn(BaseModel):
    store_id: int
    file_name: str
    import_date: date
    status: str = "pending"
    total_rows: int = 0
    matched_rows: int = 0
    unmatched_rows: int = 0
    sale_date_end: Optional[date] = None
    uploaded_by: Optional[str] = None
    file_hash: Optional[str] = None
    total_amount: float = 0
    total_quantity: float = 0
    stock_deducted: bool = False
    remark: Optional[str] = None

# ---------- 固定资产 ----------
class AssetIn(BaseModel):
    store_id: int
    name: str
    purchase_amount: float
    purchase_date: date
    depreciation_method: str = "直线法"
    useful_life_months: int = 60
    residual_rate: float = 0.05
    monthly_depreciation: float = 0

# ---------- 成本/营收/利润 ----------
class CostDailyIn(BaseModel):
    store_id: int
    cost_date: date
    material_cost: float = 0
    labor_cost: float = 0
    rent_cost: float = 0
    utility_cost: float = 0
    depreciation_cost: float = 0
    other_cost: float = 0
    total_cost: float = 0            # 新增：前端 saveCost() 会提交，避免被丢弃

class RevenueDailyIn(BaseModel):
    store_id: int
    revenue_date: date
    total_revenue: float = 0
    total_orders: int = 0

class ProfitDailyIn(BaseModel):
    store_id: int
    profit_date: date
    revenue: float = 0
    cost: float = 0
    gross_profit: float = 0
    pretax_profit: float = 0