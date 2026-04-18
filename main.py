from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from agg import aggregate_gold_prices
from src.crud import get_history, get_latest_price, upsert_gold_prices
from src.database import SessionLocal, engine
from src.models import Base
from src.predict import forecast


app = FastAPI(title="Gold Dashboard API")
Base.metadata.create_all(bind=engine)


def ensure_symbol_column():
    inspector = inspect(engine)
    if "gold_prices" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("gold_prices")]
    if "symbol" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE gold_prices ADD COLUMN symbol VARCHAR(6) NOT NULL DEFAULT 'XAU'"))
            conn.execute(text("ALTER TABLE gold_prices ALTER COLUMN symbol DROP DEFAULT"))


def ensure_date_symbol_constraint():
    inspector = inspect(engine)
    if "gold_prices" not in inspector.get_table_names():
        return

    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("gold_prices")
        if constraint.get("name")
    }
    if "uq_date_symbol" not in unique_constraints:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE gold_prices "
                    "ADD CONSTRAINT uq_date_symbol UNIQUE (date, symbol)"
                )
            )


ensure_symbol_column()
ensure_date_symbol_constraint()

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
        "symbol": getattr(row, "symbol", "XAU"),
        "price_per_gram_usd": to_float(row.price_per_gram_usd),
        "price_per_gram_inr": to_float(row.price_per_gram_inr),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def normalize_records(payload, symbol="XAU"):
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
        "symbol": symbol.upper(),
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
    return FileResponse(
        DASHBOARD_PATH,
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/about")
def about_page():
    html = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>About Metal Folio</title>
  <link rel=\"stylesheet\" href=\"/static/dashboard.css?v=6\">
</head>
<body>
  <div class=\"chrome-shell chrome-shell-top\">
    <div class=\"chrome-inner\">
      <header class=\"top-bar\">
        <div class=\"brand-block\">
          <div class=\"brand-mark\">$</div>
          <div>
            <h1 class=\"brand-title\">Metal Folio</h1>
          </div>
        </div>
        <div class=\"top-bar-actions\">
          <a href=\"/dashboard\" class=\"secondary-button\">Dashboard</a>
          <a href=\"/about\" class=\"primary-button\">About</a>
        </div>
      </header>
    </div>
  </div>

  <div class=\"page-shell\">
    <section class=\"card about-panel\">
      <div class=\"card-header\">
        <div>
          <p class=\"section-label\">About</p>
          <h2>Metal Folio</h2>
        </div>
      </div>
      <p class=\"about-text\">Metal Folio is a personal project built to track and visualize metal prices for gold, silver, and platinum. It is designed for informational purposes only and is not financial advice.</p>
      <p class=\"about-text\">The application aggregates market data from external price APIs, stores daily price history, and renders trend and forecast views in USD and INR.</p>
      <p class=\"about-text\"><strong>Author:</strong> Your Name<br><strong>Project Type:</strong> Personal informational dashboard<br><strong>Built with:</strong> FastAPI, SQLAlchemy, PostgreSQL, vanilla HTML/CSS/JS</p>
      <p class=\"about-text\">This project is intended as a learning and reference tool. Please verify pricing independently before making any decisions.</p>
    </section>
  </div>
</body>
</html>
    """
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store, max-age=0"})


@app.get("/aggregate")
def run_aggregation(
    symbol: str = Query(default="XAU", pattern="^(XAU|XAG|XPT)$"),
    db: Session = Depends(get_db),
):
    symbol = symbol.upper()
    data = aggregate_gold_prices(symbol=symbol)
    if data.get("error"):
        raise HTTPException(status_code=502, detail=data["error"])

    records = normalize_records(data, symbol=symbol)
    if not records:
        raise HTTPException(status_code=500, detail="Aggregation returned no usable records.")

    rows = upsert_gold_prices(db, records)
    latest = get_latest_price(db, symbol=symbol)

    return {
        "message": "Saved to DB",
        "rows": rows,
        "sources": data.get("sources", []),
        "latest": serialize_price(latest) if latest else None,
    }


@app.get("/api/summary")
def api_summary(
    symbol: str = Query(default="XAU", pattern="^(XAU|XAG|XPT)$"),
    db: Session = Depends(get_db),
):
    symbol = symbol.upper()
    history = list(reversed(get_history(db, days=365, symbol=symbol)))
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
    symbol: str = Query(default="XAU", pattern="^(XAU|XAG|XPT)$"),
    db: Session = Depends(get_db),
):
    symbol = symbol.upper()
    history = list(reversed(get_history(db, days=days, symbol=symbol)))
    return {"items": [serialize_price(row) for row in history]}


@app.get("/api/forecast")
def api_forecast(
    days: int = Query(default=30, ge=1, le=180),
    symbol: str = Query(default="XAU", pattern="^(XAU|XAG|XPT)$"),
):
    symbol = symbol.upper()
    result = forecast(days=days, symbol=symbol)
    if result.get("error"):
        return {"items": [], "error": result["error"], "method": None}
    return result


if __name__ == "__main__":
    data = aggregate_gold_prices()
    print("Aggregated Gold Prices:\n", data)
