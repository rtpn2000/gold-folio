from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from .models import GoldPrice

def upsert_gold_prices(db: Session, rows: list[dict]) -> int:
    """
    rows: [{"date": datetime.date, "symbol": str, "price_per_gram_usd": float/Decimal, "price_per_gram_inr": float/Decimal}, ...]
    Upserts by date + symbol.
    Returns number of rows attempted (not exact updated/inserted count).
    """
    if not rows:
        return 0

    for row in rows:
        if "symbol" not in row:
            row["symbol"] = "XAU"

    stmt = insert(GoldPrice).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[GoldPrice.date, GoldPrice.symbol],
        set_={
            "price_per_gram_usd": stmt.excluded.price_per_gram_usd,
            "price_per_gram_inr": stmt.excluded.price_per_gram_inr,
        },
    )
    db.execute(stmt)
    db.commit()
    return len(rows)

def get_latest_price(db: Session, symbol: str = "XAU"):
    return (
        db.query(GoldPrice)
        .filter(GoldPrice.symbol == symbol)
        .order_by(GoldPrice.date.desc())
        .first()
    )

def get_history(db: Session, days: int = 365, symbol: str = "XAU"):
    # Simple: last N rows by date (works if you store daily data)
    return (
        db.query(GoldPrice)
        .filter(GoldPrice.symbol == symbol)
        .order_by(GoldPrice.date.desc())
        .limit(days)
        .all()
    )