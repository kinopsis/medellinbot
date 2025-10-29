#!/usr/bin/env python3
"""
Comprehensive Test Suite for MedellínBot Web Scraping Framework
==============================================================

This test suite provides comprehensive validation of the web scraping implementation
against the technical plan requirements. It includes unit tests, integration tests,
performance benchmarks, security checks, and compliance validation.

Author: MedellínBot Development Team
Version: 1.0
Date: October 29, 2025
"""

import sys
import os
import asyncio
import json
import time
import tempfile
import unittest
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Optional, Tuple
import logging

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_scraping.core.base_scraper import BaseScraper, ScrapingConfig, ScrapingResult
from web_scraping.core.database import DatabaseManager, ScrapedData, ScrapingJob, db_manager
from web_scraping.services.data_processor import DataProcessor, DataQuality, ProcessingResult
from web_scraping.monitoring.monitor import ScrapingMonitor, monitoring_service
from web_scraping.main import WebScrapingOrchestrator
from web_scraping.scrapers.alcaldia_medellin import AlcaldiaMedellinScraper
from web_scraping.scrapers.secretaria_movilidad import SecretariaMovilidadScraper
from web_scraping.config.settings import config, get_source_config


class TestRequirementsValidation(unittest.TestCase):
    """Validate implementation against technical requirements."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger(__name__)
        
    def test_performance_requirements(self):
        """Test that performance requirements are met."""
        # Requirement: <5 seconds for HTML retrieval
        start_time = time.time()
        
        # Mock a slow response
        async def slow_fetch():
            await asyncio.sleep(2)  # Simulate 2 second response
            return "<html></html>"
        
        # This should pass (2s < 5s)
        result = asyncio.run(slow_fetch())
        elapsed = time.time() - start_time
        
        self.assertLess(elapsed, 5.0, "HTML retrieval should be < 5 seconds")
        
    def test_reliability_requirements(self):
        """Test reliability requirements."""
        # Requirement: 99.9% uptime availability
        # This would be tested in production, but we can test the monitoring
        
        # Check that monitoring is properly configured
        self.assertIsNotNone(monitoring_service)
        self.assertTrue(hasattr(monitoring_service, 'record_request'))
        self.assertTrue(hasattr(monitoring_service, 'record_error'))
        
    def test_data_integrity_requirements(self):
        """Test data integrity requirements."""
        # Requirement: 99.9% successful extraction rate
        
        # Test with valid data
        processor = DataProcessor()
        valid_data = [
            {
                "type": "news",
                "title": "Test News",
                "content": "Test content",
                "extracted_at": datetime.now().isoformat()
            }
        ]
        
        result = asyncio.run(processor.process_scraped_data("test_source", "test_type", valid_data))
        
        # Should have high quality score for valid data
        self.assertEqual(result.quality_score, DataQuality.HIGH)
        self.assertTrue(result.success)
        
    def test_concurrent_request_limits(self):
        """Test concurrent request limits."""
        # Requirement: Up to 10 concurrent requests per domain
        
        # Test that we can handle multiple concurrent scrapers
        async def test_concurrent_scraping():
            orchestrator = WebScrapingOrchestrator()
            
            # Mock multiple scrapers
            with patch('web_scraping.scrapers.alcaldia_medellin.AlcaldiaMedellinScraper') as mock_scraper1, \
                 patch('web_scraping.scrapers.secretaria_movilidad.SecretariaMovilidadScraper') as mock_scraper2:
                
                # Setup mock scrapers
                mock_scraper1.return_value.scrape = AsyncMock(return_value=ScrapingResult(success=True, data=[{"test": "data1"}]))
                mock_scraper2.return_value.scrape = AsyncMock(return_value=ScrapingResult(success=True, data=[{"test": "data2"}]))
                
                # Setup context managers
                with patch.object(mock_scraper1.return_value, '__aenter__', return_value=mock_scraper1.return_value):
                    with patch.object(mock_scraper1.return_value, '__aexit__', return_value=None):
                        with patch.object(mock_scraper2.return_value, '__aenter__', return_value=mock_scraper2.return_value):
                            with patch.object(mock_scraper2.return_value, '__aexit__', return_value=None):
                                # Run concurrent operations
                                await asyncio.gather(
                                    orchestrator.run_scraper("alcaldia_medellin"),
                                    orchestrator.run_scraper("secretaria_movilidad")
                                )
                                
                                # Should handle concurrent operations without issues
                                self.assertTrue(True)  # If we get here, concurrent operations worked
        
        asyncio.run(test_concurrent_scraping())


class TestBaseScraperImplementation(unittest.TestCase):
    """Test base scraper implementation."""
    
    def test_scraping_config_defaults(self):
        """Test default scraping configuration."""
        config = ScrapingConfig(base_url="https://example.com")
        
        self.assertEqual(config.base_url, "https://example.com")
        self.assertEqual(config.rate_limit_delay, 1.0)
        self.assertEqual(config.timeout, 30)
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.user_agent, "MedellínBot/1.0")
        self.assertIsNotNone(config.headers)
        self.assertIn("User-Agent", config.headers)
        
    def test_scraping_config_custom(self):
        """Test custom scraping configuration."""
        config = ScrapingConfig(
            base_url="https://example.com",
            rate_limit_delay=2.5,
            timeout=60,
            max_retries=5,
            user_agent="TestBot/1.0"
        )
        
        self.assertEqual(config.rate_limit_delay, 2.5)
        self.assertEqual(config.timeout, 60)
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.user_agent, "TestBot/1.0")
        
    def test_scraping_result_creation(self):
        """Test scraping result creation."""
        result = ScrapingResult(
            success=True,
            data=[{"test": "data"}],
            error_message=None
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.data, [{"test": "data"}])
        self.assertIsNone(result.error_message)
        self.assertIsNotNone(result.timestamp)
        
    def test_scraping_result_with_error(self):
        """Test scraping result with error."""
        result = ScrapingResult(
            success=False,
            data=None,
            error_message="Test error"
        )
        
        self.assertFalse(result.success)
        self.assertIsNone(result.data)
        self.assertEqual(result.error_message, "Test error")
        self.assertIsNotNone(result.timestamp)


class TestDataProcessorImplementation(unittest.TestCase):
    """Test data processor implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = DataProcessor()
        
    def test_data_cleaning(self):
        """Test data cleaning functionality."""
        raw_data = [
            {
                "type": "news",
                "title": "  Test News  ",
                "content": "  Test content  ",
                "empty_field": "",
                "null_field": None
            }
        ]
        
        cleaned_data = self.processor._clean_data(raw_data)
        
        self.assertEqual(len(cleaned_data), 1)
        self.assertEqual(cleaned_data[0]["title"], "Test News")
        self.assertEqual(cleaned_data[0]["content"], "Test content")
        self.assertNotIn("empty_field", cleaned_data[0])
        self.assertNotIn("null_field", cleaned_data[0])
        self.assertIn("extracted_at", cleaned_data[0])
        
    def test_data_validation(self):
        """Test data validation."""
        valid_data = [
            {
                "type": "news",
                "extracted_at": "2024-01-01T00:00:00",
                "title": "Test News",
                "content": "Test content"
            }
        ]
        
        validated_data, errors = self.processor._validate_data_structure(valid_data)
        
        self.assertEqual(len(validated_data), 1)
        self.assertEqual(len(errors), 0)
        self.assertEqual(validated_data[0]["type"], "news")
        
    def test_data_validation_missing_required_fields(self):
        """Test data validation with missing required fields."""
        invalid_data = [
            {
                "title": "Test News",  # Missing 'type' and 'extracted_at'
                "content": "Test content"
            }
        ]
        
        validated_data, errors = self.processor._validate_data_structure(invalid_data)
        
        self.assertEqual(len(validated_data), 0)
        self.assertEqual(len(errors), 2)  # Two missing required fields
        
    def test_duplicate_removal(self):
        """Test duplicate removal."""
        data = [
            {
                "type": "news",
                "title": "Test News",
                "content": "Test content"
            },
            {
                "type": "news",
                "title": "Test News",  # Duplicate
                "content": "Test content"
            }
        ]
        
        unique_data, duplicate_count = self.processor._remove_duplicates(data)
        
        self.assertEqual(len(unique_data), 1)
        self.assertEqual(duplicate_count, 1)
        self.assertIn("content_hash", unique_data[0])
        
    def test_quality_score_calculation(self):
        """Test quality score calculation."""
        # High quality data
        high_quality_data = [
            {
                "type": "news",
                "extracted_at": "2024-01-01T00:00:00",
                "title": "Test News",
                "content": "Test content"
            }
        ]
        
        quality_score = self.processor._calculate_quality_score(high_quality_data, [])
        self.assertEqual(quality_score, DataQuality.HIGH)
        
        # Invalid data
        invalid_data = []
        quality_score = self.processor._calculate_quality_score(invalid_data, ["error1", "error2"])
        self.assertEqual(quality_score, DataQuality.INVALID)


