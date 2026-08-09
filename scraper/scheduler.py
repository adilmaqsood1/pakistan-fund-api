import logging
from datetime import datetime, date, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import FundNAV, FundPerformance, ETFSnapshot, PKRVYield, ScrapeLog
from db.crud import add_scrape_log
from scraper.mufap import fetch_mufap_daily_nav, fetch_mufap_performance, fetch_pkrv_yields
from scraper.psx import fetch_all_etf_prices

logger = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler()

async def run_daily_pipeline() -> dict:
    """
    Executes daily pipeline:
    1. Scrapes MUFAP NAVs & performance
    2. Scrapes PSX ETF prices & volumes
    3. Scrapes PKRV yield curve
    4. Computes premium/discount vs NAV & signals
    5. Saves updates and logs status
    """
    logger.info("Starting daily data scraping pipeline...")
    db: Session = SessionLocal()
    today_str = date.today().strftime("%Y-%m-%d")
    total_inserted = 0
    errors = []

    try:
        # 1. MUFAP NAVs
        navs = await fetch_mufap_daily_nav()
        if navs:
            for item in navs:
                existing = db.query(FundNAV).filter(
                    FundNAV.date == item["date"],
                    FundNAV.fund_name == item["fund_name"]
                ).first()
                if existing:
                    existing.nav = item["nav"]
                    existing.aum_mn = item["aum_mn"]
                    existing.ter = item["ter"]
                else:
                    db.add(FundNAV(**item))
                    total_inserted += 1

        # 2. MUFAP Performance
        perfs = await fetch_mufap_performance()
        if perfs:
            for item in perfs:
                existing = db.query(FundPerformance).filter(
                    FundPerformance.date == item["date"],
                    FundPerformance.fund_name == item["fund_name"]
                ).first()
                if existing:
                    existing.ytd = item["ytd"]
                    existing.return_1yr = item["return_1yr"]
                    existing.return_3yr = item["return_3yr"]
                    existing.return_5yr = item["return_5yr"]
                else:
                    db.add(FundPerformance(**item))
                    total_inserted += 1

        # 3. PSX ETF Prices & Premium/Discount Update
        etf_prices = await fetch_all_etf_prices()
        for etf_p in etf_prices:
            symbol = etf_p["symbol"]
            mkt_price = etf_p["market_price"]
            vol = etf_p["volume"]

            latest_nav_record = db.query(FundNAV).filter(
                FundNAV.fund_name.like(f"%{symbol}%")
            ).order_by(FundNAV.date.desc()).first()

            nav_val = latest_nav_record.nav if latest_nav_record else mkt_price

            prem_pct = ((mkt_price - nav_val) / nav_val) * 100.0 if nav_val > 0 else 0.0
            if prem_pct > 1.5:
                signal = "OVERVALUED"
            elif prem_pct < -1.5:
                signal = "UNDERVALUED"
            else:
                signal = "FAIR"

            existing_etf = db.query(ETFSnapshot).filter(
                ETFSnapshot.date == today_str,
                ETFSnapshot.symbol == symbol
            ).first()

            if existing_etf:
                existing_etf.market_price = mkt_price
                existing_etf.nav = nav_val
                existing_etf.premium_discount_pct = round(prem_pct, 4)
                existing_etf.signal = signal
                existing_etf.volume_today = vol
            else:
                db.add(ETFSnapshot(
                    date=today_str,
                    symbol=symbol,
                    name=f"{symbol} Fund",
                    nav=nav_val,
                    market_price=mkt_price,
                    premium_discount_pct=round(prem_pct, 4),
                    signal=signal,
                    aum_mn_pkr=1000.0,
                    ter_pct=0.75,
                    ytd_return_pct=15.0,
                    volume_today=vol,
                    category="equity"
                ))
                total_inserted += 1

        # 4. PKRV Yields
        yields = await fetch_pkrv_yields()
        if yields:
            for y_item in yields:
                existing_y = db.query(PKRVYield).filter(
                    PKRVYield.date == y_item["date"],
                    PKRVYield.tenor == y_item["tenor"]
                ).first()
                if existing_y:
                    existing_y.yield_pct = y_item["yield_pct"]
                else:
                    db.add(PKRVYield(**y_item))
                    total_inserted += 1

        db.commit()
        add_scrape_log(db, source="PIPELINE", status="SUCCESS", rows_inserted=total_inserted)
        logger.info(f"Daily pipeline completed successfully. Rows inserted/updated: {total_inserted}")
        return {"status": "SUCCESS", "rows_inserted": total_inserted, "error": None}

    except Exception as e:
        logger.error(f"Daily pipeline failed: {e}")
        db.rollback()
        err_msg = str(e)
        add_scrape_log(db, source="PIPELINE", status="FAILURE", rows_inserted=0, error=err_msg)
        return {"status": "FAILURE", "rows_inserted": 0, "error": err_msg}

    finally:
        db.close()

def start_scheduler():
    # 5:30 PM PKT = 17:30 PKT (UTC+5) = 12:30 UTC
    trigger = CronTrigger(hour=12, minute=30, timezone=timezone.utc)
    scheduler.add_job(run_daily_pipeline, trigger=trigger, id="daily_mufap_psx_pipeline", replace_existing=True)
    scheduler.start()
    logger.info("APScheduler started: Daily pipeline scheduled at 17:30 PKT (12:30 UTC)")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler stopped.")
