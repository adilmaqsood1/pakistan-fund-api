from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.crud import (
    get_latest_etfs,
    get_etf_detail,
    get_etf_premium_discount_series,
    get_etf_alerts,
    compare_etfs,
)
from api.schemas import (
    ETFSnapshotResponse,
    ETFDetailResponse,
    ETFPremiumDiscountSeries,
    ETFAlertResponse,
)

router = APIRouter(prefix="/etfs", tags=["ETFs"])

@router.get("", response_model=List[ETFSnapshotResponse])
def list_etfs(db: Session = Depends(get_db)):
    """All 9 ETFs — latest NAV, price, premium/discount."""
    return get_latest_etfs(db)

@router.get("/alerts", response_model=List[ETFAlertResponse])
def etf_alerts(
    threshold: float = Query(2.0, description="Percentage threshold for premium/discount alerts"),
    db: Session = Depends(get_db)
):
    """ETFs trading > ±threshold% from NAV."""
    return get_etf_alerts(db, threshold_pct=threshold)

@router.get("/compare", response_model=List[ETFSnapshotResponse])
def compare_etf_list(
    symbols: str = Query("HBLTETF,MZNPETF", description="Comma-separated symbols to compare"),
    db: Session = Depends(get_db)
):
    """Side-by-side AUM, TER, return, premium/discount comparison."""
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        raise HTTPException(status_code=400, detail="At least one symbol must be provided for comparison")
    return compare_etfs(db, symbol_list)

@router.get("/{symbol}", response_model=ETFDetailResponse)
def get_etf_by_symbol(symbol: str, db: Session = Depends(get_db)):
    """Single ETF detail + 90-day history."""
    detail = get_etf_detail(db, symbol=symbol, days=90)
    if not detail:
        raise HTTPException(status_code=404, detail=f"ETF symbol '{symbol}' not found")
    return detail

@router.get("/{symbol}/premium-discount", response_model=ETFPremiumDiscountSeries)
def get_premium_discount_time_series(symbol: str, db: Session = Depends(get_db)):
    """Premium/discount time series history."""
    return get_etf_premium_discount_series(db, symbol=symbol, days=90)