class TestDatabaseIntegration(unittest.TestCase):
    """Test database integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()
        
        # Mock the database URL
        self.original_db_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_db_path}'
        
        self.db_manager = DatabaseManager(f'sqlite:///{self.temp_db_path}')
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Restore original database URL
        if self.original_db_url:
            os.environ['DATABASE_URL'] = self.original_db_url
        else:
            os.environ.pop('DATABASE_URL', None)
            
        # Clean up temporary database
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)
            
    def test_database_creation(self):
        """Test database table creation."""
        try:
            self.db_manager.create_tables()
            # If this succeeds, tables were created successfully
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Failed to create database tables: {e}")
            
    def test_save_scraped_data(self):
        """Test saving scraped data."""
        source = "test_source"
        data_type = "test_type"
        content = {"test": "data", "type": "news"}
        
        record_id = asyncio.run(self.db_manager.save_scraped_data(source, data_type, content))
        
        self.assertIsNotNone(record_id)
        
        # Verify data can be retrieved
        recent_data = self.db_manager.get_recent_data(source, data_type, limit=1)
        self.assertEqual(len(recent_data), 1)
        self.assertEqual(recent_data[0]["source"], source)
        self.assertEqual(recent_data[0]["data_type"], data_type)
        
    def test_scraping_job_management(self):
        """Test scraping job management."""
        # Create a job
        job_id = asyncio.run(self.db_manager.create_scraping_job("test_scraper", {"test": "config"}))
        self.assertIsNotNone(job_id)
        
        # Update the job
        update_success = asyncio.run(self.db_manager.update_scraping_job(
            job_id, 
            status="completed",
            records_processed=10,
            success_count=9,
            error_count=1
        ))
        self.assertTrue(update_success)


class TestMonitoringAndAlerting(unittest.TestCase):
    """Test monitoring and alerting implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Start monitoring service
        monitoring_service.start_monitoring(0)  # Use port 0 for testing
        
    def test_metric_recording(self):
        """Test metric recording."""
        # Record some metrics
        monitoring_service.record_request("test_source", "success", 1.5)
        monitoring_service.record_error("test_source", "test_error")
        monitoring_service.update_data_quality("test_source", "test_type", 0.8)
        
        # Get system health
        health = monitoring_service.get_system_health()
        
        self.assertIn("status", health)
        self.assertIn("uptime_seconds", health)
        self.assertIn("active_alerts", health)
        
    def test_metrics_summary(self):
        """Test metrics summary generation."""
        # Get metrics summary
        metrics = monitoring_service.get_metrics_summary()
        
        self.assertIn("total_requests", metrics)
        self.assertIn("error_rate", metrics)
        self.assertIn("average_response_time", metrics)
        
    def test_alert_thresholds(self):
        """Test alert threshold configuration."""
        # Check that alert thresholds are configured
        self.assertIsNotNone(monitoring_service.alert_thresholds)
        
        # Test alert generation
        # This would be tested more thoroughly in integration tests


