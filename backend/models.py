from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from db import Base


class Run(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)
    summary_text = Column(Text, nullable=True)

    # Relationships
    forecasts = relationship("Forecast", back_populates="run", cascade="all, delete-orphan")
    production_plans = relationship("ProductionPlan", back_populates="run", cascade="all, delete-orphan")
    raw_material_orders = relationship("RawMaterialOrder", back_populates="run", cascade="all, delete-orphan")
    risk_alerts = relationship("RiskAlert", back_populates="run", cascade="all, delete-orphan")


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False)
    sku = Column(String, nullable=False)
    forecasted_demand = Column(Integer, nullable=False)
    confidence_or_reason = Column(Text, nullable=True)

    run = relationship("Run", back_populates="forecasts")


class ProductionPlan(Base):
    __tablename__ = "production_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False)
    sku = Column(String, nullable=False)
    forecasted_demand = Column(Integer, nullable=False)
    current_inventory = Column(Integer, nullable=False)
    suggested_production = Column(Integer, nullable=False)

    run = relationship("Run", back_populates="production_plans")


class RawMaterialOrder(Base):
    __tablename__ = "raw_material_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False)
    material_id = Column(String, nullable=False)
    needed_qty_kg = Column(Integer, nullable=False)
    current_stock_kg = Column(Integer, nullable=False)
    suggested_order_kg = Column(Integer, nullable=False)

    run = relationship("Run", back_populates="raw_material_orders")


class RiskAlert(Base):
    __tablename__ = "risk_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False)
    alert_type = Column(String, nullable=False)
    sku_or_material = Column(String, nullable=True)
    description = Column(Text, nullable=False)

    run = relationship("Run", back_populates="risk_alerts")
