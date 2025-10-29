"""
Web Scraping Orchestrator
=========================

Main orchestrator for managing web scraping operations across all data sources.
"""

import logging
import asyncio
import argparse
import signal
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

from web_scraping.core.database import db_manager
from web_scraping.services.data_processor import DataProcessor
from web_scraping.monitoring.monitor import monitoring_service, ScrapingMonitor
from web_scraping.config.settings import config
from web_scraping.scrapers.alcaldia_medellin import AlcaldiaMedellinScraper
from web_scraping.scrapers.secretaria_movilidad import SecretariaMovilidadScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebScrapingOrchestrator:
    """Main orchestrator for web scraping operations."""
    
    def __init__(self):
        self.running = False
        self.scraper_tasks: List[asyncio.Task] = []
        self.data_processor = DataProcessor()
        
    async def initialize(self):
        """Initialize the orchestrator."""
        try:
            # Initialize database
            db_manager.create_tables()
            
            # Start monitoring
            monitoring_service.start_monitoring(config.monitoring.prometheus_port)
            
            logger.info("Web scraping orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise
            
    async def shutdown(self):
        """Shutdown the orchestrator."""
        self.running = False
        
        # Cancel all scraper tasks
        for task in self.scraper_tasks:
            task.cancel()
            
        # Wait for tasks to complete
        if self.scraper_tasks:
            await asyncio.gather(*self.scraper_tasks, return_exceptions=True)
            
        logger.info("Web scraping orchestrator shutdown complete")
        
    async def run_scraper(self, scraper_name: str, force_refresh: bool = False):
        """Run a specific scraper."""
        async with ScrapingMonitor(scraper_name, monitoring_service):
            try:
                logger.info(f"Starting scraper: {scraper_name}")
                
                # Initialize appropriate scraper
                if scraper_name == "alcaldia_medellin":
                    scraper = AlcaldiaMedellinScraper()
                elif scraper_name == "secretaria_movilidad":
                    scraper = SecretariaMovilidadScraper()
                else:
                    logger.error(f"Unknown scraper: {scraper_name}")
                    return
                    
                # Run scraping
                async with scraper:
                    result = await scraper.scrape()
                    
                if result.success:
                    # Process the scraped data
                    processing_result = await self.data_processor.process_scraped_data(
                        source=scraper_name,
                        data_type="scraped_data",
                        raw_data=result.data or []
                    )
                    
                    # Update data quality metrics
                    if processing_result.quality_score:
                        quality_score_map = {
                            "high": 1.0,
                            "medium": 0.7,
                            "low": 0.5,
                            "invalid": 0.0
                        }
                        monitoring_service.update_data_quality(
                            scraper_name,
                            "scraped_data",
                            quality_score_map.get(processing_result.quality_score.value, 0.0)
                        )
                        
                    logger.info(
                        f"Scraper {scraper_name} completed: "
                        f"{len(result.data or [])} records scraped, "
                        f"{len(processing_result.processed_data)} processed, "
                        f"{processing_result.duplicate_count} duplicates removed"
                    )
                else:
                    logger.error(f"Scraper {scraper_name} failed: {result.error_message}")
                    
            except Exception as e:
                logger.error(f"Error running scraper {scraper_name}: {e}")
                monitoring_service.record_error(scraper_name, str(type(e).__name__))
                
    async def run_all_scrapers(self, force_refresh: bool = False):
        """Run all configured scrapers."""
        scrapers = ["alcaldia_medellin", "secretaria_movilidad"]
        
        for scraper_name in scrapers:
            await self.run_scraper(scraper_name, force_refresh)
            
    async def run_scheduled_scraping(self):
        """Run scheduled scraping operations."""
        logger.info("Starting scheduled scraping operations")
        
        while self.running:
            try:
                # Run all scrapers
                await self.run_all_scrapers()
                
                # Check alerts
                await monitoring_service.check_alerts()
                
                # Wait for next cycle
                await asyncio.sleep(config.scraping.rate_limit_delay * 10)  # 10x rate limit delay
                
            except asyncio.CancelledError:
                logger.info("Scheduled scraping cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduled scraping: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
                
    async def run_manual_scraping(self, scrapers: List[str], force_refresh: bool = False):
        """Run manual scraping for specific sources."""
        logger.info(f"Running manual scraping for: {scrapers}")
        
        for scraper_name in scrapers:
            await self.run_scraper(scraper_name, force_refresh)
            
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            "status": "running" if self.running else "stopped",
            "active_tasks": len([t for t in self.scraper_tasks if not t.done()]),
            "total_tasks": len(self.scraper_tasks),
            "monitoring": monitoring_service.get_system_health(),
            "data_processor": {
                "status": "ready"
            }
        }

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Web Scraping Orchestrator")
    parser.add_argument(
        "--mode", 
        choices=["scheduled", "manual", "single"], 
        default="scheduled",
        help="Operation mode"
    )
    parser.add_argument(
        "--scrapers",
        nargs="+",
        help="List of scrapers to run (for manual mode)"
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force refresh data even if recently scraped"
    )
    parser.add_argument(
        "--single-scraper",
        choices=["alcaldia_medellin", "secretaria_movilidad"],
        help="Single scraper to run (for single mode)"
    )
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = WebScrapingOrchestrator()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(orchestrator.shutdown())
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await orchestrator.initialize()
        orchestrator.running = True
        
        if args.mode == "scheduled":
            # Run scheduled scraping
            await orchestrator.run_scheduled_scraping()
            
        elif args.mode == "manual":
            if args.scrapers:
                await orchestrator.run_manual_scraping(args.scrapers, args.force_refresh)
            else:
                logger.error("No scrapers specified for manual mode")
                
        elif args.mode == "single":
            if args.single_scraper:
                await orchestrator.run_scraper(args.single_scraper, args.force_refresh)
            else:
                logger.error("No scraper specified for single mode")
                
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        await orchestrator.shutdown()

if __name__ == "__main__":
    asyncio.run(main())