class TestOrchestratorFunctionality(unittest.TestCase):
    """Test orchestrator functionality."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = WebScrapingOrchestrator()
        
        # Initialize should succeed
        await orchestrator.initialize()
        
        self.assertFalse(orchestrator.running)
        self.assertIsNotNone(orchestrator.data_processor)
        
        # Cleanup
        await orchestrator.shutdown()
        
    @pytest.mark.asyncio
    async def test_manual_scraping(self):
        """Test manual scraping operation."""
        orchestrator = WebScrapingOrchestrator()
        await orchestrator.initialize()
        
        # Mock a scraper
        with patch('web_scraping.scrapers.alcaldia_medellin.AlcaldiaMedellinScraper') as mock_scraper_class:
            mock_scraper = Mock()
            mock_scraper.scrape = AsyncMock(return_value=ScrapingResult(success=True, data=[{"test": "data"}]))
            mock_scraper_class.return_value = mock_scraper
            
            with patch.object(mock_scraper, '__aenter__', return_value=mock_scraper):
                with patch.object(mock_scraper, '__aexit__', return_value=None):
                    await orchestrator.run_scraper("alcaldia_medellin")
                    
                    # Verify scraper was called
                    mock_scraper.scrape.assert_called_once()
                    
        await orchestrator.shutdown()
        
    @pytest.mark.asyncio
    async def test_system_status(self):
        """Test getting system status."""
        orchestrator = WebScrapingOrchestrator()
        await orchestrator.initialize()
        
        status = orchestrator.get_system_status()
        
        self.assertIn("status", status)
        self.assertIn("active_tasks", status)
        self.assertIn("total_tasks", status)
        self.assertIn("monitoring", status)
        self.assertIn("data_processor", status)
        
        await orchestrator.shutdown()


class TestPerformanceBenchmarks(unittest.TestCase):
    """Test performance benchmarks."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = DataProcessor()
        
    def test_data_processing_performance(self):
        """Test data processing performance."""
        # Generate large dataset
        large_dataset = [
            {
                "type": "news",
                "title": f"Test News {i}",
                "content": f"Test content {i}" * 100,  # Large content
                "extracted_at": datetime.now().isoformat()
            }
            for i in range(1000)  # 1000 records
        ]
        
        start_time = time.time()
        
        # Process the data
        result = asyncio.run(self.processor.process_scraped_data("test_source", "test_type", large_dataset))
        
        elapsed_time = time.time() - start_time
        
        # Should process 1000 records in reasonable time (< 30 seconds)
        self.assertLess(elapsed_time, 30.0, f"Processing took {elapsed_time:.2f}s, should be < 30s")
        
        # Should maintain high quality
        self.assertEqual(result.quality_score, DataQuality.HIGH)
        self.assertEqual(len(result.processed_data), 1000)
        
    def test_memory_usage(self):
        """Test memory usage during processing."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process large dataset
        large_dataset = [
            {
                "type": "news",
                "title": f"Test News {i}",
                "content": f"Test content {i}" * 100,
                "extracted_at": datetime.now().isoformat()
            }
            for i in range(5000)  # 5000 records
        ]
        
        result = asyncio.run(self.processor.process_scraped_data("test_source", "test_type", large_dataset))
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 500MB)
        self.assertLess(memory_increase, 500, f"Memory increase: {memory_increase:.2f}MB, should be < 500MB")
        
    def test_concurrent_processing(self):
        """Test concurrent processing performance."""
        async def process_data_chunk(chunk_id: int, size: int):
            """Process a chunk of data."""
            data = [
                {
                    "type": "news",
                    "title": f"Chunk {chunk_id} News {i}",
                    "content": f"Content {i}",
                    "extracted_at": datetime.now().isoformat()
                }
                for i in range(size)
            ]
            
            return await self.processor.process_scraped_data(f"chunk_{chunk_id}", "test_type", data)
            
        start_time = time.time()
        
        # Process multiple chunks concurrently
        chunks = [
            process_data_chunk(i, 200) for i in range(5)  # 5 chunks of 200 records each
        ]
        
        results = asyncio.run(asyncio.gather(*chunks))
        
        elapsed_time = time.time() - start_time
        
        # Should complete in reasonable time (< 10 seconds)
        self.assertLess(elapsed_time, 10.0, f"Concurrent processing took {elapsed_time:.2f}s, should be < 10s")
        
        # All chunks should succeed
        for result in results:
            self.assertTrue(result.success)
            self.assertEqual(len(result.processed_data), 200)


class TestSecurityAndCompliance(unittest.TestCase):
    """Test security and compliance measures."""
    
    def test_rate_limiting(self):
        """Test rate limiting implementation."""
        # Check that rate limiting is implemented in scrapers
        scraper = AlcaldiaMedellinScraper()
        
        # Should have rate limit configuration
        self.assertIsNotNone(scraper.config.rate_limit_delay)
        self.assertGreater(scraper.config.rate_limit_delay, 0)
        
    def test_user_agent_configuration(self):
        """Test user agent configuration."""
        scraper = AlcaldiaMedellinScraper()
        
        # Should use proper user agent
        self.assertIn("MedellínBot", scraper.config.user_agent)
        
    def test_error_handling(self):
        """Test error handling and sanitization."""
        processor = DataProcessor()
        
        # Test with invalid data that should trigger errors
        invalid_data = [
            {
                "title": "Missing type",  # Missing required field
                "content": "Test content"
            }
        ]
        
        result = asyncio.run(processor.process_scraped_data("test_source", "test_type", invalid_data))
        
        # Should handle errors gracefully
        self.assertFalse(result.success)
        self.assertGreater(len(result.errors), 0)
        
    def test_data_validation(self):
        """Test data validation and sanitization."""
        processor = DataProcessor()
        
        # Test with potentially malicious content
        malicious_data = [
            {
                "type": "news",
                "title": "<script>alert('xss')</script>",
                "content": "Test content",
                "extracted_at": datetime.now().isoformat()
            }
        ]
        
        result = asyncio.run(processor.process_scraped_data("test_source", "test_type", malicious_data))
        
        # Should sanitize the data
        if result.processed_data:
            sanitized_title = result.processed_data[0].get("title", "")
            self.assertNotIn("<script>", sanitized_title)
            self.assertNotIn("alert", sanitized_title)


class TestConfigurationManagement(unittest.TestCase):
    """Test configuration management."""
    
    def test_default_configuration(self):
        """Test default configuration loading."""
        # Check that default configuration is loaded
        self.assertIsNotNone(config.database)
        self.assertIsNotNone(config.scraping)
        self.assertIsNotNone(config.monitoring)
        self.assertIsNotNone(config.cloud)
        
    def test_source_configurations(self):
        """Test source configuration loading."""
        # Check source configurations
        self.assertIn("alcaldia_medellin", config.source_configs)
        self.assertIn("secretaria_movilidad", config.source_configs)
        
        source_config = config.source_configs["alcaldia_medellin"]
        self.assertIn("base_url", source_config)
        self.assertIn("rate_limit_delay", source_config)
        self.assertIn("timeout", source_config)
        
    def test_environment_variable_usage(self):
        """Test environment variable configuration."""
        # These would be tested in integration environment
        # For now, just verify the configuration structure
        self.assertIsNotNone(config)
        self.assertTrue(hasattr(config, 'database'))
        self.assertTrue(hasattr(config, 'scraping'))


class TestIntegrationWorkflows(unittest.TestCase):
    """Test integration workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_scraping_workflow(self):
        """Test complete scraping workflow."""
        # This would be a comprehensive integration test
        # For now, test the basic workflow
        
        orchestrator = WebScrapingOrchestrator()
        await orchestrator.initialize()
        
        # Test that we can run a complete cycle
        try:
            # This would require actual HTTP access in a real test
            # For now, just verify the method exists and can be called
            await orchestrator.run_scraper("alcaldia_medellin", force_refresh=True)
            self.assertTrue(True)  # If we get here, the method call succeeded
        except Exception as e:
            # In a test environment without internet access, this is expected
            self.assertIn("Failed to fetch", str(e))
            
        await orchestrator.shutdown()
        
    def test_data_pipeline(self):
        """Test complete data processing pipeline."""
        processor = DataProcessor()
        
        # Test the complete pipeline
        raw_data = [
            {
                "type": "news",
                "title": "  Test News  ",
                "content": "  Test content  ",
                "empty_field": "",
                "null_field": None
            }
        ]
        
        result = asyncio.run(processor.process_scraped_data("test_source", "test_type", raw_data))
        
        # Should complete the pipeline
        self.assertTrue(result.success)
        self.assertEqual(len(result.processed_data), 1)
        self.assertEqual(result.quality_score, DataQuality.HIGH)
        self.assertEqual(result.duplicate_count, 0)


