"""
Test Data Processor
===================

Unit tests for the data processing and validation pipeline.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from web_scraping.services.data_processor import DataProcessor, DataQuality, ProcessingResult


class TestDataProcessor:
    """Test DataProcessor class."""
    
    @pytest.fixture
    def processor(self):
        """Create a data processor for testing."""
        return DataProcessor()
        
    def test_clean_data_basic(self, processor):
        """Test basic data cleaning."""
        raw_data = [
            {
                "type": "news",
                "title": "  Test News  ",
                "content": "  Test content  ",
                "empty_field": "",
                "null_field": None
            }
        ]
        
        cleaned_data = processor._clean_data(raw_data)
        
        assert len(cleaned_data) == 1
        assert cleaned_data[0]["title"] == "Test News"
        assert cleaned_data[0]["content"] == "Test content"
        assert "empty_field" not in cleaned_data[0]
        assert "null_field" not in cleaned_data[0]
        assert "extracted_at" in cleaned_data[0]
        
    def test_clean_data_missing_type(self, processor):
        """Test cleaning data with missing type field."""
        raw_data = [
            {
                "title": "Test News",
                "content": "Test content"
            }
        ]
        
        cleaned_data = processor._clean_data(raw_data)
        
        assert len(cleaned_data) == 1
        assert cleaned_data[0]["type"] == "unknown"
        
    def test_validate_data_structure_valid(self, processor):
        """Test validation of valid data structure."""
        data = [
            {
                "type": "news",
                "extracted_at": "2024-01-01T00:00:00",
                "title": "Test News",
                "content": "Test content"
            }
        ]
        
        validated_data, errors = processor._validate_data_structure(data)
        
        assert len(validated_data) == 1
        assert len(errors) == 0
        assert validated_data[0]["type"] == "news"
        
    def test_validate_data_structure_missing_required_fields(self, processor):
        """Test validation with missing required fields."""
        data = [
            {
                "title": "Test News",  # Missing 'type' and 'extracted_at'
                "content": "Test content"
            }
        ]
        
        validated_data, errors = processor._validate_data_structure(data)
        
        assert len(validated_data) == 0
        assert len(errors) == 2  # Two missing required fields
        
    def test_validate_data_structure_invalid_date(self, processor):
        """Test validation with invalid date format."""
        data = [
            {
                "type": "news",
                "extracted_at": "2024-01-01T00:00:00",
                "date": "invalid-date",
                "title": "Test News"
            }
        ]
        
        validated_data, errors = processor._validate_data_structure(data)
        
        assert len(validated_data) == 0
        assert len(errors) == 1
        assert "Invalid date format" in errors[0]
        
    def test_validate_data_structure_invalid_url(self, processor):
        """Test validation with invalid URL format."""
        data = [
            {
                "type": "news",
                "extracted_at": "2024-01-01T00:00:00",
                "url": "not-a-url",
                "title": "Test News"
            }
        ]
        
        validated_data, errors = processor._validate_data_structure(data)
        
        assert len(validated_data) == 0
        assert len(errors) == 1
        assert "Invalid URL format" in errors[0]
        
    def test_remove_duplicates_identical_records(self, processor):
        """Test removing identical duplicate records."""
        data = [
            {
                "type": "news",
                "title": "Test News",
                "content": "Test content"
            },
            {
                "type": "news",
                "title": "Test News",
                "content": "Test content"
            }
        ]
        
        unique_data, duplicate_count = processor._remove_duplicates(data)
        
        assert len(unique_data) == 1
        assert duplicate_count == 1
        assert "content_hash" in unique_data[0]
        
    def test_remove_duplicates_different_records(self, processor):
        """Test that different records are preserved."""
        data = [
            {
                "type": "news",
                "title": "Test News 1",
                "content": "Test content 1"
            },
            {
                "type": "news",
                "title": "Test News 2",
                "content": "Test content 2"
            }
        ]
        
        unique_data, duplicate_count = processor._remove_duplicates(data)
        
        assert len(unique_data) == 2
        assert duplicate_count == 0
        
    def test_normalize_data_formats(self, processor):
        """Test normalization of data formats."""
        data = [
            {
                "type": "news",
                "title": "  Test  News  ",
                "content": "  Test  content  ",
                "tags": ["", "tag1", None, "  tag2  "],
                "numbers": [1, 2, 3]
            }
        ]
        
        normalized_data = processor._normalize_data_formats(data)
        
        assert len(normalized_data) == 1
        assert normalized_data[0]["title"] == "Test News"
        assert normalized_data[0]["content"] == "Test content"
        assert normalized_data[0]["tags"] == ["tag1", "tag2"]
        assert normalized_data[0]["numbers"] == [1, 2, 3]
        
    def test_calculate_quality_score_high(self, processor):
        """Test calculation of high quality score."""
        data = [
            {
                "type": "news",
                "extracted_at": "2024-01-01T00:00:00",
                "title": "Test News",
                "content": "Test content"
            }
        ]
        errors = []
        
        quality_score = processor._calculate_quality_score(data, errors)
        
        assert quality_score == DataQuality.HIGH
        
    def test_calculate_quality_score_medium(self, processor):
        """Test calculation of medium quality score."""
        data = [
            {
                "type": "news",
                "extracted_at": "2024-01-01T00:00:00",
                "title": "Test News"
                # Missing 'content'
            }
        ]
        errors = ["Some validation error"]
        
        quality_score = processor._calculate_quality_score(data, errors)
        
        assert quality_score == DataQuality.MEDIUM
        
    def test_calculate_quality_score_low(self, processor):
        """Test calculation of low quality score."""
        data = [
            {
                "type": "news",
                "extracted_at": "2024-01-01T00:00:00"
                # Missing 'title' and 'content'
            }
        ]
        errors = ["Error 1", "Error 2", "Error 3"]
        
        quality_score = processor._calculate_quality_score(data, errors)
        
        assert quality_score == DataQuality.LOW
        
    def test_calculate_quality_score_invalid(self, processor):
        """Test calculation of invalid quality score."""
        data = []
        errors = ["Error 1", "Error 2"]
        
        quality_score = processor._calculate_quality_score(data, errors)
        
        assert quality_score == DataQuality.INVALID
        
    def test_generate_warnings_missing_important_fields(self, processor):
        """Test generation of warnings for missing important fields."""
        data = [
            {
                "type": "news",
                "extracted_at": "2024-01-01T00:00:00"
                # Missing title, content, description
            }
        ]
        
        warnings = processor._generate_warnings(data)
        
        assert len(warnings) == 1
        assert "Missing multiple important fields" in warnings[0]
        
    def test_generate_warnings_no_warnings(self, processor):
        """Test that no warnings are generated for complete data."""
        data = [
            {
                "type": "news",
                "extracted_at": "2024-01-01T00:00:00",
                "title": "Test News",
                "content": "Test content",
                "description": "Test description"
            }
        ]
        
        warnings = processor._generate_warnings(data)
        
        assert len(warnings) == 0
        
    @pytest.mark.asyncio
    async def test_process_scraped_data_success(self, processor):
        """Test successful processing of scraped data."""
        source = "test_source"
        data_type = "test_type"
        raw_data = [
            {
                "type": "news",
                "title": "Test News",
                "content": "Test content"
            }
        ]
        
        with patch.object(processor, '_save_to_database', return_value=True):
            result = await processor.process_scraped_data(source, data_type, raw_data)
            
        assert result.success is True
        assert len(result.processed_data) == 1
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert result.quality_score == DataQuality.HIGH
        assert result.duplicate_count == 0
        
    @pytest.mark.asyncio
    async def test_process_scraped_data_with_issues(self, processor):
        """Test processing data with various issues."""
        source = "test_source"
        data_type = "test_type"
        raw_data = [
            {
                "type": "news",
                "title": "Test News",
                "content": "Test content"
            },
            {
                "type": "news",
                "title": "Test News",  # Duplicate
                "content": "Test content"
            },
            {
                "title": "Missing type"  # Missing required field
            }
        ]
        
        with patch.object(processor, '_save_to_database', return_value=True):
            result = await processor.process_scraped_data(source, data_type, raw_data)
            
        assert result.success is True
        assert len(result.processed_data) == 1  # Only one unique, valid record
        assert len(result.errors) > 0  # Should have validation errors
        assert result.duplicate_count == 1
        assert result.quality_score in [DataQuality.HIGH, DataQuality.MEDIUM]
        
    @pytest.mark.asyncio
    async def test_process_scraped_data_save_failure(self, processor):
        """Test behavior when database save fails."""
        source = "test_source"
        data_type = "test_type"
        raw_data = [
            {
                "type": "news",
                "title": "Test News",
                "content": "Test content"
            }
        ]
        
        with patch.object(processor, '_save_to_database', return_value=False):
            result = await processor.process_scraped_data(source, data_type, raw_data)
            
        assert result.success is False
        assert len(result.processed_data) == 1  # Data was processed but not saved
        assert "Failed to save data to database" in result.errors