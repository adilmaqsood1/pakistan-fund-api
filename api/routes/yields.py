from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.crud import (
    get_latest_pkrv_yields,
    get_pkrv_history,
    get_pkrv_trend,
    get_hbltetf_benchmark,
)
from api.schemas import (
    PKRVYieldResponse,
    PKRVHistoryItem,
    PKRVTrendResponse,
    BenchmarkHBLTETFResponse,
)

router = APIRouter(tags=["Yields & Benchmark"])

@router.get("/yields/pkrv", response_model=PKRVYieldResponse)
def get_latest_yield_curve(db: Session = Depends(get_db)):
    """Latest PKRV yield curve (1M → 10Y)."""
    return get_latest_pkrv_yields(db)

@router.get("/yields/pkrv/history", response_model=List[PKRVHistoryItem])
def get_tenor_history(
    tenor: str = Query("3M", description="Yield curve tenor: 1M, 3M, 6M, 1Y, 3Y, 5Y, 10Y"),
    limit: int = Query(90, ge=1, le=365, description="Number of historical records"),
    db: Session = Depends(get_db)
):
    """PKRV history for a specific tenor."""
    return get_pkrv_history(db, tenor=tenor, limit=limit)

@router.get("/yields/trend", response_model=PKRVTrendResponse)
def get_yield_trend(db: Session = Depends(get_db)):
    """3M PKRV direction: rising / falling / stable."""
    return get_pkrv_trend(db)

@router.get("/benchmark/hbltetf", response_model=BenchmarkHBLTETFResponse)
def get_hbltetf_benchmark_series(db: Session = Depends(get_db)):
    """HBLTETF NAV series — the benchmark to beat."""
    return get_hbltetf_benchmark(db, days=90)
