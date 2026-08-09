from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.crud import (
    get_etf_detail,
    get_latest_pkrv_yields,
    get_fund_detail,
    get_latest_etfs,
    get_latest_funds,
)
from ai.groq_client import ask_groq
from api.schemas import (
    AIExplainResponse,
    AIRegimeResponse,
    AIAskResponse,
    AICompareResponse,
)

router = APIRouter(prefix="/ai", tags=["AI Layer (Groq)"])

SYSTEM_PROMPT = """You are a Pakistan mutual fund and ETF analyst.

RULES — follow strictly:
1. Only use numbers explicitly provided in the user message.
   If a number is missing, say "data not available" — never estimate.
2. Always compare against HBLTETF benchmark (12.09% YTD, near-zero risk).
3. Keep responses under 150 words. Be direct, no filler.
4. Structure every response as:
   SITUATION: one sentence
   ANALYSIS: key metrics evaluation (NAV, AUM, TER, Prem/Disc %)
   VS HBLTETF: comparison against HBLTETF benchmark
5. You only know about Pakistan — MUFAP funds, PSX-listed ETFs,
   SBP policy rates, PKRV yield curve. Do not reference global markets
   unless directly relevant.
6. If the question is outside Pakistan fund/ETF scope, say:
   "I can only answer questions about Pakistan mutual funds and ETFs."
"""

def build_db_context_for_query(db: Session, q: str) -> str:
    """Retrieves relevant database context (ETFs, Funds, PKRV yields) for user questions."""
    context_lines = []
    q_upper = q.upper()
    q_words = [w.strip() for w in q.split() if len(w.strip()) >= 2]

    # 1. Search ETFs
    all_etfs = get_latest_etfs(db)
    matched_etfs = []
    for etf in all_etfs:
        sym = etf["symbol"].upper()
        name = etf["name"].upper()
        if sym in q_upper or any(w.upper() in name for w in q_words if len(w) >= 3):
            matched_etfs.append(etf)

    if matched_etfs:
        for e in matched_etfs:
            context_lines.append(
                f"ETF {e['symbol']} ({e['name']}): NAV={e['nav']}, Price={e['market_price']}, "
                f"Prem/Disc={e['premium_discount_pct']}%, AUM=PKR {e['aum_mn_pkr']}M, "
                f"TER={e['ter_pct']}%, YTD Return={e['ytd_return_pct']}%, Volume={e['volume_today']}"
            )

    # 2. Search Funds
    latest_funds = get_latest_funds(db)
    matched_funds = []
    for f in latest_funds:
        fname = f["fund_name"]
        if any(w.lower() in fname.lower() for w in q_words if len(w) >= 3 and w.lower() not in ["fund", "etf", "what", "show", "tell"]):
            matched_funds.append(f)
            if len(matched_funds) >= 5:
                break

    if matched_funds:
        for f in matched_funds:
            det = get_fund_detail(db, fund_name=f["fund_name"], days=1)
            if det:
                perf = det.get("performance", {})
                context_lines.append(
                    f"Fund '{det['fund_name']}' ({det['category']}): NAV={det['latest_nav']}, AUM=PKR {det['aum_mn']}M, "
                    f"TER={det['ter']}%, YTD Return={perf.get('ytd', 'data not available')}%, 1Yr Return={perf.get('return_1yr', 'data not available')}%"
                )

    # 3. Attach PKRV yields
    yields = get_latest_pkrv_yields(db)
    yc = yields.get("yield_curve", {})
    if yc:
        yc_str = ", ".join([f"{k}:{v}%" for k, v in yc.items() if v is not None])
        context_lines.append(f"Latest PKRV Yield Curve ({yields.get('date')}): {yc_str}")

    # 4. Fallback benchmark context if no specific matches
    if not matched_etfs and not matched_funds:
        hbl = next((e for e in all_etfs if e["symbol"] == "HBLTETF"), None)
        if hbl:
            context_lines.append(
                f"Benchmark ETF HBLTETF ({hbl['name']}): NAV={hbl['nav']}, Price={hbl['market_price']}, "
                f"Prem/Disc={hbl['premium_discount_pct']}%, YTD Return={hbl['ytd_return_pct']}%, AUM=PKR {hbl['aum_mn_pkr']}M"
            )

    return "\n".join(context_lines)