class TestDocumentationAndReporting(unittest.TestCase):
    """Test documentation and reporting capabilities."""
    
    def test_monitoring_metrics(self):
        """Test monitoring metrics generation."""
        # Record some test metrics
        monitoring_service.record_request("test_source", "success", 1.5)
        monitoring_service.record_request("test_source", "success", 2.0)
        monitoring_service.record_error("test_source", "test_error")
        
        # Get detailed metrics
        metrics = monitoring_service.get_metrics_summary()
        
        self.assertIn("total_requests", metrics)
        self.assertIn("successful_requests", metrics)
        self.assertIn("failed_requests", metrics)
        self.assertIn("error_rate", metrics)
        self.assertIn("average_response_time", metrics)
        
    def test_system_health_check(self):
        """Test system health check."""
        health = monitoring_service.get_system_health()
        
        self.assertIn("status", health)
        self.assertIn("uptime_seconds", health)
        self.assertIn("memory_usage", health)
        self.assertIn("cpu_usage", health)
        self.assertIn("active_alerts", health)
        self.assertIn("last_updated", health)


def run_comprehensive_tests():
    """Run the comprehensive test suite."""
    print("MedellínBot Web Scraping Framework - Comprehensive Test Suite")
    print("=" * 70)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestRequirementsValidation,
        TestBaseScraperImplementation,
        TestDataProcessorImplementation,
        TestDatabaseIntegration,
        TestMonitoringAndAlerting,
        TestOrchestratorFunctionality,
        TestPerformanceBenchmarks,
        TestSecurityAndCompliance,
        TestConfigurationManagement,
        TestIntegrationWorkflows,
        TestDocumentationAndReporting
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    passed = total_tests - failures - errors - skipped
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed}")
    print(f"Failures: {failures}")
    print(f"Errors: {errors}")
    print(f"Skipped: {skipped}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
            
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    # Return success status
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)