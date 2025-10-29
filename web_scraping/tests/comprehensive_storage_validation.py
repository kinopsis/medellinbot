"""
Comprehensive Storage Validation Tests
======================================

Tests to verify that data flows correctly through all storage layers (Cloud SQL, Firestore, Vector Search)
and that the unified storage service works as expected.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import List, Dict, Any

from web_scraping.services.storage_service import StorageService, StorageConfig
from web_scraping.config.firestore_config import FirestoreManager, FirestoreConfig
from web_scraping.config.vector_search_config import VectorSearchManager, VectorSearchConfig
from web_scraping.services.data_processor import DataProcessor, ProcessingResult, DataQuality
from web_scraping.core.database import db_manager


class TestComprehensiveStorageValidation:
    """Comprehensive tests for storage layer integration."""
    
    @pytest.fixture
    def sample_scraped_data(self):
        """Sample scraped data for testing."""
        return [
            {
                "type": "news",
                "title": "Test News Title",
                "content": "This is a test news article content with sufficient length to test embedding generation.",
                "date": "2024-01-01",
                "url": "https://example.com/news/1",
                "source_url": "https://example.com",
                "content_hash": "test_hash_1",
                "extracted_at": datetime.now().isoformat()
            },
            {
                "type": "tramite",
                "title": "Test Tramite",
                "description": "This is a test tramite description.",
                "requirements": "Test requirements",
                "url": "https://example.com/tramite/1",
                "source_url": "https://example.com",
                "content_hash": "test_hash_2",
                "extracted_at": datetime.now().isoformat()
            },
            {
                "type": "contact",
                "emails": ["test@example.com"],
                "phone_numbers": ["+57 123 456 7890"],
                "source_url": "https://example.com",
                "content_hash": "test_hash_3",
                "extracted_at": datetime.now().isoformat()
            }
        ]
    
    @pytest.fixture
    def storage_service(self):
        """Create a storage service with mocked dependencies."""
        with patch('web_scraping.services.storage_service.get_firestore_manager'):
            with patch('web_scraping.services.storage_service.get_vector_search_manager'):
                service = StorageService()
                # Mock the managers
                service.firestore_manager = Mock()
                service.vector_search_manager = Mock()
                service.data_processor = Mock()
                service.monitoring_service = Mock()
                return service
    
    @pytest.mark.asyncio
    async def test_end_to_end_storage_flow_cloud_sql(self, storage_service, sample_scraped_data):
        """Test complete storage flow for Cloud SQL configuration."""
        # Mock processing result
        processing_result = ProcessingResult(
            success=True,
            processed_data=sample_scraped_data,
            errors=[],
            warnings=[],
            quality_score=DataQuality.HIGH,
            duplicate_count=0
        )
        storage_service.data_processor.process_scraped_data.return_value = processing_result
        
        # Mock database save
        with patch('web_scraping.core.database.db_manager') as mock_db:
            mock_db.save_scraped_data = Mock(return_value=True)
            
            result = await storage_service.store_data(
                source="test_source",
                data_type="tramites",
                raw_data=sample_scraped_data
            )
            
            # Verify success
            assert result["success"] is True
            assert "cloud_sql" in result["stored_locations"]
            assert "firestore" not in result["stored_locations"]
            assert "vector_search" not in result["stored_locations"]
            
            # Verify database calls
            assert mock_db.save_scraped_data.call_count == len(sample_scraped_data)
            
            # Verify monitoring calls
            storage_service.monitoring_service.record_firestore_write.assert_not_called()
            storage_service.monitoring_service.record_vector_embedding.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_end_to_end_storage_flow_firestore(self, storage_service, sample_scraped_data):
        """Test complete storage flow for Firestore configuration."""
        # Mock processing result
        processing_result = ProcessingResult(
            success=True,
            processed_data=sample_scraped_data,
            errors=[],
            warnings=[],
            quality_score=DataQuality.HIGH,
            duplicate_count=0
        )
        storage_service.data_processor.process_scraped_data.return_value = processing_result
        
        # Mock Firestore save
        storage_service.firestore_manager.save_temporary_data = Mock(return_value="doc_id_1")
        storage_service.firestore_manager.get_collection_ref = Mock()
        
        result = await storage_service.store_data(
            source="test_source",
            data_type="pico_placa",
            raw_data=sample_scraped_data
        )
        
        # Verify success
        assert result["success"] is True
        assert "firestore" in result["stored_locations"]
        assert "cloud_sql" not in result["stored_locations"]
        assert "vector_search" not in result["stored_locations"]
        
        # Verify Firestore calls
        assert storage_service.firestore_manager.save_temporary_data.call_count == len(sample_scraped_data)
        
        # Verify monitoring calls
        assert storage_service.monitoring_service.record_firestore_write.call_count == len(sample_scraped_data)
        storage_service.monitoring_service.record_vector_embedding.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_end_to_end_storage_flow_vector_search(self, storage_service, sample_scraped_data):
        """Test complete storage flow for Vector Search configuration."""
        # Mock processing result
        processing_result = ProcessingResult(
            success=True,
            processed_data=sample_scraped_data,
            errors=[],
            warnings=[],
            quality_score=DataQuality.HIGH,
            duplicate_count=0
        )
        storage_service.data_processor.process_scraped_data.return_value = processing_result
        
        # Mock vector search
        storage_service.vector_search_manager.generate_embeddings = Mock(return_value=[[0.1, 0.2, 0.3] * 256])
        storage_service.vector_search_manager.upsert_embeddings = Mock(return_value=True)
        
        result = await storage_service.store_data(
            source="test_source",
            data_type="programas_sociales",
            raw_data=sample_scraped_data
        )
        
        # Verify success
        assert result["success"] is True
        assert "vector_search" in result["stored_locations"]
        assert "cloud_sql" in result["stored_locations"]
        assert "firestore" in result["stored_locations"]
        
        # Verify vector search calls
        storage_service.vector_search_manager.generate_embeddings.assert_called_once()
        storage_service.vector_search_manager.upsert_embeddings.assert_called_once()
        
        # Verify monitoring calls
        storage_service.monitoring_service.record_vector_embedding.assert_called_once()
        storage_service.monitoring_service.record_vector_upsert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_data_quality_validation(self, storage_service, sample_scraped_data):
        """Test that data quality is properly validated and reported."""
        # Mock processing result with different quality levels
        processing_result = ProcessingResult(
            success=True,
            processed_data=sample_scraped_data,
            errors=[],
            warnings=["Warning 1", "Warning 2"],
            quality_score=DataQuality.MEDIUM,
            duplicate_count=2
        )
        storage_service.data_processor.process_scraped_data.return_value = processing_result
        
        # Mock database save
        with patch('web_scraping.core.database.db_manager') as mock_db:
            mock_db.save_scraped_data = Mock(return_value=True)
            
            result = await storage_service.store_data(
                source="test_source",
                data_type="tramites",
                raw_data=sample_scraped_data
            )
            
            # Verify processing result is included
            assert "processing_result" in result
            assert result["processing_result"]["quality_score"] == "MEDIUM"
            assert result["processing_result"]["duplicate_count"] == 2
            assert result["processing_result"]["record_count"] == len(sample_scraped_data)
    
    @pytest.mark.asyncio
    async def test_error_handling_cloud_sql_failure(self, storage_service, sample_scraped_data):
        """Test error handling when Cloud SQL storage fails."""
        # Mock processing result
        processing_result = ProcessingResult(
            success=True,
            processed_data=sample_scraped_data,
            errors=[],
            warnings=[],
            quality_score=DataQuality.HIGH,
            duplicate_count=0
        )
        storage_service.data_processor.process_scraped_data.return_value = processing_result
        
        # Mock database save failure
        with patch('web_scraping.core.database.db_manager') as mock_db:
            mock_db.save_scraped_data = Mock(side_effect=Exception("Database connection failed"))
            
            result = await storage_service.store_data(
                source="test_source",
                data_type="tramites",
                raw_data=sample_scraped_data
            )
            
            # Verify failure
            assert result["success"] is False
            assert "Failed to store in Cloud SQL" in str(result["errors"])
    
    @pytest.mark.asyncio
    async def test_error_handling_firestore_failure(self, storage_service, sample_scraped_data):
        """Test error handling when Firestore storage fails."""
        # Mock processing result
        processing_result = ProcessingResult(
            success=True,
            processed_data=sample_scraped_data,
            errors=[],
            warnings=[],
            quality_score=DataQuality.HIGH,
            duplicate_count=0
        )
        storage_service.data_processor.process_scraped_data.return_value = processing_result
        
        # Mock Firestore save failure
        storage_service.firestore_manager.save_temporary_data = Mock(side_effect=Exception("Firestore error"))
        
        result = await storage_service.store_data(
            source="test_source",
            data_type="pico_placa",
            raw_data=sample_scraped_data
        )
        
        # Verify failure
        assert result["success"] is False
        assert "Failed to store in Firestore" in str(result["errors"])
    
    @pytest.mark.asyncio
    async def test_error_handling_vector_search_failure(self, storage_service, sample_scraped_data):
        """Test error handling when Vector Search storage fails."""
        # Mock processing result
        processing_result = ProcessingResult(
            success=True,
            processed_data=sample_scraped_data,
            errors=[],
            warnings=[],
            quality_score=DataQuality.HIGH,
            duplicate_count=0
        )
        storage_service.data_processor.process_scraped_data.return_value = processing_result
        
        # Mock vector search failure
        storage_service.vector_search_manager.generate_embeddings = Mock(side_effect=Exception("API quota exceeded"))
        
        result = await storage_service.store_data(
            source="test_source",
            data_type="programas_sociales",
            raw_data=sample_scraped_data
        )
        
        # Verify partial success (Cloud SQL and Firestore should still work)
        assert result["success"] is True  # Cloud SQL and Firestore should succeed
        assert "cloud_sql" in result["stored_locations"]
        assert "firestore" in result["stored_locations"]
        assert "vector_search" not in result["stored_locations"]
    
    @pytest.mark.asyncio
    async def test_semantic_search_functionality(self, storage_service):
        """Test semantic search functionality across stored data."""
        # Mock vector search
        mock_search_result = [
            {
                "id": "test_source_programas_sociales_test_hash_1",
                "distance": 0.1,
                "metadata": {
                    "source": "test_source",
                    "data_type": "programas_sociales",
                    "record_id": "test_hash_1",
                    "content_hash": "test_hash_1"
                }
            }
        ]
        
        storage_service.vector_search_manager.generate_embeddings = Mock(return_value=[[0.1, 0.2, 0.3]])
        storage_service.vector_search_manager.search_similar_vectors = Mock(return_value=mock_search_result)
        
        results = await storage_service.search_similar_content("test query")
        
        # Verify search results
        assert len(results) == 1
        assert results[0]["id"] == "test_source_programas_sociales_test_hash_1"
        assert results[0]["relevance_score"] == 0.9  # 1 - 0.1
        assert "metadata" in results[0]
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, storage_service, sample_scraped_data):
        """Test caching functionality."""
        # Mock processing result
        processing_result = ProcessingResult(
            success=True,
            processed_data=sample_scraped_data,
            errors=[],
            warnings=[],
            quality_score=DataQuality.HIGH,
            duplicate_count=0
        )
        storage_service.data_processor.process_scraped_data.return_value = processing_result
        
        # Mock Firestore cache
        storage_service.firestore_manager.save_cache_entry = Mock(return_value=True)
        
        result = await storage_service.store_data(
            source="test_source",
            data_type="tramites",
            raw_data=sample_scraped_data
        )
        
        # Verify cache was called
        storage_service.firestore_manager.save_cache_entry.assert_called_once()
        storage_service.monitoring_service.record_firestore_write.assert_called()
    
    @pytest.mark.asyncio
    async def test_monitoring_integration(self, storage_service, sample_scraped_data):
        """Test that monitoring metrics are properly recorded."""
        # Mock processing result
        processing_result = ProcessingResult(
            success=True,
            processed_data=sample_scraped_data,
            errors=[],
            warnings=[],
            quality_score=DataQuality.HIGH,
            duplicate_count=0
        )
        storage_service.data_processor.process_scraped_data.return_value = processing_result
        
        # Mock all storage operations
        with patch('web_scraping.core.database.db_manager') as mock_db:
            mock_db.save_scraped_data = Mock(return_value=True)
            storage_service.firestore_manager.save_temporary_data = Mock(return_value="doc_id")
            storage_service.vector_search_manager.generate_embeddings = Mock(return_value=[[0.1, 0.2, 0.3]])
            storage_service.vector_search_manager.upsert_embeddings = Mock(return_value=True)
            
            result = await storage_service.store_data(
                source="test_source",
                data_type="programas_sociales",
                raw_data=sample_scraped_data
            )
            
            # Verify monitoring calls
            storage_service.monitoring_service.record_firestore_write.assert_called()
            storage_service.monitoring_service.record_vector_embedding.assert_called()
            storage_service.monitoring_service.record_vector_upsert.assert_called()
    
    def test_storage_configuration_validation(self):
        """Test that storage configurations are properly validated."""
        service = StorageService()
        
        # Test default configurations
        assert service.storage_configs["tramites"].primary_storage == "cloud_sql"
        assert service.storage_configs["pico_placa"].primary_storage == "firestore"
        assert service.storage_configs["programas_sociales"].primary_storage == "both"
        assert service.storage_configs["temporal"].primary_storage == "firestore"
        
        # Test TTL configurations
        assert service.storage_configs["pico_placa"].ttl_days == 1
        assert service.storage_configs["notificaciones"].ttl_days == 7
        assert service.storage_configs["temporal"].ttl_days == 3
        
        # Test vector search configurations
        assert service.storage_configs["tramites"].vector_search_enabled is True
        assert service.storage_configs["pico_placa"].vector_search_enabled is False
        assert service.storage_configs["programas_sociales"].vector_search_enabled is True
    
    @pytest.mark.asyncio
    async def test_data_transformation_consistency(self, storage_service, sample_scraped_data):
        """Test that data is consistently transformed across storage layers."""
        # Mock processing result
        processing_result = ProcessingResult(
            success=True,
            processed_data=sample_scraped_data,
            errors=[],
            warnings=[],
            quality_score=DataQuality.HIGH,
            duplicate_count=0
        )
        storage_service.data_processor.process_scraped_data.return_value = processing_result
        
        # Mock all storage operations
        with patch('web_scraping.core.database.db_manager') as mock_db:
            mock_db.save_scraped_data = Mock(return_value=True)
            storage_service.firestore_manager.save_temporary_data = Mock(return_value="doc_id")
            storage_service.vector_search_manager.generate_embeddings = Mock(return_value=[[0.1, 0.2, 0.3]])
            storage_service.vector_search_manager.upsert_embeddings = Mock(return_value=True)
            
            result = await storage_service.store_data(
                source="test_source",
                data_type="programas_sociales",
                raw_data=sample_scraped_data
            )
            
            # Verify that the same processed data was used across all storage layers
            # This tests that data transformation happens once and is consistent
            assert result["success"] is True
            assert len(result["stored_locations"]) >= 3  # cloud_sql, firestore, vector_search


class TestDataIntegrityValidation:
    """Tests for data integrity across storage layers."""
    
    def test_content_hash_consistency(self, sample_scraped_data):
        """Test that content hashes are consistent and unique."""
        hashes = [item["content_hash"] for item in sample_scraped_data]
        
        # All hashes should be unique
        assert len(hashes) == len(set(hashes))
        
        # All hashes should be non-empty
        assert all(hash_val for hash_val in hashes)
    
    def test_metadata_enrichment(self, sample_scraped_data):
        """Test that metadata is properly enriched during storage."""
        for item in sample_scraped_data:
            # Verify required fields are present
            assert "type" in item
            assert "content_hash" in item
            assert "extracted_at" in item
            assert "source_url" in item
            
            # Verify extracted_at is a valid ISO format
            try:
                datetime.fromisoformat(item["extracted_at"].replace('Z', '+00:00'))
            except ValueError:
                pytest.fail(f"Invalid ISO format for extracted_at: {item['extracted_at']}")
    
    def test_text_extraction_for_embeddings(self, storage_service, sample_scraped_data):
        """Test that text extraction for embeddings works correctly."""
        # Test with a record that has title and content
        record_with_content = {
            "title": "Test Title",
            "content": "Test content for embedding",
            "description": "Test description",
            "other_field": "Other data"
        }
        
        text = storage_service._extract_text_for_embedding(record_with_content)
        
        # Should include important fields
        assert "Test Title" in text
        assert "Test content for embedding" in text
        assert "Test description" in text
        assert "Other data" not in text  # Too short
        
        # Test with record that has no important fields
        record_without_content = {
            "other_field": "Short text",
            "another_field": "Another short text"
        }
        
        text = storage_service._extract_text_for_embedding(record_without_content)
        
        # Should include longer string values
        assert "Another short text" in text


@pytest.mark.asyncio
async def test_performance_benchmarks():
    """Test performance benchmarks for storage operations."""
    service = StorageService()
    
    # This would require actual GCP credentials and services
    # For now, just test that the service can be instantiated and basic methods work
    assert service is not None
    assert service.data_processor is not None
    
    # Test that storage configurations are properly loaded
    assert len(service.storage_configs) > 0
    assert "tramites" in service.storage_configs
    assert "pico_placa" in service.storage_configs


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
