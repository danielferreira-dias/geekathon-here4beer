import time
import uuid
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from db import SessionLocal
import models as db_models


def _now_scenario_id() -> str:
    return f"scenario_{int(time.time())}"


def _clone_run(session: Session, baseline_run_id: Optional[str]) -> tuple[str, str]:
    """
    Clone baseline run rows to a new run_id. If baseline_run_id is None, pick the latest.
    Returns (new_run_id, baseline_run_id).
    """
    if baseline_run_id is None:
        from sqlalchemy import desc
        row = session.execute(select(db_models.Run.id).order_by(desc(db_models.Run.created_at)).limit(1)).first()
        baseline_run_id = row[0] if row else None
        if baseline_run_id is None:
            raise ValueError("No baseline run found")

    new_run_id = _now_scenario_id()
    # Create Run
    new_run = db_models.Run(id=new_run_id, notes=f"Scenario cloned from {baseline_run_id}")
    session.add(new_run)
    session.flush()

    # Clone forecasts
    forecasts = session.execute(select(db_models.Forecast).where(db_models.Forecast.run_id == baseline_run_id)).scalars().all()
    for f in forecasts:
        session.add(
            db_models.Forecast(
                run_id=new_run_id,
                sku=f.sku,
                forecasted_demand=f.forecasted_demand,
                confidence_or_reason=f.confidence_or_reason,
            )
        )

    # Clone production plans
    plans = session.execute(select(db_models.ProductionPlan).where(db_models.ProductionPlan.run_id == baseline_run_id)).scalars().all()
    for p in plans:
        session.add(
            db_models.ProductionPlan(
                run_id=new_run_id,
                sku=p.sku,
                forecasted_demand=p.forecasted_demand,
                current_inventory=p.current_inventory,
                suggested_production=p.suggested_production,
            )
        )

    # Clone raw material orders
    orders = session.execute(select(db_models.RawMaterialOrder).where(db_models.RawMaterialOrder.run_id == baseline_run_id)).scalars().all()
    for o in orders:
        session.add(
            db_models.RawMaterialOrder(
                run_id=new_run_id,
                material_id=o.material_id,
                needed_qty_kg=o.needed_qty_kg,
                current_stock_kg=o.current_stock_kg,
                suggested_order_kg=o.suggested_order_kg,
            )
        )

    return new_run_id, baseline_run_id


def _recompute_for_consistency(session: Session, run_id: str) -> None:
    """
    Very simple recomputation:
    - For ProductionPlan: suggested_production = max(forecasted_demand - current_inventory, 0)
    - For RawMaterialOrder: suggested_order_kg = max(needed_qty_kg - current_stock_kg, 0)
    """
    plans = session.execute(select(db_models.ProductionPlan).where(db_models.ProductionPlan.run_id == run_id)).scalars().all()
    for p in plans:
        p.suggested_production = max(int(p.forecasted_demand) - int(p.current_inventory), 0)

    orders = session.execute(select(db_models.RawMaterialOrder).where(db_models.RawMaterialOrder.run_id == run_id)).scalars().all()
    for o in orders:
        o.suggested_order_kg = max(int(o.needed_qty_kg) - int(o.current_stock_kg), 0)


def simulate_scenario(payload: Dict[str, Any]) -> Dict[str, Any]:
    baseline_run_id = payload.get("baseline_run_id")
    demand_multipliers: Optional[Dict[str, float]] = payload.get("demand_multipliers")
    material_caps: Optional[Dict[str, float]] = payload.get("material_caps")

    with SessionLocal() as session:
        new_run_id, baseline_run_id = _clone_run(session, baseline_run_id)

        # Apply demand multipliers to forecasts (and propagate to production plans' forecasted_demand)
        if demand_multipliers:
            forecasts = session.execute(select(db_models.Forecast).where(db_models.Forecast.run_id == new_run_id)).scalars().all()
            sku_to_multiplier = {str(k): float(v) for k, v in demand_multipliers.items()}
            for f in forecasts:
                m = sku_to_multiplier.get(f.sku)
                if m is not None:
                    f.forecasted_demand = int(round(f.forecasted_demand * m))
            # Update production plans forecast to match forecasts if same SKU exists
            plans = session.execute(select(db_models.ProductionPlan).where(db_models.ProductionPlan.run_id == new_run_id)).scalars().all()
            f_map = {f.sku: f.forecasted_demand for f in forecasts}
            for p in plans:
                if p.sku in f_map:
                    p.forecasted_demand = int(f_map[p.sku])

        # Apply material caps to suggested_order_kg
        if material_caps:
            caps = {str(k): float(v) for k, v in material_caps.items()}
            orders = session.execute(select(db_models.RawMaterialOrder).where(db_models.RawMaterialOrder.run_id == new_run_id)).scalars().all()
            for o in orders:
                cap = caps.get(o.material_id)
                if cap is not None:
                    # Cap suggested order
                    o.suggested_order_kg = int(min(o.suggested_order_kg, cap))

        # Recompute internal consistency
        _recompute_for_consistency(session, new_run_id)

        # Totals
        total_forecast = session.execute(
            select(db_models.Forecast).where(db_models.Forecast.run_id == new_run_id)
        ).scalars().all()
        total_prod = session.execute(
            select(db_models.ProductionPlan).where(db_models.ProductionPlan.run_id == new_run_id)
        ).scalars().all()
        total_orders = session.execute(
            select(db_models.RawMaterialOrder).where(db_models.RawMaterialOrder.run_id == new_run_id)
        ).scalars().all()

        totals = {
            "forecast_units": int(sum(f.forecasted_demand for f in total_forecast)),
            "production_units": int(sum(p.suggested_production for p in total_prod)),
            "orders_kg": float(sum(float(o.suggested_order_kg) for o in total_orders)),
        }

        # Baseline totals for summary
        base_forecast = session.execute(
            select(db_models.Forecast).where(db_models.Forecast.run_id == baseline_run_id)
        ).scalars().all()
        base_prod = session.execute(
            select(db_models.ProductionPlan).where(db_models.ProductionPlan.run_id == baseline_run_id)
        ).scalars().all()
        base_orders = session.execute(
            select(db_models.RawMaterialOrder).where(db_models.RawMaterialOrder.run_id == baseline_run_id)
        ).scalars().all()
        base_totals = {
            "forecast_units": int(sum(f.forecasted_demand for f in base_forecast)),
            "production_units": int(sum(p.suggested_production for p in base_prod)),
            "orders_kg": float(sum(float(o.suggested_order_kg) for o in base_orders)),
        }

        summary = (
            f"Scenario {new_run_id} vs {baseline_run_id}: "
            f"forecast {totals['forecast_units']} ({totals['forecast_units'] - base_totals['forecast_units']:+}), "
            f"production {totals['production_units']} ({totals['production_units'] - base_totals['production_units']:+}), "
            f"orders {totals['orders_kg']:.1f}kg ({totals['orders_kg'] - base_totals['orders_kg']:+.1f})"
        )

        session.commit()

        return {
            "new_run_id": new_run_id,
            "baseline_run_id": baseline_run_id,
            "totals": totals,
            "summary": summary,
        }


