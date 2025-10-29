"""
Alcaldía de Medellín Scraper
============================

Scraper for collecting data from the Alcaldía de Medellín website with vector search integration.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from bs4 import BeautifulSoup

from web_scraping.core.base_scraper import BaseScraper, ScrapingConfig, ScrapingResult
from web_scraping.core.utils import (
    extract_metadata, clean_text, extract_emails, extract_phone_numbers,
    parse_date_string, normalize_url, generate_content_hash
)
from web_scraping.config.settings import get_source_config
from web_scraping.services.storage_service import StorageService

class AlcaldiaMedellinScraper(BaseScraper):
    """Scraper for Alcaldía de Medellín website with vector search integration."""
    
    def __init__(self):
        source_config = get_source_config("alcaldia_medellin")
        config = ScrapingConfig(
            base_url=source_config.get("base_url", "https://medellin.gov.co"),
            rate_limit_delay=source_config.get("rate_limit_delay", 2.0),
            timeout=source_config.get("timeout", 30),
            user_agent="MedellínBot/1.0"
        )
        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.storage_service = StorageService()
        
    async def scrape(self) -> ScrapingResult:
        """Main scraping method for Alcaldía de Medellín."""
        try:
            self.logger.info("Starting Alcaldía de Medellín scraping")
            
            # Get main page
            main_page_html = await self.fetch_page(self.config.base_url)
            if not main_page_html:
                return ScrapingResult(
                    success=False,
                    error_message="Failed to fetch main page"
                )
                
            soup = self.parse_html(main_page_html)
            
            # Extract different types of data
            data = []
            
            # 1. Extract news and announcements
            news_data = await self._scrape_news(soup)
            data.extend(news_data)
            
            # 2. Extract trámites and servicios
            tramites_data = await self._scrape_tramites()
            data.extend(tramites_data)
            
            # 3. Extract contact information
            contact_data = await self._scrape_contact_info(soup)
            data.extend(contact_data)
            
            # 4. Extract program information
            programs_data = await self._scrape_programs()
            data.extend(programs_data)
            
            # Store data using unified storage service
            storage_result = await self.storage_service.store_data(
                source="alcaldia_medellin",
                data_type="general",
                raw_data=data
            )
            
            # Validate data
            is_valid, validation_errors = self.validate_data(data)
            
            return ScrapingResult(
                success=storage_result["success"],
                data=data,
                metadata={
                    "source": "alcaldia_medellin",
                    "total_records": len(data),
                    "validation_errors": validation_errors if not is_valid else None,
                    "storage_result": storage_result
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error scraping Alcaldía de Medellín: {e}")
            return ScrapingResult(
                success=False,
                error_message=str(e)
            )
            
    async def _scrape_news(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Scrape news and announcements."""
        news_data = []
        
        try:
            # Look for news sections
            news_selectors = [
                'div.news-item', 'article.news', 'div.noticia', 
                'div.comunicado', 'div.announcement'
            ]
            
            for selector in news_selectors:
                news_elements = soup.select(selector)
                for element in news_elements:
                    try:
                        title_elem = element.select_one('h2, h3, .title, .titulo')
                        content_elem = element.select_one('p, .content, .contenido')
                        date_elem = element.select_one('.date, .fecha, time')
                        link_elem = element.select_one('a')
                        
                        title = clean_text(title_elem.get_text()) if title_elem else None
                        content = clean_text(content_elem.get_text()) if content_elem else None
                        date_str = clean_text(date_elem.get_text()) if date_elem else None
                        link = link_elem.get('href') if link_elem else None
                        
                        parsed_date = parse_date_string(date_str) if date_str else None
                        normalized_link = normalize_url(self.config.base_url, str(link)) if link else None
                        
                        if title and content:
                            news_item = {
                                "type": "news",
                                "title": title,
                                "content": content,
                                "date": parsed_date.isoformat() if parsed_date else None,
                                "url": normalized_link,
                                "source_url": self.config.base_url,
                                "content_hash": generate_content_hash(content),
                                "extracted_at": datetime.now().isoformat()
                            }
                            news_data.append(news_item)
                            
                    except Exception as e:
                        self.logger.warning(f"Error processing news item: {e}")
                        continue
                        
        except Exception as e:
            self.logger.error(f"Error scraping news: {e}")
            
        return news_data
        
    async def _scrape_tramites(self) -> List[Dict[str, Any]]:
        """Scrape trámites and servicios information."""
        tramites_data = []
        
        try:
            # Common trámites URLs
            tramites_urls = [
                f"{self.config.base_url}/tramites",
                f"{self.config.base_url}/servicios",
                f"{self.config.base_url}/ciudadano",
                f"{self.config.base_url}/gestiones"
            ]
            
            for url in tramites_urls:
                try:
                    html = await self.fetch_page(url)
                    if not html:
                        continue
                        
                    soup = self.parse_html(html)
                    
                    # Look for trámites
                    tramite_selectors = [
                        'div.tramite', 'article.tramite', 'div.servicio',
                        'div.gestion', 'div.procedure'
                    ]
                    
                    for selector in tramite_selectors:
                        tramite_elements = soup.select(selector)
                        for element in tramite_elements:
                            try:
                                title_elem = element.select_one('h2, h3, .title, .titulo')
                                description_elem = element.select_one('p, .description, .descripcion')
                                requirements_elem = element.select_one('.requirements, .requisitos')
                                link_elem = element.select_one('a')
                                
                                title = clean_text(title_elem.get_text()) if title_elem else None
                                description = clean_text(description_elem.get_text()) if description_elem else None
                                requirements = clean_text(requirements_elem.get_text()) if requirements_elem else None
                                link = link_elem.get('href') if link_elem else None
                                
                                normalized_link = normalize_url(self.config.base_url, str(link)) if link else None
                                
                                if title:
                                    tramite_item = {
                                        "type": "tramite",
                                        "title": title,
                                        "description": description,
                                        "requirements": requirements,
                                        "url": normalized_link,
                                        "source_url": url,
                                        "content_hash": generate_content_hash(title + (description or "")),
                                        "extracted_at": datetime.now().isoformat()
                                    }
                                    tramites_data.append(tramite_item)
                                    
                            except Exception as e:
                                self.logger.warning(f"Error processing tramite item: {e}")
                                continue
                                
                except Exception as e:
                    self.logger.warning(f"Error fetching tramites URL {url}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error scraping tramites: {e}")
            
        return tramites_data
        
    async def _scrape_contact_info(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Scrape contact information."""
        contact_data = []
        
        try:
            # Extract metadata for contact info
            metadata = extract_metadata(soup, self.config.base_url)
            
            # Look for contact sections
            contact_selectors = [
                'div.contact', 'section.contact', 'div.contacto', 
                'footer', 'div.footer'
            ]
            
            for selector in contact_selectors:
                contact_elements = soup.select(selector)
                for element in contact_elements:
                    try:
                        text_content = clean_text(element.get_text())
                        emails = extract_emails(text_content)
                        phones = extract_phone_numbers(text_content)
                        
                        if emails or phones:
                            contact_item = {
                                "type": "contact",
                                "emails": emails,
                                "phone_numbers": phones,
                                "source_url": self.config.base_url,
                                "content_hash": generate_content_hash(text_content),
                                "extracted_at": datetime.now().isoformat()
                            }
                            contact_data.append(contact_item)
                            
                    except Exception as e:
                        self.logger.warning(f"Error processing contact info: {e}")
                        continue
                        
            # Also check for structured contact data in metadata
            if 'og_email' in metadata:
                contact_item = {
                    "type": "contact",
                    "emails": [metadata['og_email']],
                    "phone_numbers": [],
                    "source_url": self.config.base_url,
                    "content_hash": generate_content_hash(metadata['og_email']),
                    "extracted_at": datetime.now().isoformat()
                }
                contact_data.append(contact_item)
                
        except Exception as e:
            self.logger.error(f"Error scraping contact info: {e}")
            
        return contact_data
        
    async def _scrape_programs(self) -> List[Dict[str, Any]]:
        """Scrape social programs and initiatives."""
        programs_data = []
        
        try:
            # Common programs URLs
            programs_urls = [
                f"{self.config.base_url}/programas",
                f"{self.config.base_url}/iniciativas",
                f"{self.config.base_url}/proyectos",
                f"{self.config.base_url}/social"
            ]
            
            for url in programs_urls:
                try:
                    html = await self.fetch_page(url)
                    if not html:
                        continue
                        
                    soup = self.parse_html(html)
                    
                    # Look for program elements
                    program_selectors = [
                        'div.program', 'article.program', 'div.iniciativa',
                        'div.proyecto', 'div.iniciativa-social'
                    ]
                    
                    for selector in program_selectors:
                        program_elements = soup.select(selector)
                        for element in program_elements:
                            try:
                                title_elem = element.select_one('h2, h3, .title, .titulo')
                                description_elem = element.select_one('p, .description, .descripcion')
                                objectives_elem = element.select_one('.objectives, .objetivos')
                                beneficiaries_elem = element.select_one('.beneficiaries, .beneficiarios')
                                link_elem = element.select_one('a')
                                
                                title = clean_text(title_elem.get_text()) if title_elem else None
                                description = clean_text(description_elem.get_text()) if description_elem else None
                                objectives = clean_text(objectives_elem.get_text()) if objectives_elem else None
                                beneficiaries = clean_text(beneficiaries_elem.get_text()) if beneficiaries_elem else None
                                link = link_elem.get('href') if link_elem else None
                                
                                normalized_link = normalize_url(self.config.base_url, str(link)) if link else None
                                
                                if title:
                                    program_item = {
                                        "type": "program",
                                        "title": title,
                                        "description": description,
                                        "objectives": objectives,
                                        "beneficiaries": beneficiaries,
                                        "url": normalized_link,
                                        "source_url": url,
                                        "content_hash": generate_content_hash(title + (description or "")),
                                        "extracted_at": datetime.now().isoformat()
                                    }
                                    programs_data.append(program_item)
                                    
                            except Exception as e:
                                self.logger.warning(f"Error processing program item: {e}")
                                continue
                                
                except Exception as e:
                    self.logger.warning(f"Error fetching programs URL {url}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error scraping programs: {e}")
            
        return programs_data