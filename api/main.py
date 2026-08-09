import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from db.database import init_db, SessionLocal
from db.seed_data import seed_database_if_empty
from scraper.scheduler import start_scheduler, stop_scheduler

from api.routes import funds, etfs, yields, ai, pipeline

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")
    init_db()
    
    logger.info("Checking database seed status...")
    db = SessionLocal()
    try:
        seed_database_if_empty(db)
    finally:
        db.close()

    logger.info("Starting background scheduler...")
    start_scheduler()
    
    yield
    
    logger.info("Shutting down background scheduler...")
    stop_scheduler()

app = FastAPI(
    title="Pakistan Fund & ETF API",
    description="Daily NAV history, AUM trends, expense ratios, ETF premium/discount signals, PKRV yield curves, and Groq Llama 3.3 AI analysis.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Performance timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["X-Process-Time-MS"] = str(process_time_ms)
    return response

import os
from fastapi.responses import HTMLResponse

DASHBOARD_HTML_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "dashboard.html")

# Serve monolithic Bootstrap Web Dashboard
@app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
def get_dashboard():
    if os.path.exists(DASHBOARD_HTML_PATH):
        with open(DASHBOARD_HTML_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Dashboard template not found</h1>"

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ACTIVE",
        "service": "Pakistan Fund & ETF API",
        "version": "1.0.0",
        "docs": "/docs",
        "dashboard": "/dashboard",
        "api_v1_base": "/api/v1"
    }

# Mount v1 router
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(funds.router)
v1_router.include_router(etfs.router)
v1_router.include_router(yields.router)
v1_router.include_router(ai.router)
v1_router.include_router(pipeline.router)

app.include_router(v1_router)
