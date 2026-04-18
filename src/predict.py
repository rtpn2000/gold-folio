import pandas as pd

from src.train_model import load_series_from_db


def moving_average_forecast(days: int = 30, window: int = 7, target: str = "usd", symbol: str = "XAU"):
    series = load_series_from_db(target=target, symbol=symbol)
    if series is None or series.empty:
        return {"error": "No DB history yet. Ingest prices first."}

    if len(series) < window:
        return {"error": f"Not enough history for a {window}-day moving average forecast."}

    last_date = series.index.max()
    forecast_value = float(series.tail(window).mean())

    future_dates = pd.date_range(
        start=last_date,
        periods=days + 1,
        freq="D",
    )[1:]

    items = [{"date": str(d.date()), "price": forecast_value} for d in future_dates]

    return {
        "items": items,
        "method": f"moving_average_{window}d",
        "window": window,
        "error": None,
    }


def forecast(days: int = 30, symbol: str = "XAU"):
    return moving_average_forecast(days=days, symbol=symbol)