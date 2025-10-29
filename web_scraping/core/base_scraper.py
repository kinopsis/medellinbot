"""
Base Scraper Class
==================

Abstract base class for all web scrapers in the MedellínBot framework.
Provides common functionality and enforces consistent interface across scrapers.
"""

import abc
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import aiohttp
import requests
from bs4 import BeautifulSoup
import json

@dataclass
class ScrapingConfig:
    """Configuration for web scraping operations."""
    base_url: str
    rate_limit_delay: float = 1.0
    timeout: int = 30
    max_retries: int = 3
    user_agent: str = "MedellínBot/1.0"
    headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }

@dataclass
class ScrapingResult:
    """Result of a scraping operation."""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class BaseScraper(abc.ABC):
    """Abstract base class for web scrapers."""
    
    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
        
    async def initialize(self):
        """Initialize the scraper (e.g., create session)."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            headers=self.config.headers
        )
        
    async def cleanup(self):
        """Clean up resources (e.g., close session)."""
        if self.session:
            await self.session.close()
            
    async def fetch_page(self, url: str, **kwargs) -> str:
        """Fetch a web page with retry logic and rate limiting."""
        for attempt in range(self.config.max_retries):
            try:
                # Rate limiting
                if attempt > 0:
                    await asyncio.sleep(self.config.rate_limit_delay * (2 ** attempt))  # Exponential backoff
                    
                async with self.session.get(url, **kwargs) as response:
                    response.raise_for_status()
                    return await response.text()
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == self.config.max_retries - 1:
                    raise
                    
    def parse_html(self, html_content: str) -> BeautifulSoup:
        """Parse HTML content using BeautifulSoup."""
        return BeautifulSoup(html_content, 'html.parser')
        
    def extract_json_ld(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract JSON-LD structured data from HTML."""
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        data = []
        
        for script in json_ld_scripts:
            try:
                json_data = json.loads(script.string)
                data.append(json_data)
            except (json.JSONDecodeError, AttributeError) as e:
                self.logger.warning(f"Failed to parse JSON-LD: {e}")
                
        return data
        
    @abc.abstractmethod
    async def scrape(self) -> ScrapingResult:
        """Main scraping method to be implemented by subclasses."""
        pass
        
    def validate_data(self, data: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate scraped data and return (is_valid, errors)."""
        if not data:
            return False, ["No data to validate"]
            
        errors = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append(f"Item {i}: Expected dict, got {type(item)}")
                continue
                
            if not item:
                errors.append(f"Item {i}: Empty dictionary")
                
        return len(errors) == 0, errors