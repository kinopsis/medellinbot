
"""
Unified Storage Service
=======================

Service for managing data storage across Cloud SQL, Firestore, and Vector Search with integrated monitoring.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
import time

from web_scraping.core.database import db_manager
from web_scraping.config.firestore_config import get_firestore_manager
from web_scraping.config.vector_search_config import get_vector_search_manager
from web_scraping.services.data_processor import DataProcessor, ProcessingResult
from web_scraping.monitoring.monitor import get_monitoring_service

logger = logging.getLogger(__name__)

@dataclass
class StorageConfig:
    """Storage configuration for different data types."""
    primary_storage: str  # "cloud_sql", "firestore", or "both"
    cache_enabled: bool = True
    vector_search_enabled: bool = True
    ttl_days: Optional[int] = None  # For temporary data
    criticality: int = 5  # 1-10, affects caching and retention

class StorageService:
    """Unified service for managing data storage across multiple backends with integrated monitoring."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_processor = DataProcessor()
        self.firestore_manager = None
        self.vector_search_manager = None
        self.monitoring_service = get_monitoring_service()
        self._initialize_optional_services()
        
        # Default storage configurations
        self.storage_configs = {
            "tramites": StorageConfig(
                primary_storage="cloud_sql",
                cache_enabled=True,
                vector_search_enabled=True,
                criticality=8
            ),
            "pqrsd": StorageConfig(
                primary_storage="cloud_sql",
                cache_enabled=True,
                vector_search_enabled=True,
                criticality=7
            ),
            "pico_placa": StorageConfig(
                primary_storage="firestore",
                cache_enabled=True,
                vector_search_enabled=False,
                ttl_days=1,
                criticality=10
            ),
            "notificaciones": StorageConfig(
                primary_storage="firestore",
                cache_enabled=True,
                vector_search_enabled=False,
                ttl_days=7,
                criticality=9
            ),
            "programas_sociales": StorageConfig(
                primary_storage="both",
                cache_enabled=True,
                vector_search_enabled=True,
                criticality=7
            ),
            "temporal": StorageConfig(
                primary_storage="firestore",
                cache_enabled=False,
                vector_search_enabled=False,
                ttl_days=3,
                criticality=3
            )
        }
    
    def _initialize_optional_services(self):
        """Initialize optional storage services."""
        try:
            self.firestore_manager = get_firestore_manager()
        except Exception as e:
            self.logger.warning(f"Firestore not available: {e}")
        
        try:
            self.vector_search_manager = get_vector_search_manager()
        except Exception as e:
            self.logger.warning(f"Vector Search not available: {e}")
    
    async def store_data(self, source: str, data_type: str, raw_data: List[Dict[str, Any]], 
                        custom_config: Optional[StorageConfig] = None) -> Dict[str, Any]:
        """Store data using appropriate storage backend based on configuration."""
        try:
            self.logger.info(f"Storing {len(raw_data)} records from {source}/{data_type}")
            
            # Get storage configuration
            config = custom_config or self.storage_configs.get(data_type)
            if not config:
                # Default configuration for unknown data types
                config = StorageConfig(primary_storage="cloud_sql", cache_enabled=True, vector_search_enabled=True)
            
            # Process data
            processing_result = await self.data_processor.process_scraped_data(
                source=source,
                data_type=data_type,
                raw_data=raw_data
            )
            
            if not processing_result.success:
                return {
                    "success": False,
                    "errors": processing_result.errors,
                    "message": "Data processing failed"
                }
            
            stored_locations = []
            errors = []
            
            # Store in primary storage
            if config.primary_storage == "cloud_sql":
                cloud_sql_success = await self._store_in_cloud_sql(
                    source, data_type, processing_result.processed_data
                )
                if cloud_sql_success:
                    stored_locations.append("cloud_sql")
                else:
                    errors.append("Failed to store in Cloud SQL")
            
            elif config.primary_storage == "firestore":
                firestore_success = await self._store_in_firestore(
                    source, data_type, processing_result.processed_data, config
                )
                if firestore_success:
                    stored_locations.append("firestore")
                else:
                    errors.append("Failed to store in Firestore")
            
            elif config.primary_storage == "both":
                # Store in both, but don't fail if one fails
                cloud_sql_success = await self._store_in_cloud_sql(
                    source, data_type, processing_result.processed_data
                )
                firestore_success = await self._store_in_firestore(
                    source, data_type, processing_result.processed_data, config
                )
                
                if cloud_sql_success:
                    stored_locations.append("cloud_sql")
                if firestore_success:
                    stored_locations.append("firestore")
            
            # Store in vector search if enabled and configured
            if config.vector_search_enabled and self.vector_search_manager:
                vector_success = await self._store_in_vector_search(
                    source, data_type, processing_result.processed_data
                )
                if vector_success:
                    stored_locations.append("vector_search")
                else:
                    errors.append("Failed to store in Vector Search")
            
            # Cache processed data if enabled
            if config.cache_enabled and self.firestore_manager:
                cache_success = await self._cache_processed_data(
                    source, data_type, processing_result.processed_data
                )
                if cache_success:
                    stored_locations.append("cache")
            
            return {
                "success": len(stored_locations) > 0,
                "stored_locations": stored_locations,
                "errors": errors,
                "processing_result": {
                    "quality_score": processing_result.quality_score.value,
                    "duplicate_count": processing_result.duplicate_count,
                    "record_count": len(processing_result.processed_data)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error storing data: {e}")
            return {
                "success": False,
                "errors": [str(e)],
                "message": "Storage operation failed"
            }
    
    async def _store_in_cloud_sql(self, source: str, data_type: str,
                                data: List[Dict[str, Any]]) -> bool:
        """Store data in Cloud SQL."""
        start_time = time.time()
        try:
            async def save_batch():
                for record in data:
                    await db_manager.save_scraped_data(
                        source=source,
                        data_type=data_type,
                        content=record,
                        is_valid=True,
                        metadata={"storage_type": "cloud_sql", "stored_at": datetime.now().isoformat()}
                    )
            
            await save_batch()
            duration = time.time() - start_time
            self.logger.debug(f"Stored {len(data)} records in Cloud SQL in {duration:.2f}s")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store in Cloud SQL: {e}")
            return False
    
    async def _store_in_firestore(self, source: str, data_type: str,
                                data: List[Dict[str, Any]], config: StorageConfig) -> bool:
        """Store data in Firestore with monitoring."""
        start_time = time.time()
        try:
            if not self.firestore_manager:
                return False
            
            collection_name = f"{source}_{data_type}"
            
            # Store as temporary data if TTL is specified
            if config.ttl_days:
                for record in data:
                    write_start = time.time()
                    try:
                        await self.firestore_manager.save_temporary_data(
                            data_type=f"{source}_{data_type}",
                            data={
                                **record,
                                "source": source,
                                "data_type": data_type,
                                "stored_at": datetime.now().isoformat()
                            },
                            ttl_days=config.ttl_days
                        )
                        write_duration = time.time() - write_start
                        self.monitoring_service.record_firestore_write(collection_name, "temporary_save", write_duration)
                    except Exception as e:
                        self.monitoring_service.record_firestore_error(collection_name, type(e).__name__)
                        raise
            else:
                # Store as regular documents
                for record in data:
                    write_start = time.time()
                    try:
                        doc_id = f"{record.get('content_hash', '')}_{datetime.now().timestamp()}"
                        collection = self.firestore_manager.get_collection_ref(collection_name)
                        collection.document(doc_id).set({
                            **record,
                            "source": source,
                            "data_type": data_type,
                            "stored_at": datetime.now().isoformat()
                        })
                        write_duration = time.time() - write_start
                        self.monitoring_service.record_firestore_write(collection_name, "document_set", write_duration)
                    except Exception as e:
                        self.monitoring_service.record_firestore_error(collection_name, type(e).__name__)
                        raise
            
            duration = time.time() - start_time
            self.logger.debug(f"Stored {len(data)} records in Firestore in {duration:.2f}s")
            
            # Update document count metric
            try:
                doc_count = await self._get_firestore_document_count(collection_name)
                self.monitoring_service.update_firestore_document_count(collection_name, doc_count)
            except Exception as e:
                self.logger.warning(f"Failed to update document count for {collection_name}: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store in Firestore: {e}")
            return False
    
    async def _store_in_vector_search(self, source: str, data_type: str,
                                    data: List[Dict[str, Any]]) -> bool:
        """Store data in Vector Search for semantic search with monitoring."""
        start_time = time.time()
        try:
            if not self.vector_search_manager:
                return False
            
            # Extract text content for embedding
            texts = []
            metadata_list = []
            ids = []
            
            for i, record in enumerate(data):
                text_content = self._extract_text_for_embedding(record)
                if text_content.strip():
                    texts.append(text_content)
                    metadata_list.append({
                        'source': source,
                        'data_type': data_type,
                        'record_id': record.get('id', f"{source}_{data_type}_{i}"),
                        'content_hash': record.get('content_hash', ''),
                        'extracted_at': record.get('extracted_at', ''),
                        'stored_at': datetime.now().isoformat()
                    })
                    ids.append(f"{source}_{data_type}_{record.get('content_hash', str(i))}")
            
            if texts:
                # Generate embeddings with monitoring
                embedding_start = time.time()
                try:
                    embeddings = await self.vector_search_manager.generate_embeddings(texts)
                    embedding_duration = time.time() - embedding_start
                    self.monitoring_service.record_vector_embedding("text-embedding-004", embedding_duration)
                except Exception as e:
                    self.monitoring_service.record_vector_search_error("embedding_generation", type(e).__name__)
                    raise
                
                # Upsert embeddings with monitoring
                upsert_start = time.time()
                try:
                    success = await self.vector_search_manager.upsert_embeddings(
                        ids=ids,
                        embeddings=embeddings,
                        metadata=metadata_list
                    )
                    upsert_duration = time.time() - upsert_start
                    self.monitoring_service.record_vector_upsert(f"{source}_{data_type}_index", upsert_duration)
                except Exception as e:
                    self.monitoring_service.record_vector_search_error("vector_upsert", type(e).__name__)
                    raise
                
                if success:
                    duration = time.time() - start_time
                    self.logger.debug(f"Stored {len(embeddings)} embeddings in Vector Search in {duration:.2f}s")
                    
                    # Update index metrics
                    try:
                        index_size = await self._get_vector_index_size(f"{source}_{data_type}_index")
                        self.monitoring_service.update_vector_index_size(f"{source}_{data_type}_index", index_size)
                        self.monitoring_service.update_vector_index_dimensions(f"{source}_{data_type}_index", len(embeddings[0]) if embeddings else 0)
                    except Exception as e:
                        self.logger.warning(f"Failed to update index metrics: {e}")
                    
                return success
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store in Vector Search: {e}")
            return False
    
    async def _cache_processed_data(self, source: str, data_type: str, 
                                   data: List[Dict[str, Any]]) -> bool:
        """Cache processed data in Firestore for quick access."""
        try:
            if not self.firestore_manager:
                return False
            
            cache_key = f"{source}_{data_type}_processed"
            cache_data = {
                'data': data,
                'source': source,
                'data_type': data_type,
                'processed_at': datetime.now().isoformat(),
                'record_count': len(data)
            }
            
            # Cache for 24 hours by default
            success = await self.firestore_manager.save_cache_entry(
                cache_key=cache_key,
                data=cache_data,
                ttl_days=1
            )
            
            if success:
                self.logger.debug(f"Cached {len(data)} records")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to cache data: {e}")
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
    
    async def retrieve_data(self, source: str, data_type: str, 
                           use_cache: bool = True) -> List[Dict[str, Any]]:
        """Retrieve data from appropriate storage backend."""
        try:
            # Try cache first if enabled
            if use_cache and self.firestore_manager:
                cache_key = f"{source}_{data_type}_processed"
                cached_data = await self.firestore_manager.get_cache_entry(cache_key)
                
                if cached_data and 'data' in cached_data:
                    self.logger.debug(f"Retrieved {len(cached_data['data'])} records from cache")
                    return cached_data['data']
            
            # Fall back to primary storage
            config = self.storage_configs.get(data_type)
            if not config:
                config = StorageConfig(primary_storage="cloud_sql")
            
            if config.primary_storage == "cloud_sql":
                return db_manager.get_recent_data(source, data_type, limit=1000)
            elif config.primary_storage == "firestore":
                return await self._retrieve_from_firestore(source, data_type)
            elif config.primary_storage == "both":
                # Try Cloud SQL first, then Firestore
                cloud_sql_data = db_manager.get_recent_data(source, data_type, limit=1000)
                if cloud_sql_data:
                    return cloud_sql_data
                return await self._retrieve_from_firestore(source, data_type)
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error retrieving data: {e}")
            return []
    
    async def _retrieve_from_firestore(self, source: str, data_type: str) -> List[Dict[str, Any]]:
        """Retrieve data from Firestore."""
        try:
            if not self.firestore_manager:
                return []
            
            collection_name = f"{source}_{data_type}"
            collection = self.firestore_manager.get_collection_ref(collection_name)
            
            docs = collection.stream()
            data = []
            
            for doc in docs:
                doc_data = doc.to_dict()
                # Remove Firestore-specific fields
                doc_data.pop('stored_at', None)
                data.append(doc_data)
            
            self.logger.debug(f"Retrieved {len(data)} records from Firestore")
            return data
            
        except Exception as e:
            self.logger.error(f"Error retrieving from Firestore: {e}")
            return []
    
    async def search_similar_content(self, query: str, data_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search for similar content using vector search."""
        try:
            if not self.vector_search_manager:
                return []
            
            # Generate embedding for query
            query_embedding = await self.vector_search_manager.generate_embeddings([query])
            
            if not query_embedding:
                return []
            
            # Search for similar vectors
            results = await self.vector_search_manager.search_similar_vectors(
                query_embedding=query_embedding[0],
                num_neighbors=10
            )
            
            # Enrich results with metadata
            enriched_results = []
            for result in results:
                enriched_result = {
                    "id": result["id"],
                    "distance": result["distance"],
                    "metadata": result.get("metadata", {}),
                    "relevance_score": 1 - result["distance"]  # Convert distance to relevance score
                }
                enriched_results.append(enriched_result)
            
            # Sort by relevance score
            enriched_results.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            return enriched_results
            
        except Exception as e:
            self.logger.error(f"Error in vector search: {e}")
            return []
    
    async def cleanup_expired_data(self) -> Dict[str, int]:
        """Clean up expired data from Firestore."""
        try:
            if not self.firestore_manager:
                return {}
            
            result = await self.firestore_manager.cleanup_all_expired()
            
            # Record cleanup metrics
            for collection, count in result.items():
                self.monitoring_service.record_firestore_write(collection, "cleanup", 0)
                # Update document count after cleanup
                try:
                    doc_count = await self._get_firestore_document_count(collection)
                    self.monitoring_service.update_firestore_document_count(collection, doc_count)
                except Exception as e:
                    self.logger.warning(f"Failed to update document count after cleanup for {collection}: {e}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error cleaning up expired data: {e}")
            return {}
    
    async def _get_firestore_document_count(self, collection_name: str) -> int:
        """Get the number of documents in a Firestore collection."""
        try:
            collection = self.firestore_manager.get_collection_ref(collection_name)
            docs = collection.stream()
            return sum(1 for _ in docs)
        except Exception as e:
            self.logger.warning(f"Failed to get document count for {collection_name}: {e}")
            return 0
    
    async def _get_vector_index_size(self, index_name: str) -> int:
        """Get the number of vectors in a Vector Search index."""
        try:
            # This would depend on the specific Vector Search implementation
            # For now, return a placeholder value
            return 0
        except Exception as e:
            self.logger.warning(f"Failed to get index size for {index_name}: {e}")
            return 0
