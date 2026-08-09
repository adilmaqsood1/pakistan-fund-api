# Pakistan Fund & ETF API

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A high-performance REST API and scraping pipeline for Pakistan's mutual fund and ETF market. Automates daily scraping of MUFAP & PSX, stores historical NAV, AUM, TER, and PKRV yield curve data, calculates ETF premium/discount signals, and exposes AI insights via Groq Llama 3.3.

---

## 1. Features & Capabilities

- **300+ MUFAP Mutual Funds**: Real-time daily NAV, AUM trends, total expense ratios (TER), and historical returns (YTD, 1yr, 3yr, 5yr).
- **All 9 PSX-Listed ETFs**: Daily market closing prices, volumes, NAV tracking, and premium/discount calculations.
- **PKRV Yield Curve**: Full yield curve daily across 1M, 3M, 6M, 1Y, 3Y, 5Y, and 10Y tenors + 3M yield trend detector.
- **Benchmark Benchmark Target**: Native comparison against **HBLTETF** (HBL Total Treasury ETF) as the risk-free fixed income benchmark.
- **APScheduler Pipeline**: Automated daily execution at 17:30 PKT (12:30 UTC) post-PSX close with full `scrape_log` health reporting.
- **Groq Llama 3.3 AI Layer**: Natural language Q&A, macro regime detection, plain English ETF buy/sell signals, and side-by-side fund comparison.

---

## 2. PSX ETF Universe (All 9 Listed)

| Symbol | Fund Name | Category | Tracks |
| :--- | :--- | :--- | :--- |
| **HBLTETF** | HBL Total Treasury ETF | Fixed Income | HBL Total Treasury Index (T-Bills + PIBs) |
| **MZNPETF** | Meezan Pakistan ETF | Shariah Equity | Meezan Pakistan Index (MZNPI) |
| **MIIETF** | Mahaana Islamic Index ETF | Shariah Equity | MII30 Index |
| **NBPGETF** | NBP Growth ETF | Conventional Equity | NBP Index |
| **NITGETF** | NIT Government Index ETF | Conventional Equity | NIT Index |
| **UBLPETF** | UBL Pakistan Enterprise ETF | Conventional Equity | UBL PE Index |
| **JSGBETF** | JS Growth Balanced ETF | Balanced | JS Balanced Index |
| **ACIETF** | ACI Islamic ETF | Shariah Thematic | ACI Index |
| **JSMFETF** | JS Momentum Factor ETF | Smart Beta | JS Momentum Factor Index |

---

## 3. Project Architecture

```
pakistan-fund-api/
├── ai/
│   ├── __init__.py
│   └── groq_client.py     # Groq API client (llama-3.3-70b-versatile) & fallback engine
├── api/
│   ├── __init__.py
│   ├── main.py            # FastAPI entry point, lifespan, CORS, timing middleware
│   ├── schemas.py         # Pydantic v2 validation models
│   └── routes/
│       ├── __init__.py
│       ├── funds.py       # Fund endpoints (/funds/*)
│       ├── etfs.py        # ETF endpoints (/etfs/*)
│       ├── yields.py      # Yield curve & benchmark endpoints (/yields/*)
│       ├── ai.py          # AI reasoning endpoints (/ai/*)
│       └── pipeline.py    # Pipeline trigger & scrape logs (/pipeline/*)
├── db/
│   ├── __init__.py
│   ├── database.py        # SQLAlchemy 2.0 engine & session maker
│   ├── models.py          # Declarative ORM models
│   ├── crud.py            # Data access functions
│   └── seed_data.py       # Seed script (2022 to present backfill)
├── scraper/
│   ├── __init__.py
│   ├── mufap.py           # NAV, AUM, TER, performance & PKRV yield scrapers
│   ├── psx.py             # ETF closing prices & volume scrapers
│   ├── pdf_parser.py      # AMC FMR PDF top-10 holdings parser (pdfplumber)
│   └── scheduler.py       # APScheduler daily pipeline runner
├── tests/
│   ├── __init__.py
│   ├── test_scraper.py    # Scraper unit tests
│   └── test_api.py        # API integration tests
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 4. API Endpoints Specification

Base URL: `http://localhost:8000/api/v1`

