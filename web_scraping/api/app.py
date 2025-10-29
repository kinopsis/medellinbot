"""
Web Scraping API
================

FastAPI application for accessing scraped data and managing scraping operations.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import json

from web_scraping.core.database import db_manager
from web_scraping.services.data_processor import DataProcessor, DataQuality
from web_scraping.config.settings import config
from web_scraping.scrapers.alcaldia_medellin import AlcaldiaMedellinScraper
from web_scraping.scrapers.secretaria_movilidad import SecretariaMovilidadScraper

# Initialize FastAPI app
app = FastAPI(
    title="MedellínBot Web Scraping API",
    description="API for accessing scraped data from Medellín government sources",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
data_processor = DataProcessor()
logger = logging.getLogger(__name__)

# Pydantic models for API
class ScrapingJobRequest(BaseModel):
    source: str
    data_types: Optional[List[str]] = None
    force_refresh: bool = False

class ScrapingJobResponse(BaseModel):
    job_id: int
    status: str
    message: str
    estimated_completion: Optional[datetime] = None

class DataQueryRequest(BaseModel):
    source: Optional[str] = None
    data_type: Optional[str] = None
    limit: int = 100
    offset: int = 0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class DataResponse(BaseModel):
    data: List[Dict[str, Any]]
    total_count: int
    has_more: bool

class QualityReportResponse(BaseModel):
    source: Optional[str]
    data_type: Optional[str]
    total_records: int
    quality_score: str
    issues: List[str]

# Background task for running scrapers
async def run_scraper_job(source: str, job_id: int):
    """Run a scraping job in the background."""
    try:
        logger.info(f"Starting scraping job {job_id} for source {source}")
        
        # Update job status to running
        await db_manager.update_scraping_job(job_id, status="running")
        
        # Initialize appropriate scraper
        if source == "alcaldia_medellin":
            scraper = AlcaldiaMedellinScraper()
        elif source == "secretaria_movilidad":
            scraper = SecretariaMovilidadScraper()
        else:
            await db_manager.update_scraping_job(
                job_id, 
                status="failed", 
                error_message=f"Unknown source: {source}"
            )
            return
            
        # Run scraping
        async with scraper:
            result = await scraper.scrape()
            
        if result.success:
            # Process the scraped data
            processor = DataProcessor()
            processing_result = await processor.process_scraped_data(
                source=source,
                data_type="scraped_data",  # Default data type
                raw_data=result.data or []
            )
            
            # Update job status
            await db_manager.update_scraping_job(
                job_id,
                status="completed",
                end_time=datetime.now(),
                records_processed=len(result.data or []),
                success_count=len(processing_result.processed_data),
                error_count=len(processing_result.errors)
            )
            
            logger.info(f"Scraping job {job_id} completed successfully")
        else:
            await db_manager.update_scraping_job(
                job_id,
                status="failed",
                error_message=result.error_message,
                end_time=datetime.now()
            )
            logger.error(f"Scraping job {job_id} failed: {result.error_message}")
            
    except Exception as e:
        logger.error(f"Error in scraping job {job_id}: {e}")
        await db_manager.update_scraping_job(
            job_id,
            status="failed",
            error_message=str(e),
            end_time=datetime.now()
        )

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "MedellínBot Web Scraping API",
        "version": "1.0.0",
        "endpoints": {
            "scrape": "POST /scrape - Start a new scraping job",
            "data": "GET /data - Query scraped data",
            "quality": "GET /quality - Get data quality report",
            "jobs": "GET /jobs - Get scraping job status"
        }
    }

@app.post("/scrape", response_model=ScrapingJobResponse)
async def start_scraping_job(
    request: ScrapingJobRequest,
    background_tasks: BackgroundTasks
):
    """Start a new scraping job."""
    try:
        # Create job record
        job_id = await db_manager.create_scraping_job(
            scraper_name=request.source,
            config={
                "data_types": request.data_types,
                "force_refresh": request.force_refresh
            }
        )
        
        if not job_id:
            raise HTTPException(status_code=500, detail="Failed to create scraping job")
            
        # Add background task
        background_tasks.add_task(run_scraper_job, request.source, job_id)
        
        return ScrapingJobResponse(
            job_id=job_id,
            status="pending",
            message=f"Scraping job started for {request.source}",
            estimated_completion=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error starting scraping job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data", response_model=DataResponse)
async def get_scraped_data(
    source: Optional[str] = Query(None, description="Filter by source"),
    data_type: Optional[str] = Query(None, description="Filter by data type"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date")
):
    """Get scraped data with filtering options."""
    try:
        # This would need to be implemented based on your database query capabilities
        # For now, return sample data structure
        sample_data = [
            {
                "id": 1,
                "source": "alcaldia_medellin",
                "data_type": "news",
                "content": {
                    "title": "Sample News",
                    "content": "Sample content",
                    "date": "2024-01-01T00:00:00"
                },
                "created_at": "2024-01-01T00:00:00",
                "is_valid": True
            }
        ]
        
        return DataResponse(
            data=sample_data,
            total_count=len(sample_data),
            has_more=False
        )
        
    except Exception as e:
        logger.error(f"Error getting scraped data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/quality", response_model=QualityReportResponse)
async def get_quality_report(
    source: Optional[str] = Query(None, description="Filter by source"),
    data_type: Optional[str] = Query(None, description="Filter by data type")
):
    """Get data quality report."""
    try:
        report = await data_processor.get_data_quality_report(source, data_type)
        
        return QualityReportResponse(
            source=report.get("source"),
            data_type=report.get("data_type"),
            total_records=report.get("total_records", 0),
            quality_score=report.get("quality_score", "invalid"),
            issues=report.get("issues", [])
        )
        
    except Exception as e:
        logger.error(f"Error getting quality report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs")
async def get_scraping_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    limit: int = Query(100, ge=1, le=1000, description="Number of jobs to return")
):
    """Get scraping job status and history."""
    try:
        # This would need to be implemented based on your database query capabilities
        # For now, return sample data structure
        sample_jobs = [
            {
                "id": 1,
                "scraper_name": "alcaldia_medellin",
                "status": "completed",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-01T00:05:00",
                "records_processed": 100,
                "success_count": 95,
                "error_count": 5
            }
        ]
        
        return {
            "jobs": sample_jobs,
            "total_count": len(sample_jobs)
        }
        
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sources")
async def get_available_sources():
    """Get list of available data sources."""
    return {
        "sources": [
            {
                "name": "alcaldia_medellin",
                "description": "Alcaldía de Medellín official website",
                "base_url": "https://medellin.gov.co",
                "data_types": ["news", "tramites", "contact", "program"]
            },
            {
                "name": "secretaria_movilidad",
                "description": "Secretaría de Movilidad de Medellín",
                "base_url": "https://movilidadmedellin.gov.co",
                "data_types": ["traffic_alert", "pico_placa", "vial_closure", "contact"]
            }
        ]
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    logger.error(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return {
        "error": exc.detail,
        "status_code": exc.status_code
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"General exception: {exc}")
    return {
        "error": "Internal server error",
        "status_code": 500
    }