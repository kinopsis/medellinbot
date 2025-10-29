"""
Utility Functions
=================

Common utility functions for web scraping operations.
"""

import re
import json
import logging
import hashlib
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, urlunparse
import aiohttp
import requests
from bs4 import BeautifulSoup

def normalize_url(base_url: str, relative_url: str) -> str:
    """Normalize a relative URL against a base URL."""
    return urljoin(base_url, relative_url)

def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc

def is_valid_url(url: str) -> bool:
    """Check if a URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    if not text:
        return ""
        
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters that might cause issues
    text = re.sub(r'[^\w\sáéíóúÁÉÍÓÚñÑ.,;:!?()-]', ' ', text)
    
    return text.strip()

def extract_emails(text: str) -> List[str]:
    """Extract email addresses from text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(email_pattern, text)

def extract_phone_numbers(text: str) -> List[str]:
    """Extract phone numbers from text."""
    # Colombian phone number patterns
    patterns = [
        r'\b(?:\+?57[-.\s]?)?(?:\(?[1-9]\d{2}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b',
        r'\b(?:\+?57[-.\s]?)?(?:3[0-9]{2})[-.\s]?\d{3}[-.\s]?\d{4}\b'
    ]
    
    phones = []
    for pattern in patterns:
        phones.extend(re.findall(pattern, text))
        
    return list(set(phones))  # Remove duplicates

def generate_content_hash(content: str) -> str:
    """Generate a hash for content deduplication."""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def parse_date_string(date_str: str) -> Optional[datetime]:
    """Parse various date string formats."""
    if not date_str:
        return None
        
    # Common date formats
    formats = [
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%Y-%m-%d %H:%M:%S',
        '%d/%m/%Y %H:%M:%S',
        '%m/%d/%Y %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S.%fZ'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
            
    return None

def extract_metadata(soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
    """Extract metadata from HTML soup."""
    metadata = {}
    
    # Open Graph metadata
    og_tags = soup.find_all('meta', property=re.compile(r'^og:'))
    for tag in og_tags:
        property_name = tag.get('property', '').replace('og:', '')
        content = tag.get('content', '')
        if property_name and content:
            metadata[f"og_{property_name}"] = content
            
    # Twitter Card metadata
    twitter_tags = soup.find_all('meta', name=re.compile(r'^twitter:'))
    for tag in twitter_tags:
        name = tag.get('name', '').replace('twitter:', '')
        content = tag.get('content', '')
        if name and content:
            metadata[f"twitter_{name}"] = content
            
    # Basic meta tags
    title_tag = soup.find('title')
    if title_tag:
        metadata['title'] = clean_text(title_tag.get_text())
        
    description_tag = soup.find('meta', attrs={'name': 'description'})
    if description_tag:
        metadata['description'] = clean_text(description_tag.get('content', ''))
        
    # Canonical URL
    canonical_tag = soup.find('link', rel='canonical')
    if canonical_tag:
        canonical_url = canonical_tag.get('href', '')
        if canonical_url:
            metadata['canonical_url'] = normalize_url(base_url, canonical_url)
            
    return metadata

async def fetch_with_retry(session: aiohttp.ClientSession, url: str, 
                          max_retries: int = 3, delay: float = 1.0) -> Optional[str]:
    """Fetch URL with retry logic."""
    for attempt in range(max_retries):
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"HTTP {response.status}"
                    )
        except Exception as e:
            if attempt == max_retries - 1:
                logging.getLogger(__name__).error(f"Failed to fetch {url} after {max_retries} attempts: {e}")
                return None
                
            await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
            
    return None

def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """Validate data against a JSON schema and return list of errors."""
    errors = []
    
    def validate_field(field_name: str, field_value: Any, field_schema: Any) -> None:
        if isinstance(field_schema, dict):
            if 'type' in field_schema:
                expected_type = field_schema['type']
                if expected_type == 'array' and not isinstance(field_value, list):
                    errors.append(f"{field_name}: Expected array, got {type(field_value).__name__}")
                elif expected_type == 'object' and not isinstance(field_value, dict):
                    errors.append(f"{field_name}: Expected object, got {type(field_value).__name__}")
                elif expected_type == 'string' and not isinstance(field_value, str):
                    errors.append(f"{field_name}: Expected string, got {type(field_value).__name__}")
                elif expected_type == 'number' and not isinstance(field_value, (int, float)):
                    errors.append(f"{field_name}: Expected number, got {type(field_value).__name__}")
                elif expected_type == 'boolean' and not isinstance(field_value, bool):
                    errors.append(f"{field_name}: Expected boolean, got {type(field_value).__name__}")
                    
            if 'required' in field_schema and field_schema['required'] and field_value is None:
                errors.append(f"{field_name}: Required field is missing or null")
                
            if 'min_length' in field_schema and isinstance(field_value, str):
                if len(field_value) < field_schema['min_length']:
                    errors.append(f"{field_name}: String too short (min {field_schema['min_length']} chars)")
                    
            if 'max_length' in field_schema and isinstance(field_value, str):
                if len(field_value) > field_schema['max_length']:
                    errors.append(f"{field_name}: String too long (max {field_schema['max_length']} chars)")
                    
        elif isinstance(field_schema, list):
            # Handle array of schemas
            if isinstance(field_value, list):
                for i, item in enumerate(field_value):
                    for item_schema in field_schema:
                        validate_field(f"{field_name}[{i}]", item, item_schema)
                        
    # Validate each field in the schema
    for field_name, field_schema in schema.items():
        field_value = data.get(field_name)
        validate_field(field_name, field_value, field_schema)
        
    return errors

class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, requests_per_second: float):
        self.requests_per_second = requests_per_second
        self.tokens = 1.0
        self.last_update = asyncio.get_event_loop().time()
        self.lock = asyncio.Lock()
        
    async def acquire(self):
        """Acquire a token from the rate limiter."""
        async with self.lock:
            now = asyncio.get_event_loop().time()
            time_passed = now - self.last_update
            
            # Add tokens based on time passed
            self.tokens = min(1.0, self.tokens + time_passed * self.requests_per_second)
            self.last_update = now
            
            if self.tokens < 1.0:
                # Wait for next token
                sleep_time = (1.0 - self.tokens) / self.requests_per_second
                await asyncio.sleep(sleep_time)
                self.tokens = 1.0
                
            self.tokens -= 1.0