def diff_runs(payload: Dict[str, Any]) -> Dict[str, Any]:
    base_run_id = payload.get("base_run_id")
    scenario_run_id = payload.get("scenario_run_id")
    if not base_run_id or not scenario_run_id:
        return {"error": "base_run_id and scenario_run_id are required"}

    with SessionLocal() as session:
        # Forecast deltas
        base_f = session.execute(select(db_models.Forecast).where(db_models.Forecast.run_id == base_run_id)).scalars().all()
        scn_f = session.execute(select(db_models.Forecast).where(db_models.Forecast.run_id == scenario_run_id)).scalars().all()
        f_map_base = {f.sku: int(f.forecasted_demand) for f in base_f}
        f_map_scn = {f.sku: int(f.forecasted_demand) for f in scn_f}
        skus = sorted(set(f_map_base) | set(f_map_scn))
        forecast_delta = []
        for sku in skus:
            b = f_map_base.get(sku, 0)
            s = f_map_scn.get(sku, 0)
            forecast_delta.append({"sku": sku, "base": b, "scenario": s, "delta": s - b})

        # Production deltas
        base_p = session.execute(select(db_models.ProductionPlan).where(db_models.ProductionPlan.run_id == base_run_id)).scalars().all()
        scn_p = session.execute(select(db_models.ProductionPlan).where(db_models.ProductionPlan.run_id == scenario_run_id)).scalars().all()
        p_map_base = {p.sku: int(p.suggested_production) for p in base_p}
        p_map_scn = {p.sku: int(p.suggested_production) for p in scn_p}
        skus2 = sorted(set(p_map_base) | set(p_map_scn))
        production_delta = []
        for sku in skus2:
            b = p_map_base.get(sku, 0)
            s = p_map_scn.get(sku, 0)
            production_delta.append({"sku": sku, "base": b, "scenario": s, "delta": s - b})

        # Orders deltas
        base_o = session.execute(select(db_models.RawMaterialOrder).where(db_models.RawMaterialOrder.run_id == base_run_id)).scalars().all()
        scn_o = session.execute(select(db_models.RawMaterialOrder).where(db_models.RawMaterialOrder.run_id == scenario_run_id)).scalars().all()
        o_map_base = {}
        for o in base_o:
            o_map_base[o.material_id] = float(o_map_base.get(o.material_id, 0.0)) + float(o.suggested_order_kg)
        o_map_scn = {}
        for o in scn_o:
            o_map_scn[o.material_id] = float(o_map_scn.get(o.material_id, 0.0)) + float(o.suggested_order_kg)
        mats = sorted(set(o_map_base) | set(o_map_scn))
        orders_delta = []
        for m in mats:
            b = float(o_map_base.get(m, 0.0))
            s = float(o_map_scn.get(m, 0.0))
            orders_delta.append({"material_id": m, "base": b, "scenario": s, "delta": s - b})

        summary = (
            f"Diff {scenario_run_id} vs {base_run_id}: "
            f"Δforecast={sum(d['delta'] for d in forecast_delta)}, "
            f"Δproduction={sum(d['delta'] for d in production_delta)}, "
            f"Δorders={sum(d['delta'] for d in orders_delta):.1f}kg"
        )

        return {
            "forecast_delta": forecast_delta,
            "production_delta": production_delta,
            "orders_delta": orders_delta,
            "summary": summary,
        }
