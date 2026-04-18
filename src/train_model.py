import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

from src.database import SessionLocal
from src.models import GoldPrice
from src.model_store import save_model


def load_series_from_db(target: str = "usd", symbol: str = "XAU"):
    """
    target: "usd" or "inr"
    Returns a pandas Series indexed by date for the selected metal symbol.
    """
    db = SessionLocal()
    try:
        rows = (
            db.query(GoldPrice)
            .filter(GoldPrice.symbol == symbol.upper())
            .order_by(GoldPrice.date.asc())
            .all()
        )

        if target == "inr":
            data = [
                {"date": r.date, "price": float(r.price_per_gram_inr)}
                for r in rows
                if r.price_per_gram_inr is not None
            ]
        else:
            data = [
                {"date": r.date, "price": float(r.price_per_gram_usd)}
                for r in rows
                if r.price_per_gram_usd is not None
            ]

        df = pd.DataFrame(data)
        if df.empty:
            return None

        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        return df["price"]
    finally:
        db.close()


def train_and_save_arima(days_min: int = 30, target: str = "usd"):
    """
    Trains ARIMA on stored daily prices and saves fitted model artifact.
    For MVP: ARIMA(5,1,0).
    """
    series = load_series_from_db(target=target)

    if series is None or len(series) < days_min:
        return {"ok": False, "reason": f"Not enough history in DB (need >= {days_min} points)", "points": int(len(series)) if series is not None else 0}

    model = ARIMA(series, order=(5, 1, 0))
    fitted = model.fit()

    # Save model (include target in filename inside model_store if you want separate models later)
    save_model(fitted)

    return {"ok": True, "target": target, "points": int(len(series))}