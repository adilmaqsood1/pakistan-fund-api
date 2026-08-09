from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from db.crud import get_scrape_logs
from scraper.scheduler import run_daily_pipeline
from api.schemas import PipelineRunResponse, ScrapeLogResponse

router = APIRouter(prefix="/pipeline", tags=["Pipeline & Diagnostics"])

@router.post("/run", response_model=PipelineRunResponse)
async def trigger_pipeline_run():
    """Manually trigger the MUFAP & PSX daily scraping pipeline."""
    res = await run_daily_pipeline()
    return res

@router.get("/logs", response_model=List[ScrapeLogResponse])
def list_pipeline_logs(limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve history of pipeline execution logs."""
    return get_scrape_logs(db, limit=limit)
