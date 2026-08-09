import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app
from db.database import init_db, SessionLocal
from db.seed_data import seed_database_if_empty

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    init_db()
    db = SessionLocal()
    try:
        seed_database_if_empty(db)
    finally:
        db.close()

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ACTIVE"

@pytest.mark.asyncio
async def test_dashboard_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "<html" in response.text.lower()

        response_dash = await client.get("/dashboard")
        assert response_dash.status_code == 200
        assert "<html" in response_dash.text.lower()

@pytest.mark.asyncio
async def test_funds_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # GET /api/v1/funds
        resp = await client.get("/api/v1/funds")
        assert resp.status_code == 200
        funds = resp.json()
        assert isinstance(funds, list)
        assert len(funds) > 0

        # GET /api/v1/funds/performance
        resp_perf = await client.get("/api/v1/funds/performance")
        assert resp_perf.status_code == 200
        assert isinstance(resp_perf.json(), list)

        # GET /api/v1/funds/top
        resp_top = await client.get("/api/v1/funds/top?n=5&period=ytd")
        assert resp_top.status_code == 200
        top_funds = resp_top.json()
        assert len(top_funds) <= 5

        # GET /api/v1/funds/category/equity
        resp_cat = await client.get("/api/v1/funds/category/equity")
        assert resp_cat.status_code == 200

        # GET /api/v1/funds/{name}
        sample_name = funds[0]["fund_name"]
        resp_single = await client.get(f"/api/v1/funds/{sample_name}")
        assert resp_single.status_code == 200
        single_data = resp_single.json()
        assert single_data["fund_name"] == sample_name
        assert "nav_history" in single_data

@pytest.mark.asyncio
async def test_etfs_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # GET /api/v1/etfs
        resp = await client.get("/api/v1/etfs")
        assert resp.status_code == 200
        etfs = resp.json()
        assert len(etfs) == 9

        # GET /api/v1/etfs/HBLTETF
        resp_single = await client.get("/api/v1/etfs/HBLTETF")
        assert resp_single.status_code == 200
        etf_detail = resp_single.json()
        assert etf_detail["symbol"] == "HBLTETF"
        assert "history" in etf_detail

        # GET /api/v1/etfs/HBLTETF/premium-discount
        resp_pd = await client.get("/api/v1/etfs/HBLTETF/premium-discount")
        assert resp_pd.status_code == 200
        assert "time_series" in resp_pd.json()

        # GET /api/v1/etfs/alerts
        resp_alerts = await client.get("/api/v1/etfs/alerts?threshold=0.1")
        assert resp_alerts.status_code == 200
        assert isinstance(resp_alerts.json(), list)

        # GET /api/v1/etfs/compare
        resp_comp = await client.get("/api/v1/etfs/compare?symbols=HBLTETF,MZNPETF")
        assert resp_comp.status_code == 200
        assert len(resp_comp.json()) == 2

@pytest.mark.asyncio
async def test_yields_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # GET /api/v1/yields/pkrv
        resp = await client.get("/api/v1/yields/pkrv")
        assert resp.status_code == 200
        assert "yield_curve" in resp.json()

        # GET /api/v1/yields/pkrv/history
        resp_hist = await client.get("/api/v1/yields/pkrv/history?tenor=3M")
        assert resp_hist.status_code == 200

        # GET /api/v1/yields/trend
        resp_trend = await client.get("/api/v1/yields/trend")
        assert resp_trend.status_code == 200
        assert resp_trend.json()["tenor"] == "3M"

        # GET /api/v1/benchmark/hbltetf
        resp_bench = await client.get("/api/v1/benchmark/hbltetf")
        assert resp_bench.status_code == 200
        assert resp_bench.json()["symbol"] == "HBLTETF"

@pytest.mark.asyncio
async def test_ai_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # GET /api/v1/ai/etfs/HBLTETF/explain
        resp = await client.get("/api/v1/ai/etfs/HBLTETF/explain")
        assert resp.status_code in [200, 400]

        # GET /api/v1/ai/regime
        resp_regime = await client.get("/api/v1/ai/regime")
        assert resp_regime.status_code in [200, 400]

        # GET /api/v1/ai/compare
        resp_comp = await client.get("/api/v1/ai/compare?funds=HBLTETF,MZNPETF")
        assert resp_comp.status_code in [200, 400]

        # GET /api/v1/ai/ask
        resp_ask = await client.get("/api/v1/ai/ask?q=What+is+HBLTETF?")
        assert resp_ask.status_code in [200, 400]

@pytest.mark.asyncio
async def test_pipeline_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # GET /api/v1/pipeline/logs
        resp = await client.get("/api/v1/pipeline/logs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