### 4.1 Funds (`/api/v1/funds`)
- `GET /funds` — All funds with latest NAV, AUM, and TER. Optional `?category=equity` filter.
- `GET /funds/performance` — YTD, 1yr, 3yr, 5yr returns for all funds.
- `GET /funds/top?n=20&period=ytd` — Top N funds sorted by return period (`ytd`, `1yr`, `3yr`, `5yr`).
- `GET /funds/category/{cat}` — Filter funds by category (e.g. `equity`, `income`, `money_market`, `shariah_equity`).
- `GET /funds/{name}` — Single fund detail with 90-day NAV history series.

### 4.2 ETFs (`/api/v1/etfs`)
- `GET /etfs` — All 9 ETFs with latest NAV, market price, premium/discount %, and signal.
- `GET /etfs/{symbol}` — Single ETF details with 90-day price vs NAV history.
- `GET /etfs/{symbol}/premium-discount` — Time series of premium/discount %.
- `GET /etfs/alerts?threshold=2.0` — ETFs trading beyond configurable premium/discount threshold (e.g. ±2%).
- `GET /etfs/compare?symbols=HBLTETF,MZNPETF` — Side-by-side metrics comparison.

### 4.3 Yields & Benchmark (`/api/v1/yields`, `/api/v1/benchmark`)
- `GET /yields/pkrv` — Latest PKRV yield curve (1M → 10Y tenors).
- `GET /yields/pkrv/history?tenor=3M` — Historical yield series for specified tenor.
- `GET /yields/trend` — 3M PKRV yield direction (`rising`, `falling`, or `stable`).
- `GET /benchmark/hbltetf` — HBLTETF NAV time series (the benchmark to beat).

### 4.4 AI Layer (`/api/v1/ai`)
- `GET /ai/etfs/{symbol}/explain` — Plain English ETF signal analysis vs HBLTETF benchmark.
- `GET /ai/regime` — Macro regime classification & asset allocation recommendation.
- `GET /ai/compare?funds=HBLTETF,MZNPETF` — Natural language comparison of funds.
- `GET /ai/ask?q=...` — Free-form Q&A about Pakistan funds/ETFs.

### 4.5 Pipeline & Diagnostics (`/api/v1/pipeline`)
- `POST /pipeline/run` — On-demand manual trigger for scraping pipeline.
- `GET /pipeline/logs` — Pipeline health and execution logs.

---

## 5. Getting Started

### 5.1 Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/adilmaqsood1/pakistan-fund-api.git
   cd pakistan-fund-api
   ```

2. **Create a virtual environment & install dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   ```
   Add your Groq API Key to `.env` (optional; rule-based fallback active if omitted):
   ```env
   GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
   ```

4. **Run the API server**:
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```

5. **Access Web Analytics Dashboard & Swagger Docs**:
   - Monolithic Web Dashboard: `http://localhost:8000/` or `http://localhost:8000/dashboard`
   - Interactive OpenAPI Swagger Docs: `http://localhost:8000/docs`

Features included in the Web Analytics Dashboard:
- **PSX ETF Universe**: Real-time KPI cards, ETF prices, NAVs, premium/discount %, signal flags, and instant AI explain buttons.
- **Mutual Funds Explorer**: Live search & category filtering across 300+ MUFAP registered funds.
- **PKRV Yield Curve**: Live yield curve table & Chart.js line plot.
- **Groq AI Assistant**: Side-by-side fund comparison, macro regime detector, and natural language Q&A.
- **Pipeline Diagnostics**: Live trigger button for MUFAP & PSX scrapers with execution logs.

---

## 6. Running Tests

Run the full pytest suite:

```bash
pytest -v
```

---

## 7. Docker Deployment

Build and run using Docker Compose:

```bash
docker-compose up --build -d
```

The API will be live at `http://localhost:8000`.

---

## 8. License

Distributed under the MIT License.
