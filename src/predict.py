import pandas as pd
from src.model_store import load_model
from src.database import SessionLocal
from src.models import GoldPrice

def get_last_date():
    db = SessionLocal()
    try:
        row = db.query(GoldPrice).order_by(GoldPrice.date.desc()).first()
        return row.date if row else None
    finally:
        db.close()

def forecast(days: int = 30):
    fitted = load_model()
    if fitted is None:
        return {"error": "Model not trained yet. Run daily job or train once."}

    last_date = get_last_date()
    if last_date is None:
        return {"error": "No DB history yet. Ingest prices first."}

    preds = fitted.forecast(steps=days)

    future_dates = pd.date_range(
        start=pd.to_datetime(last_date),
        periods=days + 1,
        freq="D"
    )[1:]

    return [
        {"date": str(d.date()), "price": float(p)}
        for d, p in zip(future_dates, preds)
    ]