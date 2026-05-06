from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.dialects.postgresql import insert

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from src.models import Base, GoldPrice


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is missing. Add it to .env or your shell environment.")
    return value


def ensure_target_schema(target_engine) -> None:
    Base.metadata.create_all(bind=target_engine)

    inspector = inspect(target_engine)
    columns = [col["name"] for col in inspector.get_columns("gold_prices")]
    if "symbol" not in columns:
        with target_engine.begin() as conn:
            conn.execute(text("ALTER TABLE gold_prices ADD COLUMN symbol VARCHAR(6) NOT NULL DEFAULT 'XAU'"))
            conn.execute(text("ALTER TABLE gold_prices ALTER COLUMN symbol DROP DEFAULT"))

    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("gold_prices")
        if constraint.get("name")
    }
    if "uq_date_symbol" not in unique_constraints:
        with target_engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE gold_prices "
                    "ADD CONSTRAINT uq_date_symbol UNIQUE (date, symbol)"
                )
            )


def numeric_or_none(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def load_source_rows(source_engine) -> list[dict]:
    metadata = MetaData()
    source_table = Table("gold_prices", metadata, autoload_with=source_engine)
    source_columns = source_table.c.keys()

    with source_engine.connect() as conn:
        rows = conn.execute(select(source_table).order_by(source_table.c.date.asc())).mappings().all()

    records = []
    for row in rows:
        records.append(
            {
                "date": row["date"],
                "symbol": str(row["symbol"]).upper() if "symbol" in source_columns and row["symbol"] else "XAU",
                "price_per_gram_usd": numeric_or_none(row["price_per_gram_usd"]),
                "price_per_gram_inr": numeric_or_none(row["price_per_gram_inr"]),
                "created_at": row["created_at"] if "created_at" in source_columns else None,
            }
        )
    return records


def upsert_target_rows(target_engine, records: list[dict]) -> None:
    if not records:
        return

    stmt = insert(GoldPrice).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=[GoldPrice.date, GoldPrice.symbol],
        set_={
            "price_per_gram_usd": stmt.excluded.price_per_gram_usd,
            "price_per_gram_inr": stmt.excluded.price_per_gram_inr,
            "created_at": stmt.excluded.created_at,
        },
    )

    with target_engine.begin() as conn:
        conn.execute(stmt)


def main() -> None:
    load_dotenv()
    source_url = require_env("DATABASE_URL")
    target_url = require_env("NEON_DATABASE_URL")

    if source_url == target_url:
        raise RuntimeError("DATABASE_URL and NEON_DATABASE_URL are the same. Refusing to migrate.")

    source_engine = create_engine(source_url, pool_pre_ping=True)
    target_engine = create_engine(target_url, pool_pre_ping=True)

    ensure_target_schema(target_engine)
    records = load_source_rows(source_engine)
    upsert_target_rows(target_engine, records)

    print(f"Migrated {len(records)} gold_prices row(s) to Neon.")


if __name__ == "__main__":
    main()
