import os
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from database import get_db, engine
import schemas

app = FastAPI(title="餐饮店进销存系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# 通用工具
# =========================================================
def rows_to_list(result):
    return [dict(r._mapping) for r in result]

# =========================================================
# 1. 数据看板
# =========================================================
@app.get("/api/dashboard")
def dashboard(store_id: int = 1, db: Session = Depends(get_db)):
    today = db.execute(text("SELECT CURRENT_DATE")).scalar()

    revenue = db.execute(text("""
        SELECT COALESCE(total_revenue,0) FROM revenue_daily
        WHERE store_id=:sid AND revenue_date=:d
    """), {"sid": store_id, "d": today}).scalar() or 0

    profit = db.execute(text("""
        SELECT COALESCE(pretax_profit,0) FROM profit_daily
        WHERE store_id=:sid AND profit_date=:d
    """), {"sid": store_id, "d": today}).scalar() or 0

    warn_count = db.execute(text("""
        SELECT COUNT(*) FROM inventory i
        JOIN materials m ON i.material_id=m.id
        WHERE i.store_id=:sid AND i.quantity <= m.safety_stock
    """), {"sid": store_id}).scalar() or 0

    total_materials = db.execute(text("""
        SELECT COUNT(*) FROM materials WHERE store_id=:sid
    """), {"sid": store_id}).scalar() or 0

    return {
        "today_revenue": float(revenue),
        "today_profit": float(profit),
        "warn_count": warn_count,
        "total_materials": total_materials
    }

# =========================================================
# 2. 门店
# =========================================================
@app.get("/api/stores")
def list_stores(db: Session = Depends(get_db)):
    return rows_to_list(db.execute(text("SELECT * FROM stores ORDER BY id")))

@app.post("/api/stores")
def create_store(item: schemas.StoreIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO stores (name, address, tax_rate)
        VALUES (:name, :address, :tax_rate) RETURNING id
    """), item.dict()).scalar()
    db.commit()
    return {"id": rid, "message": "创建成功"}

# =========================================================
# 3. 用户
# =========================================================
@app.get("/api/users")
def list_users(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    sql = "SELECT * FROM users"
    params = {}
    if store_id:
        sql += " WHERE store_id=:sid"
        params["sid"] = store_id
    sql += " ORDER BY id DESC"
    return rows_to_list(db.execute(text(sql), params))

@app.post("/api/users")
def create_user(item: schemas.UserIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO users (store_id, auth_uid, name, role, phone, status)
        VALUES (:store_id, :auth_uid, :name, :role, :phone, :status) RETURNING id
    """), item.dict()).scalar()
    db.commit()
    return {"id": rid, "message": "创建成功"}

# =========================================================
# 4. 供应商
# =========================================================
@app.get("/api/suppliers")
def list_suppliers(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    sql = "SELECT * FROM suppliers"
    params = {}
    if store_id:
        sql += " WHERE store_id=:sid"
        params["sid"] = store_id
    sql += " ORDER BY id DESC"
    return rows_to_list(db.execute(text(sql), params))

@app.post("/api/suppliers")
def create_supplier(item: schemas.SupplierIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO suppliers (store_id, name, contact, phone, address, bank_account, status)
        VALUES (:store_id, :name, :contact, :phone, :address, :bank_account, :status) RETURNING id
    """), item.dict()).scalar()
    db.commit()
    return {"id": rid, "message": "创建成功"}

@app.put("/api/suppliers/{sid}")
def update_supplier(sid: int, item: schemas.SupplierIn, db: Session = Depends(get_db)):
    params = item.dict()
    params["id"] = sid
    db.execute(text("""
        UPDATE suppliers SET store_id=:store_id, name=:name, contact=:contact,
        phone=:phone, address=:address, bank_account=:bank_account, status=:status
        WHERE id=:id
    """), params)
    db.commit()
    return {"message": "更新成功"}

@app.delete("/api/suppliers/{sid}")
def delete_supplier(sid: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM suppliers WHERE id=:id"), {"id": sid})
    db.commit()
    return {"message": "删除成功"}

# =========================================================
# 5. 仓库
# =========================================================
@app.get("/api/warehouses")
def list_warehouses(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    sql = "SELECT * FROM warehouses"
    params = {}
    if store_id:
        sql += " WHERE store_id=:sid"
        params["sid"] = store_id
    sql += " ORDER BY id"
    return rows_to_list(db.execute(text(sql), params))

@app.post("/api/warehouses")
def create_warehouse(item: schemas.WarehouseIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO warehouses (store_id, name, type)
        VALUES (:store_id, :name, :type) RETURNING id
    """), item.dict()).scalar()
    db.commit()
    return {"id": rid, "message": "创建成功"}

