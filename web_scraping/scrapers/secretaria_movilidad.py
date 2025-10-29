"""
Secretaría de Movilidad de Medellín Scraper
===========================================

Scraper for collecting data from the Secretaría de Movilidad website with unified storage integration.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from web_scraping.core.base_scraper import BaseScraper, ScrapingConfig, ScrapingResult
from web_scraping.core.utils import (
    extract_metadata, clean_text, extract_emails, extract_phone_numbers,
    parse_date_string, normalize_url, generate_content_hash
)
from web_scraping.config.settings import get_source_config
from web_scraping.services.storage_service import StorageService

class SecretariaMovilidadScraper(BaseScraper):
    """Scraper for Secretaría de Movilidad de Medellín website with unified storage integration."""
    
    def __init__(self):
        source_config = get_source_config("secretaria_movilidad")
        config = ScrapingConfig(
            base_url=source_config.get("base_url", "https://movilidadmedellin.gov.co"),
            rate_limit_delay=source_config.get("rate_limit_delay", 1.5),
            timeout=source_config.get("timeout", 25),
            user_agent="MedellínBot/1.0"
        )
        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.storage_service = StorageService()
        
    async def scrape(self) -> ScrapingResult:
        """Main scraping method for Secretaría de Movilidad with unified storage integration."""
        try:
            self.logger.info("Starting Secretaría de Movilidad scraping")
            
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
            
            # 1. Extract traffic information
            traffic_data = await self._scrape_traffic_info(soup)
            data.extend(traffic_data)
            
            # 2. Extract pico y placa information
            pico_placa_data = await self._scrape_pico_placa()
            data.extend(pico_placa_data)
            
            # 3. Extract vial closures
            vial_closures_data = await self._scrape_vial_closures()
            data.extend(vial_closures_data)
            
            # 4. Extract contact information
            contact_data = await self._scrape_contact_info(soup)
            data.extend(contact_data)
            
            # Store data using unified storage service
            storage_result = await self.storage_service.store_data(
                source="secretaria_movilidad",
                data_type="general",
                raw_data=data
            )
            
            # Validate data
            is_valid, validation_errors = self.validate_data(data)
            
            return ScrapingResult(
                success=storage_result["success"],
                data=data,
                metadata={
                    "source": "secretaria_movilidad",
                    "total_records": len(data),
                    "validation_errors": validation_errors if not is_valid else None,
                    "storage_result": storage_result
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error scraping Secretaría de Movilidad: {e}")
            return ScrapingResult(
                success=False,
                error_message=str(e)
            )
            
    async def _scrape_traffic_info(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Scrape traffic information and alerts."""
        traffic_data = []
        
        try:
            # Look for traffic information sections
            traffic_selectors = [
                'div.traffic-alert', 'div.traffic-info', 'div.alerta-trafico',
                'div.comunicado-transito', 'article.traffic'
            ]
            
            for selector in traffic_selectors:
                traffic_elements = soup.select(selector)
                for element in traffic_elements:
                    try:
                        title_elem = element.select_one('h2, h3, .title, .titulo')
                        content_elem = element.select_one('p, .content, .contenido')
                        location_elem = element.select_one('.location, .ubicacion')
                        severity_elem = element.select_one('.severity, .gravedad')
                        link_elem = element.select_one('a')
                        
                        title = clean_text(title_elem.get_text()) if title_elem else None
                        content = clean_text(content_elem.get_text()) if content_elem else None
                        location = clean_text(location_elem.get_text()) if location_elem else None
                        severity = clean_text(severity_elem.get_text()) if severity_elem else None
                        link = link_elem.get('href') if link_elem else None
                        
                        if title and content:
                            traffic_item = {
                                "type": "traffic_alert",
                                "title": title,
                                "content": content,
                                "location": location,
                                "severity": severity,
                                "url": normalize_url(self.config.base_url, str(link)) if link else None,
                                "source_url": self.config.base_url,
                                "content_hash": generate_content_hash(content),
                                "extracted_at": datetime.now().isoformat()
                            }
                            traffic_data.append(traffic_item)
                            
                    except Exception as e:
                        self.logger.warning(f"Error processing traffic item: {e}")
                        continue
                        
        except Exception as e:
            self.logger.error(f"Error scraping traffic info: {e}")
            
        return traffic_data
        
    async def _scrape_pico_placa(self) -> List[Dict[str, Any]]:
        """Scrape pico y placa information."""
        pico_placa_data = []
        
        try:
            # Common pico y placa URLs
            pico_placa_urls = [
                f"{self.config.base_url}/pico-y-placa",
                f"{self.config.base_url}/transito/pico-placa",
                f"{self.config.base_url}/movilidad/pico-placa"
            ]
            
            for url in pico_placa_urls:
                try:
                    html = await self.fetch_page(url)
                    if not html:
                        continue
                        
                    soup = self.parse_html(html)
                    
                    # Look for pico y placa information
                    pico_placa_selectors = [
                        'div.pico-placa', 'div.restriccion', 'table.pico-placa',
                        'div.movilidad-restriccion'
                    ]
                    
                    for selector in pico_placa_selectors:
                        pico_placa_elements = soup.select(selector)
                        for element in pico_placa_elements:
                            try:
                                title_elem = element.select_one('h2, h3, .title, .titulo')
                                content_elem = element.select_one('p, .content, .contenido')
                                table_elem = element.select_one('table')
                                
                                title = clean_text(title_elem.get_text()) if title_elem else None
                                content = clean_text(content_elem.get_text()) if content_elem else None
                                
                                # Extract table data if available
                                restrictions = []
                                if table_elem:
                                    rows = table_elem.select('tr')
                                    for row in rows:
                                        cells = row.select('td, th')
                                        if len(cells) >= 2:
                                            day = clean_text(cells[0].get_text())
                                            plate_numbers = clean_text(cells[1].get_text())
                                            restrictions.append({
                                                "day": day,
                                                "plate_numbers": plate_numbers
                                            })
                                
                                if title or content:
                                    pico_placa_item = {
                                        "type": "pico_placa",
                                        "title": title,
                                        "content": content,
                                        "restrictions": restrictions,
                                        "url": url,
                                        "source_url": url,
                                        "content_hash": generate_content_hash((title or "") + (content or "")),
                                        "extracted_at": datetime.now().isoformat()
                                    }
                                    pico_placa_data.append(pico_placa_item)
                                    
                            except Exception as e:
                                self.logger.warning(f"Error processing pico y placa item: {e}")
                                continue
                                
                except Exception as e:
                    self.logger.warning(f"Error fetching pico y placa URL {url}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error scraping pico y placa: {e}")
            
        return pico_placa_data
        
    async def _scrape_vial_closures(self) -> List[Dict[str, Any]]:
        """Scrape vial closure information."""
        closures_data = []
        
        try:
            # Common vial closure URLs
            closures_urls = [
                f"{self.config.base_url}/cierres-viales",
                f"{self.config.base_url}/transito/cierres",
                f"{self.config.base_url}/movilidad/cierres-viales"
            ]
            
            for url in closures_urls:
                try:
                    html = await self.fetch_page(url)
                    if not html:
                        continue
                        
                    soup = self.parse_html(html)
                    
                    # Look for vial closure information
                    closure_selectors = [
                        'div.cierre-vial', 'div.cierre', 'article.cierre',
                        'div.alerta-vial'
                    ]
                    
                    for selector in closure_selectors:
                        closure_elements = soup.select(selector)
                        for element in closure_elements:
                            try:
                                title_elem = element.select_one('h2, h3, .title, .titulo')
                                content_elem = element.select_one('p, .content, .contenido')
                                location_elem = element.select_one('.location, .ubicacion')
                                date_elem = element.select_one('.date, .fecha, time')
                                link_elem = element.select_one('a')
                                
                                title = clean_text(title_elem.get_text()) if title_elem else None
                                content = clean_text(content_elem.get_text()) if content_elem else None
                                location = clean_text(location_elem.get_text()) if location_elem else None
                                date_str = clean_text(date_elem.get_text()) if date_elem else None
                                link = link_elem.get('href') if link_elem else None
                                
                                parsed_date = parse_date_string(date_str) if date_str else None
                                
                                if title or content:
                                    closure_item = {
                                        "type": "vial_closure",
                                        "title": title,
                                        "content": content,
                                        "location": location,
                                        "date": parsed_date.isoformat() if parsed_date else None,
                                        "url": normalize_url(self.config.base_url, str(link)) if link else None,
                                        "source_url": url,
                                        "content_hash": generate_content_hash((title or "") + (content or "")),
                                        "extracted_at": datetime.now().isoformat()
                                    }
                                    closures_data.append(closure_item)
                                    
                            except Exception as e:
                                self.logger.warning(f"Error processing vial closure item: {e}")
                                continue
                                
                except Exception as e:
                    self.logger.warning(f"Error fetching vial closures URL {url}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error scraping vial closures: {e}")
            
        return closures_data
        
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