@router.get("/etfs/{symbol}/explain", response_model=AIExplainResponse)
async def explain_etf(symbol: str, db: Session = Depends(get_db)):
    """Plain English ETF metrics analysis vs HBLTETF benchmark."""
    data = get_etf_detail(db, symbol=symbol, days=1)
    if not data:
        raise HTTPException(status_code=404, detail=f"ETF '{symbol}' not found")

    user_msg = f"""
    DATA CONTEXT:
    ETF: {data['symbol']} ({data['name']})
    NAV: {data['nav']}  |  Market Price: {data['market_price']}
    Premium/Discount: {data['premium_discount_pct']}%
    YTD Return: {data['ytd_return_pct']}%  |  TER: {data['ter_pct']}%
    AUM: PKR {data['aum_mn_pkr']}M

    Provide a concise analysis of this ETF's valuation and performance vs HBLTETF (12.09% YTD return benchmark).
    """
    reply = await ask_groq(SYSTEM_PROMPT, user_msg, temperature=0.2)
    return {"symbol": symbol.upper(), "ai_analysis": reply}

@router.get("/regime", response_model=AIRegimeResponse)
async def detect_regime(db: Session = Depends(get_db)):
    """Current macro regime + equity vs treasury yield analysis."""
    yields_data = get_latest_pkrv_yields(db)
    yc = yields_data.get("yield_curve", {})
    
    user_msg = f"""
    DATA CONTEXT:
    Pakistan PKRV yields today ({yields_data.get('date')}):
    3M: {yc.get('3M', 'data not available')}%  |  6M: {yc.get('6M', 'data not available')}%  |  1Y: {yc.get('1Y', 'data not available')}%
    10Y: {yc.get('10Y', 'data not available')}%

    Based on this yield curve, classify the current macro regime for Pakistan (rate_rising / rate_falling / stable) and provide an analysis vs HBLTETF.
    """
    reply = await ask_groq(SYSTEM_PROMPT, user_msg, temperature=0.2)
    return {"regime_analysis": reply}

@router.get("/compare", response_model=AICompareResponse)
async def compare_funds_ai(
    funds: str = Query("HBLTETF,MZNPETF", description="Comma-separated fund names or symbols to compare"),
    db: Session = Depends(get_db)
):
    """Natural language fund comparison with recommendation."""
    fund_names = [f.strip() for f in funds.split(",") if f.strip()]
    if len(fund_names) < 2:
        raise HTTPException(status_code=400, detail="Provide at least two funds/ETFs for AI comparison")

    summaries = []
    found_count = 0
    for fname in fund_names:
        det = get_etf_detail(db, symbol=fname, days=1)
        if not det:
            det = get_fund_detail(db, fund_name=fname, days=1)

        if det:
            found_count += 1
            name = det.get("symbol") or det.get("fund_name")
            nav = det.get("nav") or det.get("latest_nav")
            mkt_p = det.get("market_price", "data not available")
            prem = det.get("premium_discount_pct", "data not available")
            aum = det.get("aum_mn_pkr") or det.get("aum_mn")
            ter = det.get("ter_pct") or det.get("ter")
            ytd = det.get("ytd_return_pct") or det.get("performance", {}).get("ytd", "data not available")
            summaries.append(
                f"Name: {name}, NAV: {nav}, Price: {mkt_p}, Prem/Disc: {prem}%, AUM: PKR {aum}M, TER: {ter}%, YTD Return: {ytd}%"
            )
        else:
            summaries.append(f"Name: {fname} (data not available)")

    if found_count == 0:
        raise HTTPException(
            status_code=404,
            detail="None of the specified funds or ETFs were found in the database."
        )

    user_msg = f"""
    DATA CONTEXT:
    {" | ".join(summaries)}

    Compare these funds side-by-side and provide a recommendation against HBLTETF (12.09% YTD return benchmark).
    """
    reply = await ask_groq(SYSTEM_PROMPT, user_msg, temperature=0.2)
    return {"funds": fund_names, "ai_analysis": reply}

@router.get("/ask", response_model=AIAskResponse)
async def ask_anything(
    q: str = Query(..., description="Natural language question about Pakistan funds or ETFs"),
    db: Session = Depends(get_db)
):
    """Free-form Q&A about any fund or ETF in the database."""
    db_context = build_db_context_for_query(db, q)

    user_msg = f"""
    DATA CONTEXT FROM DATABASE:
    {db_context}

    USER QUESTION:
    {q}
    """
    reply = await ask_groq(SYSTEM_PROMPT, user_msg, temperature=0.5)
    return {"question": q, "answer": reply}