# =========================================================
# 6. 分类
# =========================================================
@app.get("/api/categories")
def list_categories(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    sql = "SELECT * FROM categories"
    params = {}
    if store_id:
        sql += " WHERE store_id=:sid"
        params["sid"] = store_id
    sql += " ORDER BY id"
    return rows_to_list(db.execute(text(sql), params))

@app.post("/api/categories")
def create_category(item: schemas.CategoryIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO categories (store_id, name, parent_id)
        VALUES (:store_id, :name, :parent_id) RETURNING id
    """), item.dict()).scalar()
    db.commit()
    return {"id": rid, "message": "创建成功"}

# =========================================================
# 7. 原材料
# =========================================================
@app.get("/api/materials")
def list_materials(store_id: Optional[int] = None,
                   keyword: str = "",
                   db: Session = Depends(get_db)):
    sql = "SELECT * FROM materials WHERE 1=1"
    params = {}
    if store_id:
        sql += " AND store_id=:sid"
        params["sid"] = store_id
    if keyword:
        sql += " AND name ILIKE :kw"
        params["kw"] = f"%{keyword}%"
    sql += " ORDER BY id DESC"
    return rows_to_list(db.execute(text(sql), params))

@app.get("/api/materials/{mid}")
def get_material(mid: int, db: Session = Depends(get_db)):
    row = db.execute(text("SELECT * FROM materials WHERE id=:id"), {"id": mid}).mappings().first()
    if not row:
        raise HTTPException(404, "原材料不存在")
    return dict(row)

@app.post("/api/materials")
def create_material(item: schemas.MaterialIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO materials (store_id, name, category_id, unit, spec, purchase_unit,
            purchase_to_base_ratio, safety_stock, shelf_life_days, is_perishable, latest_purchase_price)
        VALUES (:store_id, :name, :category_id, :unit, :spec, :purchase_unit,
            :purchase_to_base_ratio, :safety_stock, :shelf_life_days, :is_perishable, :latest_purchase_price)
        RETURNING id
    """), item.dict()).scalar()
    db.commit()
    return {"id": rid, "message": "创建成功"}

@app.put("/api/materials/{mid}")
def update_material(mid: int, item: schemas.MaterialIn, db: Session = Depends(get_db)):
    params = item.dict()
    params["id"] = mid
    db.execute(text("""
        UPDATE materials SET store_id=:store_id, name=:name, category_id=:category_id,
        unit=:unit, spec=:spec, purchase_unit=:purchase_unit,
        purchase_to_base_ratio=:purchase_to_base_ratio, safety_stock=:safety_stock,
        shelf_life_days=:shelf_life_days, is_perishable=:is_perishable,
        latest_purchase_price=:latest_purchase_price, updated_at=NOW()
        WHERE id=:id
    """), params)
    db.commit()
    return {"message": "更新成功"}

