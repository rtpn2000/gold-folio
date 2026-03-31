import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

from src.database import SessionLocal
from src.models import GoldPrice
from src.model_store import save_model


def load_series_from_db(target: str = "usd"):
    """
    target: "usd" or "inr"
    Returns a pandas Series indexed by date.
    """
    db = SessionLocal()
    try:
        rows = db.query(GoldPrice).order_by(GoldPrice.date.asc()).all()

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
        # Give the series an explicit daily frequency before fitting ARIMA.
        df = df.asfreq("D")
        df["price"] = df["price"].interpolate(method="time")
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


def backtest_arima_holdout(months: int = 2, days_min: int = 30, target: str = "usd"):
    """
    Train on history up to the last `months` months, forecast the holdout window,
    and compare predictions against the actual stored values.
    """
    series = load_series_from_db(target=target)

    if series is None or len(series) < days_min:
        return {
            "ok": False,
            "reason": f"Not enough history in DB (need >= {days_min} points)",
            "points": int(len(series)) if series is not None else 0,
        }

    last_date = series.index.max()
    split_date = last_date - pd.DateOffset(months=months)

    train = series[series.index < split_date]
    test = series[series.index >= split_date]

    if len(train) < days_min:
        return {
            "ok": False,
            "reason": "Training window too small after holdout split.",
            "train_points": int(len(train)),
            "test_points": int(len(test)),
            "split_date": str(split_date.date()),
        }

    if test.empty:
        return {
            "ok": False,
            "reason": "Holdout window produced no test rows.",
            "split_date": str(split_date.date()),
        }

    model = ARIMA(train, order=(5, 1, 0))
    fitted = model.fit()
    preds = fitted.forecast(steps=len(test))

    comparison = pd.DataFrame({
        "date": test.index,
        "actual": test.values,
        "predicted": preds.values,
    })
    comparison["abs_error"] = (comparison["actual"] - comparison["predicted"]).abs()
    comparison["sq_error"] = (comparison["actual"] - comparison["predicted"]) ** 2
    comparison["ape"] = comparison["abs_error"] / comparison["actual"].replace(0, pd.NA)

    mae = float(comparison["abs_error"].mean())
    rmse = float(comparison["sq_error"].mean() ** 0.5)
    mape = float(comparison["ape"].dropna().mean() * 100)

    sample = [
        {
            "date": str(row.date.date()),
            "actual": float(row.actual),
            "predicted": float(row.predicted),
            "abs_error": float(row.abs_error),
        }
        for row in comparison.head(10).itertuples(index=False)
    ]

    return {
        "ok": True,
        "target": target,
        "split_date": str(split_date.date()),
        "train_points": int(len(train)),
        "test_points": int(len(test)),
        "mae": mae,
        "rmse": rmse,
        "mape": mape,
        "sample": sample,
    }


def compare_arima_orders(
    orders: list[tuple[int, int, int]] | None = None,
    months: int = 2,
    days_min: int = 30,
    target: str = "usd",
):
    if orders is None:
        orders = [(1, 1, 1), (2, 1, 2), (3, 1, 3), (5, 1, 0), (5, 1, 1)]

    series = load_series_from_db(target=target)

    if series is None or len(series) < days_min:
        return {
            "ok": False,
            "reason": f"Not enough history in DB (need >= {days_min} points)",
            "points": int(len(series)) if series is not None else 0,
        }

    last_date = series.index.max()
    split_date = last_date - pd.DateOffset(months=months)
    train = series[series.index < split_date]
    test = series[series.index >= split_date]

    if len(train) < days_min or test.empty:
        return {
            "ok": False,
            "reason": "Invalid train/test split for holdout comparison.",
            "train_points": int(len(train)),
            "test_points": int(len(test)),
            "split_date": str(split_date.date()),
        }

    results = []

    for order in orders:
        try:
            model = ARIMA(train, order=order)
            fitted = model.fit()
            preds = fitted.forecast(steps=len(test))

            comparison = pd.DataFrame({
                "actual": test.values,
                "predicted": preds.values,
            })
            abs_error = (comparison["actual"] - comparison["predicted"]).abs()
            sq_error = (comparison["actual"] - comparison["predicted"]) ** 2
            ape = abs_error / comparison["actual"].replace(0, pd.NA)

            results.append({
                "order": order,
                "mae": float(abs_error.mean()),
                "rmse": float(sq_error.mean() ** 0.5),
                "mape": float(ape.dropna().mean() * 100),
                "aic": float(fitted.aic),
            })
        except Exception as exc:
            results.append({
                "order": order,
                "error": str(exc),
            })

    successful = [item for item in results if "error" not in item]
    best = min(successful, key=lambda item: item["mae"]) if successful else None

    return {
        "ok": True,
        "target": target,
        "split_date": str(split_date.date()),
        "train_points": int(len(train)),
        "test_points": int(len(test)),
        "best_by_mae": best,
        "results": results,
    }


def compare_against_baselines(months: int = 2, days_min: int = 30, target: str = "usd"):
    series = load_series_from_db(target=target)

    if series is None or len(series) < days_min:
        return {
            "ok": False,
            "reason": f"Not enough history in DB (need >= {days_min} points)",
            "points": int(len(series)) if series is not None else 0,
        }

    last_date = series.index.max()
    split_date = last_date - pd.DateOffset(months=months)
    train = series[series.index < split_date]
    test = series[series.index >= split_date]

    if len(train) < days_min or test.empty:
        return {
            "ok": False,
            "reason": "Invalid train/test split for baseline comparison.",
            "train_points": int(len(train)),
            "test_points": int(len(test)),
            "split_date": str(split_date.date()),
        }

    def score_predictions(name: str, predicted: pd.Series):
        comparison = pd.DataFrame({
            "actual": test.values,
            "predicted": predicted.values,
        })
        abs_error = (comparison["actual"] - comparison["predicted"]).abs()
        sq_error = (comparison["actual"] - comparison["predicted"]) ** 2
        ape = abs_error / comparison["actual"].replace(0, pd.NA)
        return {
            "model": name,
            "mae": float(abs_error.mean()),
            "rmse": float(sq_error.mean() ** 0.5),
            "mape": float(ape.dropna().mean() * 100),
        }

    arima_model = ARIMA(train, order=(5, 1, 1)).fit()
    arima_preds = arima_model.forecast(steps=len(test))

    last_value = float(train.iloc[-1])
    naive_preds = pd.Series([last_value] * len(test), index=test.index)

    moving_average = float(train.tail(7).mean())
    ma7_preds = pd.Series([moving_average] * len(test), index=test.index)

    results = [
        score_predictions("arima_5_1_1", arima_preds),
        score_predictions("naive_last_value", naive_preds),
        score_predictions("moving_average_7d", ma7_preds),
    ]

    best = min(results, key=lambda item: item["mae"])

    return {
        "ok": True,
        "target": target,
        "split_date": str(split_date.date()),
        "train_points": int(len(train)),
        "test_points": int(len(test)),
        "best_by_mae": best,
        "results": results,
    }
