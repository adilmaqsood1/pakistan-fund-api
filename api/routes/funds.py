from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.crud import (
    get_latest_funds,
    get_fund_detail,
    get_funds_performance,
    get_top_funds,
)
from api.schemas import (
    FundListItem,
    FundPerformanceItem,
    TopFundItem,
    FundDetailResponse,
)

router = APIRouter(prefix="/funds", tags=["Funds"])

@router.get("", response_model=List[FundListItem])
def list_funds(category: Optional[str] = Query(None, description="Filter by category (equity, income, money_market, islamic)"), db: Session = Depends(get_db)):
    """All funds — latest NAV, AUM, TER."""
    return get_latest_funds(db, category=category)

@router.get("/performance", response_model=List[FundPerformanceItem])
def list_performance(db: Session = Depends(get_db)):
    """YTD, 1yr, 3yr, 5yr returns for all funds."""
    return get_funds_performance(db)

@router.get("/top", response_model=List[TopFundItem])
def get_top_performing_funds(
    n: int = Query(20, ge=1, le=100, description="Top N funds count"),
    period: str = Query("ytd", description="Period: ytd, 1yr, 3yr, 5yr"),
    db: Session = Depends(get_db)
):
    """Top N funds by return for a given period."""
    return get_top_funds(db, n=n, period=period)

@router.get("/category/{cat}", response_model=List[FundListItem])
def list_funds_by_category(cat: str, db: Session = Depends(get_db)):
    """Filter funds by category (equity, income, money-market, islamic)."""
    return get_latest_funds(db, category=cat)

@router.get("/{name}", response_model=FundDetailResponse)
def get_single_fund_detail(name: str, db: Session = Depends(get_db)):
    """Single fund detail + 90-day NAV history."""
    detail = get_fund_detail(db, fund_name=name, days=90)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Fund '{name}' not found")
    return detail