@app.delete("/api/materials/{mid}")
def delete_material(mid: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM materials WHERE id=:id"), {"id": mid})
    db.commit()
    return {"message": "删除成功"}

# =========================================================
# 8. 菜品
# =========================================================
@app.get("/api/dishes")
def list_dishes(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    sql = "SELECT * FROM dishes"
    params = {}
    if store_id:
        sql += " WHERE store_id=:sid"
        params["sid"] = store_id
    sql += " ORDER BY id DESC"
    return rows_to_list(db.execute(text(sql), params))

@app.post("/api/dishes")
def create_dish(item: schemas.DishIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO dishes (store_id, name, category_id, selling_price, pos_sku, status)
        VALUES (:store_id, :name, :category_id, :selling_price, :pos_sku, :status)
        RETURNING id
    """), item.dict()).scalar()
    db.commit()
    return {"id": rid, "message": "创建成功"}

@app.put("/api/dishes/{did}")
def update_dish(did: int, item: schemas.DishIn, db: Session = Depends(get_db)):
    params = item.dict()
    params["id"] = did
    db.execute(text("""
        UPDATE dishes SET store_id=:store_id, name=:name, category_id=:category_id,
        selling_price=:selling_price, pos_sku=:pos_sku, status=:status, updated_at=NOW()
        WHERE id=:id
    """), params)
    db.commit()
    return {"message": "更新成功"}

@app.delete("/api/dishes/{did}")
def delete_dish(did: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM dishes WHERE id=:id"), {"id": did})
    db.commit()
    return {"message": "删除成功"}

# =========================================================
# 9. BOM 配方
# =========================================================
@app.get("/api/bom")
def list_bom(dish_id: Optional[int] = None, db: Session = Depends(get_db)):
    sql = """
        SELECT b.*, m.name AS material_name, m.unit AS material_unit
        FROM bom b
        LEFT JOIN materials m ON b.material_id = m.id
        WHERE 1=1
    """
    params = {}
    if dish_id:
        sql += " AND b.dish_id=:did"
        params["did"] = dish_id
    sql += " ORDER BY b.id"
    return rows_to_list(db.execute(text(sql), params))

@app.post("/api/bom")
def create_bom(item: schemas.BomItemIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO bom (dish_id, material_id, quantity, unit, loss_rate, version, is_active)
        VALUES (:dish_id, :material_id, :quantity, :unit, :loss_rate, :version, :is_active)
        RETURNING id
    """), item.dict()).scalar()
    db.commit()
    return {"id": rid, "message": "创建成功"}

@app.delete("/api/bom/{bid}")
def delete_bom(bid: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM bom WHERE id=:id"), {"id": bid})
    db.commit()
    return {"message": "删除成功"}

# =========================================================
# 10. 采购单
# =========================================================
@app.get("/api/purchase_orders")
def list_purchase_orders(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    sql = """
        SELECT po.*, s.name AS supplier_name
        FROM purchase_orders po
        LEFT JOIN suppliers s ON po.supplier_id = s.id
        WHERE 1=1
    """
    params = {}
    if store_id:
        sql += " AND po.store_id=:sid"
        params["sid"] = store_id
    sql += " ORDER BY po.id DESC"
    return rows_to_list(db.execute(text(sql), params))

@app.get("/api/purchase_orders/{oid}/items")
def list_purchase_items(oid: int, db: Session = Depends(get_db)):
    sql = """
        SELECT poi.*, m.name AS material_name
        FROM purchase_order_items poi
        LEFT JOIN materials m ON poi.material_id = m.id
        WHERE poi.purchase_order_id=:oid
        ORDER BY poi.id
    """
    return rows_to_list(db.execute(text(sql), {"oid": oid}))

@app.post("/api/purchase_orders")
def create_purchase_order(item: schemas.PurchaseOrderIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO purchase_orders (store_id, supplier_id, order_no, status, created_by)
        VALUES (:store_id, :supplier_id, :order_no, :status, :created_by)
        RETURNING id
    """), item.dict()).scalar()
    db.commit()
    return {"id": rid, "message": "创建成功"}

@app.post("/api/purchase_order_items")
def create_purchase_item(item: schemas.PurchaseItemIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO purchase_order_items
        (purchase_order_id, material_id, quantity, unit_price, amount, tax_amount)
        VALUES (:purchase_order_id, :material_id, :quantity, :unit_price, :amount, :tax_amount)
        RETURNING id
    """), item.dict()).scalar()
    db.commit()
    return {"id": rid, "message": "创建成功"}

# =========================================================
# 11. 入库单
# =========================================================
@app.get("/api/stock_in")
def list_stock_in(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    sql = """
        SELECT si.*, w.name AS warehouse_name
        FROM stock_in si
        LEFT JOIN warehouses w ON si.warehouse_id = w.id
        WHERE 1=1
    """
    params = {}
    if store_id:
        sql += " AND si.store_id=:sid"
        params["sid"] = store_id
    sql += " ORDER BY si.id DESC"
    return rows_to_list(db.execute(text(sql), params))

@app.post("/api/stock_in")
def create_stock_in(item: schemas.StockInIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO stock_in (store_id, warehouse_id, source_type, source_id, operator_id)
        VALUES (:store_id, :warehouse_id, :source_type, :source_id, :operator_id)
        RETURNING id
    """), item.dict()).scalar()
    db.commit()
    return {"id": rid, "message": "创建成功"}

@app.post("/api/stock_in_items")
def create_stock_in_item(item: schemas.StockInItemIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO stock_in_items
        (stock_in_id, material_id, quantity, unit_cost, batch_no, production_date, expire_date)
        VALUES (:stock_in_id, :material_id, :quantity, :unit_cost, :batch_no, :production_date, :expire_date)
        RETURNING id
    """), item.dict()).scalar()
    # 同步更新实时库存
    db.execute(text("""
        INSERT INTO inventory (store_id, warehouse_id, material_id, quantity, avg_cost)
        SELECT si.store_id, si.warehouse_id, :material_id, :quantity, :unit_cost
        FROM stock_in si WHERE si.id=:stock_in_id
        ON CONFLICT (warehouse_id, material_id)
        DO UPDATE SET quantity = inventory.quantity + :quantity, updated_at = NOW()
    """), {
        "material_id": item.material_id,
        "quantity": item.quantity,
        "unit_cost": item.unit_cost,
        "stock_in_id": item.stock_in_id
    })
    db.commit()
    return {"id": rid, "message": "入库成功"}

# =========================================================
# 12. 出库单
# =========================================================
@app.get("/api/stock_out")
def list_stock_out(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    sql = """
        SELECT so.*, w.name AS warehouse_name
        FROM stock_out so
        LEFT JOIN warehouses w ON so.warehouse_id = w.id
        WHERE 1=1
    """
    params = {}
    if store_id:
        sql += " AND so.store_id=:sid"
        params["sid"] = store_id
    sql += " ORDER BY so.id DESC"
    return rows_to_list(db.execute(text(sql), params))

@app.post("/api/stock_out")
def create_stock_out(item: schemas.StockOutIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO stock_out (store_id, warehouse_id, out_type, source_id, operator_id)
        VALUES (:store_id, :warehouse_id, :out_type, :source_id, :operator_id)
        RETURNING id
    """), item.dict()).scalar()
    db.commit()
    return {"id": rid, "message": "创建成功"}

@app.post("/api/stock_out_items")
def create_stock_out_item(item: schemas.StockOutItemIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO stock_out_items (stock_out_id, material_id, quantity, cost_amount)
        VALUES (:stock_out_id, :material_id, :quantity, :cost_amount)
        RETURNING id
    """), item.dict()).scalar()
    # 扣减库存
    db.execute(text("""
        UPDATE inventory SET quantity = quantity - :qty, updated_at = NOW()
        WHERE warehouse_id = (SELECT warehouse_id FROM stock_out WHERE id=:soid)
          AND material_id = :mid
    """), {"qty": item.quantity, "soid": item.stock_out_id, "mid": item.material_id})
    db.commit()
    return {"id": rid, "message": "出库成功"}

# =========================================================
# 13. 库存
# =========================================================
@app.get("/api/inventory")
def list_inventory(store_id: Optional[int] = None,
                   warehouse_id: Optional[int] = None,
                   db: Session = Depends(get_db)):
    sql = """
        SELECT i.*, m.name AS material_name, m.unit AS material_unit,
               m.safety_stock, w.name AS warehouse_name
        FROM inventory i
        LEFT JOIN materials m ON i.material_id = m.id
        LEFT JOIN warehouses w ON i.warehouse_id = w.id
        WHERE 1=1
    """
    params = {}
    if store_id:
        sql += " AND i.store_id=:sid"
        params["sid"] = store_id
    if warehouse_id:
        sql += " AND i.warehouse_id=:wid"
        params["wid"] = warehouse_id
    sql += " ORDER BY i.id DESC"
    return rows_to_list(db.execute(text(sql), params))

@app.get("/api/inventory/warning")
def inventory_warning(store_id: int = 1, db: Session = Depends(get_db)):
    sql = """
        SELECT i.*, m.name AS material_name, m.unit AS material_unit, m.safety_stock
        FROM inventory i
        JOIN materials m ON i.material_id = m.id
        WHERE i.store_id=:sid AND i.quantity <= m.safety_stock
        ORDER BY i.quantity ASC
    """
    return rows_to_list(db.execute(text(sql), {"sid": store_id}))

# =========================================================
# 14. 盘点单
# =========================================================
@app.get("/api/stock_take")
def list_stock_take(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    sql = """
        SELECT st.*, w.name AS warehouse_name
        FROM stock_take st
        LEFT JOIN warehouses w ON st.warehouse_id = w.id
        WHERE 1=1
    """
    params = {}
    if store_id:
        sql += " AND st.store_id=:sid"
        params["sid"] = store_id
    sql += " ORDER BY st.id DESC"
    return rows_to_list(db.execute(text(sql), params))

@app.post("/api/stock_take")
def create_stock_take(item: schemas.StockTakeIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO stock_take (store_id, warehouse_id, take_date, status, operator_id)
        VALUES (:store_id, :warehouse_id, :take_date, :status, :operator_id)
        RETURNING id
    """), item.dict()).scalar()
    db.commit()
    return {"id": rid, "message": "创建成功"}

@app.post("/api/stock_take_items")
def create_stock_take_item(item: schemas.StockTakeItemIn, db: Session = Depends(get_db)):
    diff = item.actual_quantity - item.book_quantity
    rid = db.execute(text("""
        INSERT INTO stock_take_items (stock_take_id, material_id, book_quantity, actual_quantity, diff_quantity)
        VALUES (:stock_take_id, :material_id, :book_quantity, :actual_quantity, :diff_quantity)
        RETURNING id
    """), {**item.dict(), "diff_quantity": diff}).scalar()
    # 盘点差异直接覆盖库存
    db.execute(text("""
        UPDATE inventory SET quantity=:qty, updated_at=NOW()
        WHERE warehouse_id = (SELECT warehouse_id FROM stock_take WHERE id=:stid)
          AND material_id=:mid
    """), {"qty": item.actual_quantity, "stid": item.stock_take_id, "mid": item.material_id})
    db.commit()
    return {"id": rid, "diff": diff, "message": "盘点成功"}

# =========================================================
# 15. 财务报表
# =========================================================
@app.get("/api/reports/revenue_daily")
def list_revenue_daily(store_id: int = 1, db: Session = Depends(get_db)):
    return rows_to_list(db.execute(text("""
        SELECT * FROM revenue_daily WHERE store_id=:sid ORDER BY revenue_date DESC LIMIT 30
    """), {"sid": store_id}))

@app.get("/api/reports/cost_daily")
def list_cost_daily(store_id: int = 1, db: Session = Depends(get_db)):
    return rows_to_list(db.execute(text("""
        SELECT * FROM cost_daily WHERE store_id=:sid ORDER BY cost_date DESC LIMIT 30
    """), {"sid": store_id}))

@app.get("/api/reports/profit_daily")
def list_profit_daily(store_id: int = 1, db: Session = Depends(get_db)):
    return rows_to_list(db.execute(text("""
        SELECT * FROM profit_daily WHERE store_id=:sid ORDER BY profit_date DESC LIMIT 30
    """), {"sid": store_id}))

@app.get("/api/reports/tax_monthly")
def list_tax_monthly(store_id: int = 1, db: Session = Depends(get_db)):
    return rows_to_list(db.execute(text("""
        SELECT * FROM tax_monthly WHERE store_id=:sid ORDER BY period DESC
    """), {"sid": store_id}))

@app.get("/api/reports/tax_yearly")
def list_tax_yearly(store_id: int = 1, db: Session = Depends(get_db)):
    return rows_to_list(db.execute(text("""
        SELECT * FROM tax_yearly WHERE store_id=:sid ORDER BY period DESC
    """), {"sid": store_id}))

# =========================================================
# 16. 固定资产
# =========================================================
@app.get("/api/assets")
def list_assets(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    sql = "SELECT * FROM assets"
    params = {}
    if store_id:
        sql += " WHERE store_id=:sid"
        params["sid"] = store_id
    sql += " ORDER BY id DESC"
    return rows_to_list(db.execute(text(sql), params))

@app.post("/api/assets")
def create_asset(item: schemas.AssetIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO assets (store_id, name, purchase_amount, purchase_date,
            depreciation_method, useful_life_months, residual_rate, monthly_depreciation)
        VALUES (:store_id, :name, :purchase_amount, :purchase_date,
            :depreciation_method, :useful_life_months, :residual_rate, :monthly_depreciation)
        RETURNING id
    """), item.dict()).scalar()
    db.commit()
    return {"id": rid, "message": "创建成功"}

# =========================================================
# 17. POS 导入批次
# =========================================================
@app.get("/api/pos_batches")
def list_pos_batches(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    sql = "SELECT * FROM pos_import_batches"
    params = {}
    if store_id:
        sql += " WHERE store_id=:sid"
        params["sid"] = store_id
    sql += " ORDER BY id DESC"
    return rows_to_list(db.execute(text(sql), params))

@app.post("/api/pos_batches")
def create_pos_batch(item: schemas.PosImportIn, db: Session = Depends(get_db)):
    rid = db.execute(text("""
        INSERT INTO pos_import_batches
        (store_id, file_name, import_date, status, total_rows, matched_rows, unmatched_rows)
        VALUES (:store_id, :file_name, :import_date, :status, :total_rows, :matched_rows, :unmatched_rows)
        RETURNING id
    """), item.dict()).scalar()
    db.commit()
    return {"id": rid, "message": "创建成功"}

# =========================================================
# 18. 销售流水
# =========================================================
@app.get("/api/sales_records")
def list_sales_records(store_id: Optional[int] = None,
                       sale_date: Optional[str] = None,
                       db: Session = Depends(get_db)):
    sql = "SELECT * FROM sales_records WHERE 1=1"
    params = {}
    if store_id:
        sql += " AND store_id=:sid"
        params["sid"] = store_id
    if sale_date:
        sql += " AND sale_date=:sd"
        params["sd"] = sale_date
    sql += " ORDER BY id DESC LIMIT 500"
    return rows_to_list(db.execute(text(sql), params))

# =========================================================
# 19. 健康检查
# =========================================================
@app.get("/db-test")
def db_test(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' ORDER BY table_name
    """))
    return {"tables": [r[0] for r in result]}

# =========================================================
# 20. 静态文件（前端）
# =========================================================
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html")

# =========================================================
# 补充：仓库、分类、门店、用户 的编辑（PUT）接口
# =========================================================

@app.put("/api/warehouses/{wid}")
def update_warehouse(wid: int, item: schemas.WarehouseIn, db: Session = Depends(get_db)):
    params = item.dict()
    params["id"] = wid
    db.execute(text("UPDATE warehouses SET store_id=:store_id, name=:name, type=:type WHERE id=:id"), params)
    db.commit()
    return {"message": "更新成功"}

@app.put("/api/categories/{cid}")
def update_category(cid: int, item: schemas.CategoryIn, db: Session = Depends(get_db)):
    params = item.dict()
    params["id"] = cid
    db.execute(text("UPDATE categories SET store_id=:store_id, name=:name, parent_id=:parent_id WHERE id=:id"), params)
    db.commit()
    return {"message": "更新成功"}

@app.put("/api/stores/{sid}")
def update_store(sid: int, item: schemas.StoreIn, db: Session = Depends(get_db)):
    params = item.dict()
    params["id"] = sid
    db.execute(text("UPDATE stores SET name=:name, address=:address, tax_rate=:tax_rate WHERE id=:id"), params)
    db.commit()
    return {"message": "更新成功"}

@app.put("/api/users/{uid}")
def update_user(uid: int, item: schemas.UserIn, db: Session = Depends(get_db)):
    params = item.dict()
    params["id"] = uid
    db.execute(text("""
        UPDATE users SET store_id=:store_id, auth_uid=:auth_uid, name=:name,
        role=:role, phone=:phone, status=:status WHERE id=:id
    """), params)
    db.commit()
    return {"message": "更新成功"}


