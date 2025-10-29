"""
Data Processing and Validation Pipeline
=======================================

Service for processing, validating, and normalizing scraped data with vector search integration.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import hashlib
from dataclasses import dataclass
from enum import Enum

from web_scraping.core.database import db_manager
from web_scraping.core.utils import generate_content_hash, parse_date_string
from web_scraping.config.settings import config
from web_scraping.config.firestore_config import get_firestore_manager
from web_scraping.config.vector_search_config import get_vector_search_manager

class DataQuality(Enum):
    """Data quality levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INVALID = "invalid"

@dataclass
class ProcessingResult:
    """Result of data processing operation."""
    success: bool
    processed_data: List[Dict[str, Any]]
    errors: List[str]
    warnings: List[str]
    quality_score: DataQuality
    duplicate_count: int

class DataProcessor:
    """Service for processing and validating scraped data with vector search integration."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.duplicate_threshold = 0.9  # 90% similarity threshold
        self.firestore_manager = None
        self.vector_search_manager = None
        self._initialize_optional_managers()
    
    def _initialize_optional_managers(self):
        """Initialize optional managers if configured."""
        try:
            self.firestore_manager = get_firestore_manager()
        except Exception as e:
            self.logger.debug(f"Firestore not configured: {e}")
        
        try:
            self.vector_search_manager = get_vector_search_manager()
        except Exception as e:
            self.logger.debug(f"Vector Search not configured: {e}")
    
    async def process_scraped_data(self, source: str, data_type: str, 
                                  raw_data: List[Dict[str, Any]]) -> ProcessingResult:
        """Process and validate scraped data."""
        try:
            self.logger.info(f"Processing {len(raw_data)} records from {source}")
            
            # 1. Clean and normalize data
            cleaned_data = self._clean_data(raw_data)
            
            # 2. Validate data structure
            validated_data, validation_errors = self._validate_data_structure(cleaned_data)
            
            # 3. Remove duplicates
            deduplicated_data, duplicate_count = self._remove_duplicates(validated_data)
            
            # 4. Normalize data formats
            normalized_data = self._normalize_data_formats(deduplicated_data)
            
            # 5. Calculate quality score
            quality_score = self._calculate_quality_score(normalized_data, validation_errors)
            
            # 6. Save to database
            save_success = self._save_to_database(source, data_type, normalized_data)
            
            # 7. Generate embeddings for vector search (if configured)
            if self.vector_search_manager and save_success:
                await self._generate_and_store_embeddings(source, data_type, normalized_data)
            
            # 8. Cache processed data in Firestore (if configured)
            if self.firestore_manager:
                await self._cache_processed_data(source, data_type, normalized_data)
            
            # 9. Generate warnings for potential issues
            warnings = self._generate_warnings(normalized_data)
            
            return ProcessingResult(
                success=save_success,
                processed_data=normalized_data,
                errors=validation_errors,
                warnings=warnings,
                quality_score=quality_score,
                duplicate_count=duplicate_count
            )
            
        except Exception as e:
            self.logger.error(f"Error processing data from {source}: {e}")
            return ProcessingResult(
                success=False,
                processed_data=[],
                errors=[str(e)],
                warnings=[],
                quality_score=DataQuality.INVALID,
                duplicate_count=0
            )
    
    def _clean_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean and normalize raw scraped data."""
        cleaned_data = []
        
        for record in data:
            if not isinstance(record, dict):
                continue
                
            cleaned_record = {}
            
            for key, value in record.items():
                # Clean string values
                if isinstance(value, str):
                    cleaned_value = value.strip()
                    if cleaned_value:  # Only include non-empty strings
                        cleaned_record[key] = cleaned_value
                elif value is not None:  # Include non-null values
                    cleaned_record[key] = value
                    
            # Ensure required fields
            if 'type' not in cleaned_record:
                cleaned_record['type'] = 'unknown'
                
            if 'extracted_at' not in cleaned_record:
                cleaned_record['extracted_at'] = datetime.now().isoformat()
                
            cleaned_data.append(cleaned_record)
            
        return cleaned_data
    
    def _validate_data_structure(self, data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Validate data structure and content."""
        validated_data = []
        errors = []
        
        required_fields = ['type', 'extracted_at']
        
        for i, record in enumerate(data):
            record_errors = []
            
            # Check required fields
            for field in required_fields:
                if field not in record:
                    record_errors.append(f"Record {i}: Missing required field '{field}'")
                    
            # Validate field types
            if 'date' in record and record['date']:
                try:
                    parsed_date = parse_date_string(record['date'])
                    if parsed_date is None:
                        record_errors.append(f"Record {i}: Invalid date format")
                    else:
                        record['date'] = parsed_date.isoformat()
                except Exception:
                    record_errors.append(f"Record {i}: Invalid date format")
                    
            # Validate URLs
            if 'url' in record and record['url']:
                if not record['url'].startswith(('http://', 'https://')):
                    record_errors.append(f"Record {i}: Invalid URL format")
                    
            if not record_errors:
                validated_data.append(record)
            else:
                errors.extend(record_errors)
                
        return validated_data, errors
    
    def _remove_duplicates(self, data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
        """Remove duplicate records based on content similarity."""
        if not data:
            return data, 0
            
        unique_data = []
        duplicates = 0
        seen_hashes = set()
        
        for record in data:
            # Create a content hash for deduplication
            content_for_hash = json.dumps({
                k: v for k, v in record.items() 
                if k not in ['extracted_at', 'content_hash']
            }, sort_keys=True)
            
            content_hash = hashlib.md5(content_for_hash.encode()).hexdigest()
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                record['content_hash'] = content_hash
                unique_data.append(record)
            else:
                duplicates += 1
                
        return unique_data, duplicates
    
    def _normalize_data_formats(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize data formats across records."""
        normalized_data = []
        
        for record in data:
            normalized_record = record.copy()
            
            # Normalize text fields
            for key, value in record.items():
                if isinstance(value, str):
                    # Remove extra whitespace
                    normalized_record[key] = ' '.join(value.split())
                    
                # Normalize lists
                elif isinstance(value, list):
                    # Remove empty strings and None values from lists
                    normalized_record[key] = [item for item in value if item not in ['', None]]
                    
            normalized_data.append(normalized_record)
            
        return normalized_data
    
    def _calculate_quality_score(self, data: List[Dict[str, Any]], 
                               validation_errors: List[str]) -> DataQuality:
        """Calculate data quality score."""
        if not data:
            return DataQuality.INVALID
            
        total_records = len(data)
        if total_records == 0:
            return DataQuality.INVALID
            
        # Count records with complete required information
        complete_records = sum(1 for record in data 
                             if all(field in record and record[field] 
                                   for field in ['type', 'extracted_at']))
        
        completeness_ratio = complete_records / total_records
        
        # Calculate error ratio
        error_ratio = len(validation_errors) / total_records
        
        # Determine quality score
        if completeness_ratio >= 0.9 and error_ratio <= 0.1:
            return DataQuality.HIGH
        elif completeness_ratio >= 0.7 and error_ratio <= 0.2:
            return DataQuality.MEDIUM
        elif completeness_ratio >= 0.5 and error_ratio <= 0.3:
            return DataQuality.LOW
        else:
            return DataQuality.INVALID
    
    def _save_to_database(self, source: str, data_type: str, 
                         data: List[Dict[str, Any]]) -> bool:
        """Save processed data to database."""
        try:
            loop = asyncio.get_event_loop()
            
            async def save_batch():
                for record in data:
                    await db_manager.save_scraped_data(
                        source=source,
                        data_type=data_type,
                        content=record,
                        is_valid=True
                    )
                    
            loop.run_until_complete(save_batch())
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save data to database: {e}")
            return False
    
    async def _generate_and_store_embeddings(self, source: str, data_type: str, 
                                           data: List[Dict[str, Any]]) -> bool:
        """Generate embeddings for vector search and store them."""
        try:
            # Extract text content for embedding generation
            texts = []
            metadata_list = []
            ids = []
            
            for i, record in enumerate(data):
                # Create text content from record
                text_content = self._extract_text_for_embedding(record)
                if text_content.strip():
                    texts.append(text_content)
                    metadata_list.append({
                        'source': source,
                        'data_type': data_type,
                        'record_id': record.get('id', f"{source}_{data_type}_{i}"),
                        'content_hash': record.get('content_hash', ''),
                        'extracted_at': record.get('extracted_at', '')
                    })
                    ids.append(f"{source}_{data_type}_{record.get('content_hash', str(i))}")
            
            if texts:
                # Generate embeddings
                embeddings = await self.vector_search_manager.generate_embeddings(texts)
                
                # Store embeddings
                success = await self.vector_search_manager.upsert_embeddings(
                    ids=ids,
                    embeddings=embeddings,
                    metadata=metadata_list
                )
                
                if success:
                    self.logger.info(f"Generated and stored {len(embeddings)} embeddings for {source}/{data_type}")
                
                return success
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings: {e}")
            return False
    
    def _extract_text_for_embedding(self, record: Dict[str, Any]) -> str:
        """Extract relevant text content from record for embedding generation."""
        text_parts = []
        
        # Prioritize important fields for semantic meaning
        important_fields = ['title', 'content', 'description', 'summary', 'body', 'text']
        
        for field in important_fields:
            if field in record and isinstance(record[field], str):
                text_parts.append(record[field])
        
        # Fallback to all string values if important fields are missing
        if not text_parts:
            for key, value in record.items():
                if isinstance(value, str) and len(value) > 10:  # Skip very short strings
                    text_parts.append(value)
        
        return ' '.join(text_parts)
    
    async def _cache_processed_data(self, source: str, data_type: str, 
                                  data: List[Dict[str, Any]]) -> bool:
        """Cache processed data in Firestore for quick access."""
        try:
            cache_key = f"{source}_{data_type}_processed"
            cache_data = {
                'data': data,
                'source': source,
                'data_type': data_type,
                'processed_at': datetime.now().isoformat(),
                'record_count': len(data)
            }
            
            success = await self.firestore_manager.save_cache_entry(
                cache_key=cache_key,
                data=cache_data,
                ttl_days=1  # Cache for 1 day
            )
            
            if success:
                self.logger.debug(f"Cached {len(data)} records for {source}/{data_type}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to cache data: {e}")
            return False
    
    def _generate_warnings(self, data: List[Dict[str, Any]]) -> List[str]:
        """Generate warnings for potential data issues."""
        warnings = []
        
        # Check for records with missing optional but important fields
        important_fields = ['title', 'content', 'description']
        
        for i, record in enumerate(data):
            missing_important = [field for field in important_fields 
                               if field not in record or not record[field]]
                               
            if len(missing_important) >= 2:
                warnings.append(f"Record {i}: Missing multiple important fields: {', '.join(missing_important)}")
                
        return warnings
    
    async def get_data_quality_report(self, source: Optional[str] = None,
                                    data_type: Optional[str] = None) -> Dict[str, Any]:
        """Generate data quality report."""
        try:
            # Get data from database
            if source and data_type:
                raw_data = db_manager.get_recent_data(source, data_type, limit=1000)
            else:
                # This would need to be implemented based on your database query capabilities
                raw_data = []
                
            if not raw_data:
                return {
                    "source": source,
                    "data_type": data_type,
                    "total_records": 0,
                    "quality_score": DataQuality.INVALID.value,
                    "issues": ["No data available"]
                }
                
            # Process data for quality assessment
            cleaned_data = self._clean_data(raw_data)
            validated_data, validation_errors = self._validate_data_structure(cleaned_data)
            quality_score = self._calculate_quality_score(validated_data, validation_errors)
            
            return {
                "source": source,
                "data_type": data_type,
                "total_records": len(raw_data),
                "clean_records": len(cleaned_data),
                "validated_records": len(validated_data),
                "quality_score": quality_score.value,
                "validation_errors": validation_errors,
                "duplicate_count": len(raw_data) - len(validated_data) + len(validation_errors)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating quality report: {e}")
            return {
                "source": source,
                "data_type": data_type,
                "error": str(e)
            }
