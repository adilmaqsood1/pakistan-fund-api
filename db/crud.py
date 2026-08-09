from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, select, and_
from db.models import FundNAV, FundPerformance, ETFSnapshot, PKRVYield, FundPayout, ScrapeLog

# --- FUNDS CRUD ---

def get_latest_funds(db: Session, category: Optional[str] = None) -> List[Dict[str, Any]]:
    # Get max date for each fund_name in FundNAV
    subq = (
        db.query(
            FundNAV.fund_name,
            func.max(FundNAV.date).label("max_date")
        )
        .group_by(FundNAV.fund_name)
        .subquery()
    )

    # Get max date for each fund_name in FundPerformance
    perf_subq = (
        db.query(
            FundPerformance.fund_name,
            func.max(FundPerformance.date).label("max_date")
        )
        .group_by(FundPerformance.fund_name)
        .subquery()
    )

    query = (
        db.query(FundNAV, FundPerformance)
        .join(subq, and_(FundNAV.fund_name == subq.c.fund_name, FundNAV.date == subq.c.max_date))
        .outerjoin(perf_subq, FundNAV.fund_name == perf_subq.c.fund_name)
        .outerjoin(
            FundPerformance,
            and_(
                FundPerformance.fund_name == perf_subq.c.fund_name,
                FundPerformance.date == perf_subq.c.max_date
            )
        )
    )

    if category:
        cat_clean = category.lower().replace("-", "_")
        query = query.filter(func.lower(FundNAV.category).like(f"%{cat_clean}%"))

    funds_rows = query.order_by(FundNAV.fund_name).all()
    
    out = []
    for f, p in funds_rows:
        out.append({
            "fund_name": f.fund_name,
            "category": f.category,
            "date": f.date,
            "nav": f.nav,
            "aum_mn": f.aum_mn,
            "ter": f.ter,
            "ytd": p.ytd if p else 0.0,
            "return_1yr": p.return_1yr if p else 0.0,
            "return_3yr": p.return_3yr if p else 0.0,
            "return_5yr": p.return_5yr if p else 0.0,
        })
    return out

def get_fund_detail(db: Session, fund_name: str, days: int = 90) -> Optional[Dict[str, Any]]:
    # Case-insensitive match on fund_name or symbol
    fund = (
        db.query(FundNAV)
        .filter(func.lower(FundNAV.fund_name).like(f"%{fund_name.lower()}%"))
        .order_by(desc(FundNAV.date))
        .first()
    )
    if not fund:
        return None

    exact_name = fund.fund_name
    history_records = (
        db.query(FundNAV)
        .filter(FundNAV.fund_name == exact_name)
        .order_by(desc(FundNAV.date))
        .limit(days)
        .all()
    )

    perf = (
        db.query(FundPerformance)
        .filter(FundPerformance.fund_name == exact_name)
        .order_by(desc(FundPerformance.date))
        .first()
    )

    history = [
        {"date": r.date, "nav": r.nav, "aum_mn": r.aum_mn, "ter": r.ter}
        for r in reversed(history_records)
    ]

    return {
        "fund_name": exact_name,
        "category": fund.category,
        "latest_date": fund.date,
        "latest_nav": fund.nav,
        "aum_mn": fund.aum_mn,
        "ter": fund.ter,
        "performance": {
            "ytd": perf.ytd if perf else 0.0,
            "return_1yr": perf.return_1yr if perf else 0.0,
            "return_3yr": perf.return_3yr if perf else 0.0,
            "return_5yr": perf.return_5yr if perf else 0.0,
        },
        "nav_history_days": len(history),
        "nav_history": history,
    }

def get_funds_performance(db: Session) -> List[Dict[str, Any]]:
    subq = (
        db.query(
            FundPerformance.fund_name,
            func.max(FundPerformance.date).label("max_date")
        )
        .group_by(FundPerformance.fund_name)
        .subquery()
    )

    perfs = (
        db.query(FundPerformance)
        .join(subq, and_(FundPerformance.fund_name == subq.c.fund_name, FundPerformance.date == subq.c.max_date))
        .order_by(FundPerformance.fund_name)
        .all()
    )

    return [
        {
            "fund_name": p.fund_name,
            "category": p.category,
            "date": p.date,
            "ytd": p.ytd,
            "return_1yr": p.return_1yr,
            "return_3yr": p.return_3yr,
            "return_5yr": p.return_5yr,
        }
        for p in perfs
    ]

