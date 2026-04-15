from sqlalchemy import Column, Integer, Date, Numeric, DateTime, String, UniqueConstraint
from sqlalchemy.sql import func
from .database import Base

class GoldPrice(Base):
    __tablename__ = "gold_prices"
    __table_args__ = (
        UniqueConstraint("date", "symbol", name="uq_date_symbol"),
    )

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    symbol = Column(String(6), nullable=False, index=True)

    price_per_gram_usd = Column(Numeric(12, 4), nullable=False)
    price_per_gram_inr = Column(Numeric(12, 4), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())