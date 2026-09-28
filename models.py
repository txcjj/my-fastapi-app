from sqlalchemy import Column, BigInteger, String, Integer, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Goods(Base):
    __tablename__ = "goods"
    id = Column(BigInteger, primary_key=True)
    barcode = Column(String)
    name = Column(String, nullable=False)
    category_id = Column(BigInteger)
    unit = Column(String)
    purchase_price = Column(Numeric(10, 2))
    sale_price = Column(Numeric(10, 2))
    stock = Column(Integer)
    stock_warn = Column(Integer)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class Category(Base):
    __tablename__ = "categories"
    id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=False)
    parent_id = Column(BigInteger)

class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(BigInteger, primary_key=True)
    name = Column(String)
    location = Column(String)