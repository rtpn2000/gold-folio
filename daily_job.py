from agg import aggregate_gold_prices
from src.database import SessionLocal
from src.crud import upsert_gold_prices
from src.train_model import train_and_save_arima

from datetime import datetime


def parse_iso_to_date(ts: str):
    # "2026-03-02T23:42:54.431481Z" -> date(2026, 3, 2)
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).date()


def normalize_from_agg(agg: dict):
    if not isinstance(agg, dict):
        return []

    ts = agg.get("timestamp")
    prices_list = agg.get("prices")

    if not ts or not isinstance(prices_list, list):
        return []

    day = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()

    usd_price = None
    inr_price = None

    for item in prices_list:
        if not isinstance(item, dict):
            continue

        if item.get("price_per_gram_usd") and usd_price is None:
            usd_price = float(item["price_per_gram_usd"])

        if item.get("price_per_gram_inr") and inr_price is None:
            inr_price = float(item["price_per_gram_inr"])

    if usd_price is None:
        return []

    return [{
        "date": day,
        "price_per_gram_usd": usd_price,
        "price_per_gram_inr": inr_price
    }]

def main():
    agg = aggregate_gold_prices()
    print("AGG OUTPUT KEYS:", list(agg.keys()) if isinstance(agg, dict) else type(agg))
    print("AGG TIMESTAMP:", agg.get("timestamp") if isinstance(agg, dict) else None)
    print("AGG SOURCES:", agg.get("sources") if isinstance(agg, dict) else None)

    records = normalize_from_agg(agg)
    print("NORMALIZED:", records)

    if not records:
        print("No records produced; nothing to insert.")
        return

    db = SessionLocal()
    try:
        upsert_gold_prices(db, records)
        print(f"Upserted {len(records)} row(s) into gold_prices.")
    finally:
        db.close()

    res = train_and_save_arima()
    print("Training result:", res)


if __name__ == "__main__":
    main()