def get_top_funds(db: Session, n: int = 20, period: str = "ytd") -> List[Dict[str, Any]]:
    period_clean = period.lower()
    col_map = {
        "ytd": FundPerformance.ytd,
        "1yr": FundPerformance.return_1yr,
        "3yr": FundPerformance.return_3yr,
        "5yr": FundPerformance.return_5yr,
    }
    sort_col = col_map.get(period_clean, FundPerformance.ytd)

    subq = (
        db.query(
            FundPerformance.fund_name,
            func.max(FundPerformance.date).label("max_date")
        )
        .group_by(FundPerformance.fund_name)
        .subquery()
    )

    perfs = (
        db.query(FundPerformance)
        .join(subq, and_(FundPerformance.fund_name == subq.c.fund_name, FundPerformance.date == subq.c.max_date))
        .order_by(desc(sort_col))
        .limit(n)
        .all()
    )

    return [
        {
            "fund_name": p.fund_name,
            "category": p.category,
            "date": p.date,
            "period": period_clean,
            "return_pct": getattr(p, "ytd" if period_clean == "ytd" else f"return_{period_clean}"),
            "ytd": p.ytd,
            "return_1yr": p.return_1yr,
            "return_3yr": p.return_3yr,
            "return_5yr": p.return_5yr,
        }
        for p in perfs
    ]

# --- ETFS CRUD ---

def get_latest_etfs(db: Session) -> List[Dict[str, Any]]:
    subq = (
        db.query(
            ETFSnapshot.symbol,
            func.max(ETFSnapshot.id).label("max_id")
        )
        .group_by(ETFSnapshot.symbol)
        .subquery()
    )

    etfs = (
        db.query(ETFSnapshot)
        .join(subq, ETFSnapshot.id == subq.c.max_id)
        .order_by(ETFSnapshot.symbol)
        .all()
    )

    return [
        {
            "symbol": e.symbol,
            "name": e.name,
            "date": e.date,
            "nav": e.nav,
            "market_price": e.market_price,
            "premium_discount_pct": round(e.premium_discount_pct, 4),
            "signal": e.signal,
            "aum_mn_pkr": e.aum_mn_pkr,
            "ter_pct": e.ter_pct,
            "ytd_return_pct": e.ytd_return_pct,
            "volume_today": e.volume_today,
            "category": e.category,
        }
        for e in etfs
    ]

def get_etf_detail(db: Session, symbol: str, days: int = 90) -> Optional[Dict[str, Any]]:
    symbol_upper = symbol.upper()
    latest = (
        db.query(ETFSnapshot)
        .filter(ETFSnapshot.symbol == symbol_upper)
        .order_by(desc(ETFSnapshot.date))
        .first()
    )
    if not latest:
        return None

    history_records = (
        db.query(ETFSnapshot)
        .filter(ETFSnapshot.symbol == symbol_upper)
        .order_by(desc(ETFSnapshot.date))
        .limit(days)
        .all()
    )

    history = [
        {
            "date": r.date,
            "nav": r.nav,
            "market_price": r.market_price,
            "premium_discount_pct": round(r.premium_discount_pct, 4),
            "volume": r.volume_today,
        }
        for r in reversed(history_records)
    ]

    return {
        "symbol": latest.symbol,
        "name": latest.name,
        "date": latest.date,
        "nav": latest.nav,
        "market_price": latest.market_price,
        "premium_discount_pct": round(latest.premium_discount_pct, 4),
        "signal": latest.signal,
        "aum_mn_pkr": latest.aum_mn_pkr,
        "ter_pct": latest.ter_pct,
        "ytd_return_pct": latest.ytd_return_pct,
        "volume_today": latest.volume_today,
        "category": latest.category,
        "history_days": len(history),
        "history": history,
    }

def get_etf_premium_discount_series(db: Session, symbol: str, days: int = 90) -> Dict[str, Any]:
    symbol_upper = symbol.upper()
    records = (
        db.query(ETFSnapshot)
        .filter(ETFSnapshot.symbol == symbol_upper)
        .order_by(desc(ETFSnapshot.date))
        .limit(days)
        .all()
    )
    
    series = [
        {
            "date": r.date,
            "nav": r.nav,
            "market_price": r.market_price,
            "premium_discount_pct": round(r.premium_discount_pct, 4),
            "signal": r.signal,
        }
        for r in reversed(records)
    ]

    return {
        "symbol": symbol_upper,
        "count": len(series),
        "time_series": series,
    }

def get_etf_alerts(db: Session, threshold_pct: float = 2.0) -> List[Dict[str, Any]]:
    all_latest = get_latest_etfs(db)
    alerts = []
    for etf in all_latest:
        prem = abs(etf["premium_discount_pct"])
        if prem >= threshold_pct:
            alert_type = "PREMIUM" if etf["premium_discount_pct"] > 0 else "DISCOUNT"
            alerts.append({
                "symbol": etf["symbol"],
                "name": etf["name"],
                "date": etf["date"],
                "nav": etf["nav"],
                "market_price": etf["market_price"],
                "premium_discount_pct": etf["premium_discount_pct"],
                "alert_type": alert_type,
                "threshold_pct": threshold_pct,
                "message": f"ETF trading at a {alert_type.lower()} of {etf['premium_discount_pct']}% vs NAV (threshold: ±{threshold_pct}%)",
            })
    return alerts

