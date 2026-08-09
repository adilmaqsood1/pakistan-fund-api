from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict

# Base Pydantic v2 model configuration
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# --- FUNDS SCHEMAS ---

class FundListItem(BaseSchema):
    fund_name: str
    category: str
    date: str
    nav: float
    aum_mn: float
    ter: float
    ytd: Optional[float] = 0.0
    return_1yr: Optional[float] = 0.0
    return_3yr: Optional[float] = 0.0
    return_5yr: Optional[float] = 0.0

class FundPerformanceItem(BaseSchema):
    fund_name: str
    category: str
    date: str
    ytd: float
    return_1yr: float
    return_3yr: float
    return_5yr: float

class TopFundItem(BaseSchema):
    fund_name: str
    category: str
    date: str
    period: str
    return_pct: float
    ytd: float
    return_1yr: float
    return_3yr: float
    return_5yr: float

class NAVHistoryItem(BaseSchema):
    date: str
    nav: float
    aum_mn: float
    ter: float

class FundDetailResponse(BaseSchema):
    fund_name: str
    category: str
    latest_date: str
    latest_nav: float
    aum_mn: float
    ter: float
    performance: Dict[str, float]
    nav_history_days: int
    nav_history: List[NAVHistoryItem]

# --- ETF SCHEMAS ---

class ETFSnapshotResponse(BaseSchema):
    symbol: str
    name: str
    date: str
    nav: float
    market_price: float
    premium_discount_pct: float
    signal: str
    aum_mn_pkr: float
    ter_pct: float
    ytd_return_pct: float
    volume_today: int
    category: str

class ETFHistoryItem(BaseSchema):
    date: str
    nav: float
    market_price: float
    premium_discount_pct: float
    volume: int

class ETFDetailResponse(ETFSnapshotResponse):
    history_days: int
    history: List[ETFHistoryItem]

class ETFPremiumDiscountSeries(BaseSchema):
    symbol: str
    count: int
    time_series: List[Dict[str, Any]]

class ETFAlertResponse(BaseSchema):
    symbol: str
    name: str
    date: str
    nav: float
    market_price: float
    premium_discount_pct: float
    alert_type: str
    threshold_pct: float
    message: str

# --- YIELDS & BENCHMARK SCHEMAS ---

class PKRVYieldResponse(BaseSchema):
    date: Optional[str]
    yield_curve: Dict[str, Optional[float]]

class PKRVHistoryItem(BaseSchema):
    date: str
    tenor: str
    yield_pct: float

class PKRVTrendResponse(BaseSchema):
    tenor: str
    trend: str
    change_bps: int
    latest_date: Optional[str]
    latest_yield: Optional[float]
    prior_date: Optional[str]
    prior_yield: Optional[float]

class BenchmarkHBLTETFResponse(BaseSchema):
    symbol: str
    name: str
    benchmark_role: str
    latest_nav: Optional[float]
    ytd_return_pct: float
    count: int
    nav_series: List[Dict[str, Any]]

# --- AI SCHEMAS ---

class AIExplainResponse(BaseSchema):
    symbol: str
    ai_analysis: str

class AIRegimeResponse(BaseSchema):
    regime_analysis: str

class AIAskResponse(BaseSchema):
    question: str
    answer: str

class AICompareResponse(BaseSchema):
    funds: List[str]
    ai_analysis: str

# --- PIPELINE LOG SCHEMAS ---

class ScrapeLogResponse(BaseSchema):
    id: int
    run_at: Optional[str]
    source: str
    status: str
    rows_inserted: int
    error: Optional[str]

class PipelineRunResponse(BaseSchema):
    status: str
    rows_inserted: int
    error: Optional[str]
