from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from agg import aggregate_gold_prices
from src.crud import get_history, get_latest_price, upsert_gold_prices
from src.database import SessionLocal, engine
from src.models import Base
from src.predict import forecast


app = FastAPI(title="Gold Dashboard API")
Base.metadata.create_all(bind=engine)

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_PATH = BASE_DIR / "static" / "index.html"

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def to_float(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def serialize_price(row):
    return {
        "date": row.date.isoformat(),
        "price_per_gram_usd": to_float(row.price_per_gram_usd),
        "price_per_gram_inr": to_float(row.price_per_gram_inr),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def normalize_records(payload):
    if not isinstance(payload, dict):
        return []

    timestamp = payload.get("timestamp")
    prices = payload.get("prices", [])
    if not timestamp or not isinstance(prices, list):
        return []

    day = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date()
    usd_price = None
    inr_price = None

    for item in prices:
        if not isinstance(item, dict):
            continue
        if usd_price is None and item.get("price_per_gram_usd") is not None:
            usd_price = float(item["price_per_gram_usd"])
        if inr_price is None and item.get("price_per_gram_inr") is not None:
            inr_price = float(item["price_per_gram_inr"])

    if usd_price is None:
        return []

    return [{
        "date": day,
        "price_per_gram_usd": usd_price,
        "price_per_gram_inr": inr_price,
    }]


@app.get("/")
def root():
    return {"status": "Gold Dashboard Running", "dashboard": "/dashboard"}


@app.get("/dashboard")
def dashboard():
    if not DASHBOARD_PATH.exists():
        raise HTTPException(status_code=404, detail="Dashboard file not found.")
    return FileResponse(DASHBOARD_PATH)


@app.get("/aggregate")
def run_aggregation(db: Session = Depends(get_db)):
    data = aggregate_gold_prices()
    if data.get("error"):
        raise HTTPException(status_code=502, detail=data["error"])

    records = normalize_records(data)
    if not records:
        raise HTTPException(status_code=500, detail="Aggregation returned no usable records.")

    rows = upsert_gold_prices(db, records)
    latest = get_latest_price(db)

    return {
        "message": "Saved to DB",
        "rows": rows,
        "sources": data.get("sources", []),
        "latest": serialize_price(latest) if latest else None,
    }


@app.get("/api/summary")
def api_summary(db: Session = Depends(get_db)):
    history = list(reversed(get_history(db, days=365)))
    latest = history[-1] if history else None
    previous = history[-2] if len(history) > 1 else None

    if latest and previous:
        usd_change = to_float(latest.price_per_gram_usd) - to_float(previous.price_per_gram_usd)
        inr_latest = to_float(latest.price_per_gram_inr)
        inr_previous = to_float(previous.price_per_gram_inr)
        inr_change = None if inr_latest is None or inr_previous is None else inr_latest - inr_previous
    else:
        usd_change = None
        inr_change = None

    return {
        "latest": serialize_price(latest) if latest else None,
        "previous": serialize_price(previous) if previous else None,
        "change": {
            "usd": usd_change,
            "inr": inr_change,
        },
        "history_points": len(history),
    }


@app.get("/api/history")
def api_history(
    days: int = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
):
    history = list(reversed(get_history(db, days=days)))
    return {"items": [serialize_price(row) for row in history]}


@app.get("/api/forecast")
def api_forecast(days: int = Query(default=30, ge=1, le=180)):
    result = forecast(days=days)
    if result.get("error"):
        return {"items": [], "error": result["error"], "method": None}
    return result


if __name__ == "__main__":
    data = aggregate_gold_prices()
    print("Aggregated Gold Prices:\n", data)