def compare_etfs(db: Session, symbols: List[str]) -> List[Dict[str, Any]]:
    symbols_upper = [s.strip().upper() for s in symbols if s.strip()]
    subq = (
        db.query(
            ETFSnapshot.symbol,
            func.max(ETFSnapshot.id).label("max_id")
        )
        .filter(ETFSnapshot.symbol.in_(symbols_upper))
        .group_by(ETFSnapshot.symbol)
        .subquery()
    )

    records = (
        db.query(ETFSnapshot)
        .join(subq, ETFSnapshot.id == subq.c.max_id)
        .all()
    )

    return [
        {
            "symbol": r.symbol,
            "name": r.name,
            "date": r.date,
            "nav": r.nav,
            "market_price": r.market_price,
            "premium_discount_pct": round(r.premium_discount_pct, 4),
            "signal": r.signal,
            "aum_mn_pkr": r.aum_mn_pkr,
            "ter_pct": r.ter_pct,
            "ytd_return_pct": r.ytd_return_pct,
            "volume_today": r.volume_today,
            "category": r.category,
        }
        for r in records
    ]

# --- YIELDS & BENCHMARK CRUD ---

def get_latest_pkrv_yields(db: Session) -> Dict[str, Any]:
    max_date = db.query(func.max(PKRVYield.date)).scalar()
    if not max_date:
        return {"date": None, "yield_curve": {}}

    yields = (
        db.query(PKRVYield)
        .filter(PKRVYield.date == max_date)
        .all()
    )

    tenor_order = ["1M", "3M", "6M", "1Y", "3Y", "5Y", "10Y"]
    yield_map = {y.tenor: y.yield_pct for y in yields}
    ordered_yields = {t: yield_map.get(t) for t in tenor_order if t in yield_map}

    return {
        "date": max_date,
        "yield_curve": ordered_yields
    }

def get_pkrv_history(db: Session, tenor: str = "3M", limit: int = 90) -> List[Dict[str, Any]]:
    records = (
        db.query(PKRVYield)
        .filter(PKRVYield.tenor == tenor.upper())
        .order_by(desc(PKRVYield.date))
        .limit(limit)
        .all()
    )

    return [
        {"date": r.date, "tenor": r.tenor, "yield_pct": r.yield_pct}
        for r in reversed(records)
    ]

def get_pkrv_trend(db: Session) -> Dict[str, Any]:
    # Compare 3M tenor latest vs ~30 days ago
    records = (
        db.query(PKRVYield)
        .filter(PKRVYield.tenor == "3M")
        .order_by(desc(PKRVYield.date))
        .limit(30)
        .all()
    )

    if not records or len(records) < 2:
        return {
            "tenor": "3M",
            "trend": "stable",
            "change_bps": 0,
            "latest_date": records[0].date if records else None,
            "latest_yield": records[0].yield_pct if records else None,
            "prior_date": None,
            "prior_yield": None
        }

    latest = records[0]
    prior = records[-1]
    diff = latest.yield_pct - prior.yield_pct
    bps = int(round(diff * 100))

    if bps >= 25:
        trend = "rising"
    elif bps <= -25:
        trend = "falling"
    else:
        trend = "stable"

    return {
        "tenor": "3M",
        "trend": trend,
        "change_bps": bps,
        "latest_date": latest.date,
        "latest_yield": latest.yield_pct,
        "prior_date": prior.date,
        "prior_yield": prior.yield_pct,
    }

def get_hbltetf_benchmark(db: Session, days: int = 90) -> Dict[str, Any]:
    records = (
        db.query(ETFSnapshot)
        .filter(ETFSnapshot.symbol == "HBLTETF")
        .order_by(desc(ETFSnapshot.date))
        .limit(days)
        .all()
    )

    series = [
        {
            "date": r.date,
            "nav": r.nav,
            "market_price": r.market_price,
            "ytd_return_pct": r.ytd_return_pct
        }
        for r in reversed(records)
    ]

    latest = records[0] if records else None

    return {
        "symbol": "HBLTETF",
        "name": "HBL Total Treasury ETF",
        "benchmark_role": "Risk-Free Fixed Income Benchmark",
        "latest_nav": latest.nav if latest else None,
        "ytd_return_pct": latest.ytd_return_pct if latest else 12.09,
        "count": len(series),
        "nav_series": series,
    }

# --- PIPELINE LOGS ---

def add_scrape_log(db: Session, source: str, status: str, rows_inserted: int, error: Optional[str] = None):
    log = ScrapeLog(
        source=source,
        status=status,
        rows_inserted=rows_inserted,
        error=error
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def get_scrape_logs(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
    logs = (
        db.query(ScrapeLog)
        .order_by(desc(ScrapeLog.run_at))
        .limit(limit)
        .all()
    )
    return [
        {
            "id": l.id,
            "run_at": l.run_at.isoformat() if l.run_at else None,
            "source": l.source,
            "status": l.status,
            "rows_inserted": l.rows_inserted,
            "error": l.error,
        }
        for l in logs
    ]
