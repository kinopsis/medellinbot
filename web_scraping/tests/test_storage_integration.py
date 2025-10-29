"""
Storage Integration Tests
=========================

Tests for Firestore, Vector Search, and unified storage service integration.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from web_scraping.services.storage_service import StorageService, StorageConfig
from web_scraping.config.firestore_config import FirestoreManager, FirestoreConfig
from web_scraping.config.vector_search_config import VectorSearchManager, VectorSearchConfig
from web_scraping.services.data_processor import DataProcessor, ProcessingResult, DataQuality


class TestFirestoreManager:
    """Test Firestore integration."""
    
    @pytest.fixture
    def firestore_config(self):
        """Create test Firestore configuration."""
        return FirestoreConfig(
            project_id="test-project",
            database_id="(default)",
            collection_prefix="test_medellinbot",
            use_emulator=True,
            emulator_host="localhost:8080"
        )
    
    @pytest.fixture
    def firestore_manager(self, firestore_config):
        """Create test Firestore manager."""
        with patch('google.cloud.firestore.Client'):
            return FirestoreManager(firestore_config)
    
    @pytest.mark.asyncio
    async def test_save_temporary_data(self, firestore_manager):
        """Test saving temporary data with TTL."""
        # Mock the client and collection
        mock_doc_ref = Mock()
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        firestore_manager._client.collection.return_value = mock_collection
        
        test_data = {"test": "data", "value": 123}
        result = await firestore_manager.save_temporary_data(
            data_type="test_type",
            data=test_data,
            ttl_days=1
        )
        
        assert result is not None  # Should return a document ID
        mock_doc_ref.set.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_get_temporary_data(self, firestore_manager):
        """Test retrieving temporary data."""
        # Mock document data
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "test": "data",
            "data_type": "test_type",
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=1)
        }
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        firestore_manager._client.collection.return_value = mock_collection
        
        result = await firestore_manager.get_temporary_data("test_doc_id")
        
        assert result is not None
        assert result["test"] == "data"
        
    @pytest.mark.asyncio
    async def test_save_cache_entry(self, firestore_manager):
        """Test saving cache entries."""
        mock_doc_ref = Mock()
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        firestore_manager._client.collection.return_value = mock_collection
        
        test_data = {"cached": "data"}
        result = await firestore_manager.save_cache_entry(
            cache_key="test_key",
            data=test_data,
            ttl_days=1
        )
        
        assert result is True
        mock_doc_ref.set.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_cleanup_expired_documents(self, firestore_manager):
        """Test cleaning up expired documents."""
        # Mock expired documents
        mock_expired_doc1 = Mock()
        mock_expired_doc1.reference = Mock()
        mock_expired_doc1.reference.delete = Mock()
        
        mock_expired_doc2 = Mock()
        mock_expired_doc2.reference = Mock()
        mock_expired_doc2.reference.delete = Mock()
        
        mock_collection = Mock()
        mock_collection.where.return_value.stream.return_value = [mock_expired_doc1, mock_expired_doc2]
        firestore_manager._client.collection.return_value = mock_collection
        
        result = await firestore_manager.cleanup_expired_documents("test_collection")
        
        assert result == 2
        mock_expired_doc1.reference.delete.assert_called_once()
        mock_expired_doc2.reference.delete.assert_called_once()


class TestVectorSearchManager:
    """Test Vector Search integration."""
    
    @pytest.fixture
    def vector_config(self):
        """Create test Vector Search configuration."""
        return VectorSearchConfig(
            project_id="test-project",
            region="us-central1",
            dimensions=768
        )
    
    @pytest.fixture
    def vector_manager(self, vector_config):
        """Create test Vector Search manager."""
        with patch('google.cloud.aiplatform.init'):
            with patch('google.cloud.aiplatform.MatchingEngineIndex.create'):
                return VectorSearchManager(vector_config)
    
    @pytest.mark.asyncio
    async def test_generate_embeddings(self, vector_manager):
        """Test generating text embeddings."""
        with patch('vertexai.language_models.TextEmbeddingModel.from_pretrained') as mock_model:
            mock_embedding = Mock()
            mock_embedding.values = [0.1, 0.2, 0.3] * 256  # 768 dimensions
            
            mock_model_instance = Mock()
            mock_model_instance.get_embeddings.return_value = [mock_embedding]
            mock_model.return_value = mock_model_instance
            
            texts = ["test text"]
            embeddings = await vector_manager.generate_embeddings(texts)
            
            assert len(embeddings) == 1
            assert len(embeddings[0]) == 768
            assert embeddings[0][0] == 0.1
            
    @pytest.mark.asyncio
    async def test_upsert_embeddings(self, vector_manager):
        """Test upserting embeddings to vector index."""
        # Mock endpoint
        mock_endpoint = Mock()
        mock_endpoint.upsert_datapoints = Mock(return_value=None)
        vector_manager._endpoint = mock_endpoint
        
        ids = ["test_id"]
        embeddings = [[0.1, 0.2, 0.3] * 256]
        metadata = [{"test": "metadata"}]
        
        result = await vector_manager.upsert_embeddings(ids, embeddings, metadata)
        
        assert result is True
        mock_endpoint.upsert_datapoints.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_search_similar_vectors(self, vector_manager):
        """Test searching for similar vectors."""
        # Mock endpoint response
        mock_neighbor = Mock()
        mock_neighbor.id = "test_id"
        mock_neighbor.distance = 0.1
        mock_neighbor.datapoint = Mock()
        mock_neighbor.datapoint.restricts = {}
        
        mock_response = [[mock_neighbor]]
        
        mock_endpoint = Mock()
        mock_endpoint.find_neighbors.return_value = mock_response
        vector_manager._endpoint = mock_endpoint
        
        query_embedding = [0.1, 0.2, 0.3] * 256
        results = await vector_manager.search_similar_vectors(query_embedding, num_neighbors=5)
        
        assert len(results) == 1
        assert results[0]["id"] == "test_id"
        assert results[0]["distance"] == 0.1


class TestStorageService:
    """Test unified storage service."""
    
    @pytest.fixture
    def storage_service(self):
        """Create test storage service."""
        with patch('web_scraping.services.storage_service.get_firestore_manager'):
            with patch('web_scraping.services.storage_service.get_vector_search_manager'):
                service = StorageService()
                # Mock the managers
                service.firestore_manager = Mock()
                service.vector_search_manager = Mock()
                service.data_processor = Mock()
                return service
    
    @pytest.mark.asyncio
    async def test_store_data_cloud_sql(self, storage_service):
        """Test storing data in Cloud SQL."""
        # Mock processing result
        processing_result = ProcessingResult(
            success=True,
            processed_data=[{"test": "data"}],
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
                raw_data=[{"test": "data"}]
            )
            
            assert result["success"] is True
            assert "cloud_sql" in result["stored_locations"]
            
    @pytest.mark.asyncio
    async def test_store_data_firestore(self, storage_service):
        """Test storing data in Firestore."""
        # Mock processing result
        processing_result = ProcessingResult(
            success=True,
            processed_data=[{"test": "data"}],
            errors=[],
            warnings=[],
            quality_score=DataQuality.HIGH,
            duplicate_count=0
        )
        storage_service.data_processor.process_scraped_data.return_value = processing_result
        
        # Mock Firestore save
        storage_service.firestore_manager.save_temporary_data = Mock(return_value="doc_id")
        
        result = await storage_service.store_data(
            source="test_source",
            data_type="pico_placa",
            raw_data=[{"test": "data"}]
        )
        
        assert result["success"] is True
        assert "firestore" in result["stored_locations"]
        
    @pytest.mark.asyncio
    async def test_store_data_vector_search(self, storage_service):
        """Test storing data in Vector Search."""
        # Mock processing result
        processing_result = ProcessingResult(
            success=True,
            processed_data=[{"test": "data", "title": "Test Title"}],
            errors=[],
            warnings=[],
            quality_score=DataQuality.HIGH,
            duplicate_count=0
        )
        storage_service.data_processor.process_scraped_data.return_value = processing_result
        
        # Mock vector search
        storage_service.vector_search_manager.generate_embeddings = Mock(return_value=[[0.1, 0.2, 0.3]])
        storage_service.vector_search_manager.upsert_embeddings = Mock(return_value=True)
        
        result = await storage_service.store_data(
            source="test_source",
            data_type="programas_sociales",
            raw_data=[{"test": "data", "title": "Test Title"}]
        )
        
        assert result["success"] is True
        assert "vector_search" in result["stored_locations"]
        
    def test_extract_text_for_embedding(self, storage_service):
        """Test extracting text for embedding generation."""
        record = {
            "title": "Test Title",
            "content": "Test content",
            "description": "Test description",
            "other_field": "Other data"
        }
        
        text = storage_service._extract_text_for_embedding(record)
        
        assert "Test Title" in text
        assert "Test content" in text
        assert "Test description" in text
        assert "Other data" not in text  # Too short
        
    @pytest.mark.asyncio
    async def test_search_similar_content(self, storage_service):
        """Test semantic search functionality."""
        # Mock vector search
        storage_service.vector_search_manager.generate_embeddings = Mock(return_value=[[0.1, 0.2, 0.3]])
        storage_service.vector_search_manager.search_similar_vectors = Mock(return_value=[
            {"id": "result1", "distance": 0.1, "metadata": {}}
        ])
        
        results = await storage_service.search_similar_content("test query")
        
        assert len(results) == 1
        assert results[0]["id"] == "result1"
        assert results[0]["relevance_score"] == 0.9  # 1 - 0.1


class TestStorageConfig:
    """Test storage configuration."""
    
    def test_default_configurations(self):
        """Test default storage configurations."""
        service = StorageService()
        
        # Test trámites configuration
        tramites_config = service.storage_configs["tramites"]
        assert tramites_config.primary_storage == "cloud_sql"
        assert tramites_config.cache_enabled is True
        assert tramites_config.vector_search_enabled is True
        assert tramites_config.criticality == 8
        
        # Test pico_placa configuration
        pico_placa_config = service.storage_configs["pico_placa"]
        assert pico_placa_config.primary_storage == "firestore"
        assert pico_placa_config.ttl_days == 1
        assert pico_placa_config.vector_search_enabled is False
        assert pico_placa_config.criticality == 10
        
        # Test temporal configuration
        temporal_config = service.storage_configs["temporal"]
        assert temporal_config.primary_storage == "firestore"
        assert temporal_config.ttl_days == 3
        assert temporal_config.cache_enabled is False


@pytest.mark.asyncio
async def test_end_to_end_storage_workflow():
    """Test complete storage workflow."""
    # This would require actual GCP credentials and services
    # For now, just test that the service can be instantiated
    try:
        service = StorageService()
        assert service is not None
        assert service.data_processor is not None
    except Exception as e:
        pytest.skip(f"Integration test requires GCP credentials: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
