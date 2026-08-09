from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, Index
from db.database import Base

class FundNAV(Base):
    __tablename__ = "fund_nav"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    fund_name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, default="equity")
    nav = Column(Float, nullable=False)
    aum_mn = Column(Float, nullable=False, default=0.0)
    ter = Column(Float, nullable=False, default=0.0)

    __table_args__ = (
        Index("idx_fund_nav_date_name", "date", "fund_name"),
    )

class FundPerformance(Base):
    __tablename__ = "fund_performance"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    fund_name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, default="equity")
    ytd = Column(Float, nullable=False, default=0.0)
    return_1yr = Column(Float, nullable=False, default=0.0)
    return_3yr = Column(Float, nullable=False, default=0.0)
    return_5yr = Column(Float, nullable=False, default=0.0)

    __table_args__ = (
        Index("idx_fund_perf_date_name", "date", "fund_name"),
    )

class ETFSnapshot(Base):
    __tablename__ = "etf_snapshot"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    symbol = Column(String(20), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    nav = Column(Float, nullable=False)
    market_price = Column(Float, nullable=False)
    premium_discount_pct = Column(Float, nullable=False)
    signal = Column(String(50), nullable=False, default="FAIR")
    aum_mn_pkr = Column(Float, nullable=False, default=0.0)
    ter_pct = Column(Float, nullable=False, default=0.0)
    ytd_return_pct = Column(Float, nullable=False, default=0.0)
    volume_today = Column(Integer, nullable=False, default=0)
    category = Column(String(100), nullable=False, default="fixed_income")

    __table_args__ = (
        Index("idx_etf_snap_date_symbol", "date", "symbol"),
    )

class PKRVYield(Base):
    __tablename__ = "pkrv_yield"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    tenor = Column(String(20), nullable=False, index=True)  # 1M, 3M, 6M, 1Y, 3Y, 5Y, 10Y
    yield_pct = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_pkrv_date_tenor", "date", "tenor"),
    )

class FundPayout(Base):
    __tablename__ = "fund_payouts"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    fund_name = Column(String(255), nullable=False, index=True)
    payout_per_unit = Column(Float, nullable=False)
    payout_type = Column(String(50), nullable=False, default="Dividend")

    __table_args__ = (
        Index("idx_payout_date_name", "date", "fund_name"),
    )

class ScrapeLog(Base):
    __tablename__ = "scrape_log"

    id = Column(Integer, primary_key=True, index=True)
    run_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    source = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)  # SUCCESS, FAILURE, PARTIAL
    rows_inserted = Column(Integer, nullable=False, default=0)
    error = Column(String(1000), nullable=True)
