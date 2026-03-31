from pathlib import Path

import pandas as pd

from src.crud import upsert_gold_prices
from src.database import SessionLocal


CSV_PATH = Path("data/raw/GoldPrices _(2013-2023).csv")
OUNCE_TO_GRAMS = 31.1035


def build_records(csv_path: Path) -> list[dict]:
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y", errors="coerce")
    df["Price"] = (
        df["Price"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.replace('"', "", regex=False)
        .str.strip()
    )
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")

    df = df.dropna(subset=["Date", "Price"]).copy()
    df["price_per_gram_usd"] = df["Price"] / OUNCE_TO_GRAMS
    df["price_per_gram_inr"] = None
    df["date"] = df["Date"].dt.date

    df = (
        df[["date", "price_per_gram_usd", "price_per_gram_inr"]]
        .sort_values("date")
        .drop_duplicates(subset=["date"])
    )

    return df.to_dict(orient="records")


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    records = build_records(CSV_PATH)

    db = SessionLocal()
    try:
        count = upsert_gold_prices(db, records)
    finally:
        db.close()

    if records:
        print(
            {
                "upserted": count,
                "rows_prepared": len(records),
                "first_date": str(records[0]["date"]),
                "last_date": str(records[-1]["date"]),
                "csv_path": str(CSV_PATH),
            }
        )
    else:
        print({"upserted": 0, "rows_prepared": 0, "csv_path": str(CSV_PATH)})


if __name__ == "__main__":
    main()
