import argparse
import sys
from datetime import date, datetime
from pathlib import Path

import yfinance as yf

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import ounce_to_g
from src.crud import upsert_gold_prices
from src.database import SessionLocal
from src.fetch_yfinance import METAL_TICKERS
from src.models import GoldPrice


def _close_series(ticker: str, start: str, end: str | None):
    history = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
    if history.empty or "Close" not in history:
        return None
    series = history["Close"].dropna()
    series.index = series.index.date
    return series


def build_rows(symbol: str, start: str, end: str | None):
    symbol = symbol.upper()
    ticker = METAL_TICKERS.get(symbol)
    if not ticker:
        raise ValueError(f"Unsupported metal symbol: {symbol}")

    metal_close = _close_series(ticker, start, end)
    fx_close = _close_series("INR=X", start, end)
    if metal_close is None or metal_close.empty:
        raise RuntimeError(f"No Yahoo Finance history for {symbol} ({ticker})")
    if fx_close is None or fx_close.empty:
        raise RuntimeError("No Yahoo Finance history for USD/INR (INR=X)")

    rows = []
    for day, price_per_ounce_usd in metal_close.items():
        fx_rate = fx_close.get(day)
        price_per_gram_usd = float(price_per_ounce_usd) / ounce_to_g
        rows.append({
            "date": day if isinstance(day, date) else day.date(),
            "symbol": symbol,
            "price_per_gram_usd": round(price_per_gram_usd, 4),
            "price_per_gram_inr": round(price_per_gram_usd * float(fx_rate), 4) if fx_rate is not None else None,
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description="Backfill gold_prices from Yahoo Finance history.")
    parser.add_argument("--symbols", nargs="+", default=["XAU"], choices=sorted(METAL_TICKERS))
    parser.add_argument("--start", default="2010-01-01", help="Inclusive start date, YYYY-MM-DD.")
    parser.add_argument("--end", default=None, help="Exclusive end date, YYYY-MM-DD. Defaults to today/latest.")
    parser.add_argument(
        "--replace-all",
        action="store_true",
        help="Delete all rows from gold_prices before inserting Yahoo Finance rows.",
    )
    parser.add_argument(
        "--replace-symbols",
        action="store_true",
        help="Delete existing rows only for the requested symbols before inserting Yahoo Finance rows.",
    )
    args = parser.parse_args()

    datetime.strptime(args.start, "%Y-%m-%d")
    if args.end:
        datetime.strptime(args.end, "%Y-%m-%d")

    db = SessionLocal()
    try:
        if args.replace_all:
            deleted = db.query(GoldPrice).delete(synchronize_session=False)
            db.commit()
            print(f"Deleted {deleted} existing gold_prices rows.")
        elif args.replace_symbols:
            deleted = (
                db.query(GoldPrice)
                .filter(GoldPrice.symbol.in_([symbol.upper() for symbol in args.symbols]))
                .delete(synchronize_session=False)
            )
            db.commit()
            print(f"Deleted {deleted} existing rows for: {', '.join(args.symbols)}.")

        total = 0
        for symbol in args.symbols:
            rows = build_rows(symbol, args.start, args.end)
            count = upsert_gold_prices(db, rows)
            total += count
            print(f"{symbol}: upserted {count} Yahoo Finance rows")
        print(f"Done. Upserted {total} total rows.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
