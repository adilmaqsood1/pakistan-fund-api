import pytest
from scraper.mufap import fetch_mufap_daily_nav, fetch_mufap_performance, fetch_pkrv_yields
from scraper.psx import fetch_all_etf_prices, ETF_SYMBOLS
from scraper.pdf_parser import extract_top_holdings_from_pdf

@pytest.mark.asyncio
async def test_mufap_scrapers_structure():
    navs = await fetch_mufap_daily_nav()
    assert isinstance(navs, list)

    perfs = await fetch_mufap_performance()
    assert isinstance(perfs, list)

    yields = await fetch_pkrv_yields()
    assert isinstance(yields, list)

@pytest.mark.asyncio
async def test_psx_etf_symbols_universe():
    assert len(ETF_SYMBOLS) == 9
    assert "HBLTETF" in ETF_SYMBOLS
    assert "MZNPETF" in ETF_SYMBOLS
    assert "MIIETF" in ETF_SYMBOLS

def test_pdf_parser_nonexistent():
    res = extract_top_holdings_from_pdf("non_existent_file.pdf")
    assert res == []
