"""
Database Management
===================

Database connection, models, and migration management for the web scraping framework.
"""

import os
import logging
import asyncio
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import json

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./web_scraping.db")
Base = declarative_base()

class ScrapedData(Base):
    """Base model for scraped data."""
    __tablename__ = "scraped_data"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(255), index=True, nullable=False)
    data_type = Column(String(100), index=True, nullable=False)
    content = Column(JSON, nullable=False)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_valid = Column(Boolean, default=True)
    validation_errors = Column(Text, default="")

class ScrapingJob(Base):
    """Model for tracking scraping jobs."""
    __tablename__ = "scraping_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    scraper_name = Column(String(255), index=True, nullable=False)
    status = Column(String(50), default="pending")
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    records_processed = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    config = Column(JSON, default=dict)

class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, database_url: str = DATABASE_URL):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.logger = logging.getLogger(__name__)
        
    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            self.logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to create database tables: {e}")
            raise
            
    def get_session(self):
        """Get a database session."""
        return self.SessionLocal()
        
    async def save_scraped_data(self, source: str, data_type: str, content: Dict[str, Any], 
                              metadata: Optional[Dict[str, Any]] = None, 
                              is_valid: bool = True, 
                              validation_errors: str = "") -> Optional[int]:
        """Save scraped data to the database."""
        session = self.get_session()
        try:
            scraped_data = ScrapedData(
                source=source,
                data_type=data_type,
                content=content,
                metadata=metadata or {},
                is_valid=is_valid,
                validation_errors=validation_errors
            )
            session.add(scraped_data)
            session.commit()
            session.refresh(scraped_data)
            return scraped_data.id
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to save scraped data: {e}")
            return None
        finally:
            session.close()
            
    async def update_scraping_job(self, job_id: int, **kwargs) -> bool:
        """Update a scraping job record."""
        session = self.get_session()
        try:
            job = session.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()
            if not job:
                return False
                
            for key, value in kwargs.items():
                setattr(job, key, value)
                
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to update scraping job {job_id}: {e}")
            return False
        finally:
            session.close()
            
    async def create_scraping_job(self, scraper_name: str, config: Dict[str, Any] = None) -> Optional[int]:
        """Create a new scraping job record."""
        session = self.get_session()
        try:
            job = ScrapingJob(
                scraper_name=scraper_name,
                config=config or {}
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            return job.id
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to create scraping job: {e}")
            return None
        finally:
            session.close()
            
    def get_recent_data(self, source: str, data_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent scraped data for a source and data type."""
        session = self.get_session()
        try:
            results = session.query(ScrapedData).filter(
                ScrapedData.source == source,
                ScrapedData.data_type == data_type
            ).order_by(ScrapedData.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": result.id,
                    "source": result.source,
                    "data_type": result.data_type,
                    "content": result.content,
                    "metadata": result.metadata,
                    "created_at": result.created_at.isoformat(),
                    "is_valid": result.is_valid
                }
                for result in results
            ]
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get recent data: {e}")
            return []
        finally:
            session.close()

# Global database manager instance
db_manager = DatabaseManager()