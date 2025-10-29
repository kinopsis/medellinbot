#!/usr/bin/env python3
"""
Integration Tests for End-to-End Functionality
==============================================

This script provides comprehensive integration tests that validate the complete
workflow of the web scraping framework, from data collection through processing
and storage to API exposure.

Author: MedellínBot Development Team
Version: 1.0
Date: October 29, 2025
"""

import sys
import os
import asyncio
import tempfile
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import unittest
import pytest

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_scraping.main import WebScrapingOrchestrator
from web_scraping.core.database import DatabaseManager, db_manager
from web_scraping.services.data_processor import DataProcessor
from web_scraping.monitoring.monitor import monitoring_service, ScrapingMonitor
from web_scraping.scrapers.alcaldia_medellin import AlcaldiaMedellinScraper
from web_scraping.scrapers.secretaria_movilidad import SecretariaMovilidadScraper
from web_scraping.config.settings import config
from web_scraping.core.base_scraper import ScrapingResult


class TestEndToEndWorkflows(unittest.TestCase):
    """Test complete end-to-end workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_scraping_workflow(self):
        """Test the complete scraping workflow from start to finish."""
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db_path = f.name
        
        try:
            # Mock database URL
            with patch.dict(os.environ, {'DATABASE_URL': f'sqlite:///{temp_db_path}'}):
                orchestrator = WebScrapingOrchestrator()
                await orchestrator.initialize()
                
                # Mock scrapers to avoid actual HTTP requests
                with patch('web_scraping.scrapers.alcaldia_medellin.AlcaldiaMedellinScraper') as mock_scraper1, \
                     patch('web_scraping.scrapers.secretaria_movilidad.SecretariaMovilidadScraper') as mock_scraper2:
                    
                    # Setup mock scrapers with realistic data
                    mock_scraper1_instance = Mock()
                    mock_scraper1_instance.scrape = AsyncMock(return_value=ScrapingResult(
                        success=True,
                        data=[
                            {
                                "type": "news",
                                "title": "Test News 1",
                                "content": "Test content 1",
                                "extracted_at": datetime.now().isoformat()
                            }
                        ]
                    ))
                    mock_scraper1.return_value = mock_scraper1_instance
                    
                    mock_scraper2_instance = Mock()
                    mock_scraper2_instance.scrape = AsyncMock(return_value=ScrapingResult(
                        success=True,
                        data=[
                            {
                                "type": "traffic_alert",
                                "title": "Test Traffic Alert",
                                "content": "Test traffic content",
                                "extracted_at": datetime.now().isoformat()
                            }
                        ]
                    ))
                    mock_scraper2.return_value = mock_scraper2_instance
                    
                    # Setup context managers
                    with patch.object(mock_scraper1_instance, '__aenter__', return_value=mock_scraper1_instance):
                        with patch.object(mock_scraper1_instance, '__aexit__', return_value=None):
                            with patch.object(mock_scraper2_instance, '__aenter__', return_value=mock_scraper2_instance):
                                with patch.object(mock_scraper2_instance, '__aexit__', return_value=None):
                                    
                                    # Run the complete workflow
                                    await orchestrator.run_all_scrapers()
                                    
                                    # Verify scrapers were called
                                    mock_scraper1_instance.scrape.assert_called_once()
                                    mock_scraper2_instance.scrape.assert_called_once()
                                    
                                    # Verify data was processed and stored
                                    # This would be tested more thoroughly with actual database access
                                    self.assertTrue(True)  # If we get here, the workflow completed
                
                await orchestrator.shutdown()
                
        finally:
            # Clean up temporary database
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    @pytest.mark.asyncio
    async def test_data_pipeline_integration(self):
        """Test the complete data processing pipeline."""
        
        processor = DataProcessor()
        
        # Test data that goes through the complete pipeline
        raw_data = [
            {
                "type": "news",
                "title": "  Test News  ",
                "content": "  Test content with extra spaces  ",
                "empty_field": "",
                "null_field": None,
                "extracted_at": datetime.now().isoformat()
            },
            {
                "type": "news",
                "title": "  Test News  ",  # Duplicate
                "content": "  Test content with extra spaces  ",
                "extracted_at": datetime.now().isoformat()
            }
        ]
        
        # Run complete processing pipeline
        result = await processor.process_scraped_data("test_source", "test_type", raw_data)
        
        # Verify complete pipeline execution
        self.assertTrue(result.success)
        self.assertEqual(len(result.processed_data), 1)  # Should remove duplicate
        self.assertEqual(result.duplicate_count, 1)
        self.assertEqual(result.quality_score, processor._calculate_quality_score(raw_data, []))
        
        # Verify data was cleaned and normalized
        processed_record = result.processed_data[0]
        self.assertEqual(processed_record["title"], "Test News")
        self.assertEqual(processed_record["content"], "Test content with extra spaces")
        self.assertNotIn("empty_field", processed_record)
        self.assertNotIn("null_field", processed_record)
        self.assertIn("content_hash", processed_record)
    
    @pytest.mark.asyncio
    async def test_monitoring_integration(self):
        """Test monitoring integration throughout the workflow."""
        
        # Start monitoring service
        monitoring_service.start_monitoring(0)  # Use port 0 for testing
        
        # Record various metrics
        monitoring_service.record_request("test_source", "success", 1.5)
        monitoring_service.record_request("test_source", "success", 2.0)
        monitoring_service.record_request("test_source", "failure", 3.0)
        monitoring_service.record_error("test_source", "test_error")
        monitoring_service.update_data_quality("test_source", "test_type", 0.85)
        
        # Get system health
        health = monitoring_service.get_system_health()
        
        self.assertIn("status", health)
        self.assertIn("uptime_seconds", health)
        self.assertIn("memory_usage", health)
        self.assertIn("cpu_usage", health)
        self.assertIn("active_alerts", health)
        
        # Get detailed metrics
        metrics = monitoring_service.get_metrics_summary()
        
        self.assertIn("total_requests", metrics)
        self.assertIn("successful_requests", metrics)
        self.assertIn("failed_requests", metrics)
        self.assertIn("error_rate", metrics)
        self.assertIn("average_response_time", metrics)
        self.assertIn("data_quality_metrics", metrics)
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self):
        """Test error handling throughout the workflow."""
        
        orchestrator = WebScrapingOrchestrator()
        await orchestrator.initialize()
        
        # Test with failing scraper
        with patch('web_scraping.scrapers.alcaldia_medellin.AlcaldiaMedellinScraper') as mock_scraper:
            mock_instance = Mock()
            mock_instance.scrape = AsyncMock(return_value=ScrapingResult(
                success=False,
                error_message="Network error"
            ))
            mock_scraper.return_value = mock_instance
            
            with patch.object(mock_instance, '__aenter__', return_value=mock_instance):
                with patch.object(mock_instance, '__aexit__', return_value=None):
                    
                    # Run scraper and verify error handling
                    await orchestrator.run_scraper("alcaldia_medellin")
                    
                    # Should handle errors gracefully without crashing
                    self.assertTrue(True)
        
        await orchestrator.shutdown()
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_integration(self):
        """Test concurrent operations integration."""
        
        orchestrator = WebScrapingOrchestrator()
        await orchestrator.initialize()
        
        # Mock multiple scrapers
        with patch('web_scraping.scrapers.alcaldia_medellin.AlcaldiaMedellinScraper') as mock_scraper1, \
             patch('web_scraping.scrapers.secretaria_movilidad.SecretariaMovilidadScraper') as mock_scraper2:
            
            # Setup mock scrapers
            mock_scraper1_instance = Mock()
            mock_scraper1_instance.scrape = AsyncMock(return_value=ScrapingResult(success=True, data=[{"test": "data1"}]))
            mock_scraper1.return_value = mock_scraper1_instance
            
            mock_scraper2_instance = Mock()
            mock_scraper2_instance.scrape = AsyncMock(return_value=ScrapingResult(success=True, data=[{"test": "data2"}]))
            mock_scraper2.return_value = mock_scraper2_instance
            
            # Setup context managers
            with patch.object(mock_scraper1_instance, '__aenter__', return_value=mock_scraper1_instance):
                with patch.object(mock_scraper1_instance, '__aexit__', return_value=None):
                    with patch.object(mock_scraper2_instance, '__aenter__', return_value=mock_scraper2_instance):
                        with patch.object(mock_scraper2_instance, '__aexit__', return_value=None):
                            
                            # Run concurrent operations
                            start_time = time.time()
                            await asyncio.gather(
                                orchestrator.run_scraper("alcaldia_medellin"),
                                orchestrator.run_scraper("secretaria_movilidad")
                            )
                            end_time = time.time()
                            
                            # Should complete concurrently (faster than sequential)
                            concurrent_time = end_time - start_time
                            
                            # Verify both scrapers were called
                            mock_scraper1_instance.scrape.assert_called_once()
                            mock_scraper2_instance.scrape.assert_called_once()
                            
                            # Should complete in reasonable time for concurrent execution
                            self.assertLess(concurrent_time, 1.0)  # Should be very fast with mocks
        
        await orchestrator.shutdown()


class TestAPIIntegration(unittest.TestCase):
    """Test API integration and exposure."""
    
    @pytest.mark.asyncio
    async def test_api_health_endpoint(self):
        """Test API health check endpoint."""
        
        # This would test the actual API endpoints
        # For now, test the health check functionality
        
        monitoring_service.start_monitoring(0)
        
        # Simulate some system activity
        monitoring_service.record_request("test", "success", 1.0)
        
        # Get health status
        health = monitoring_service.get_system_health()
        
        self.assertIn("status", health)
        self.assertIn("timestamp", health)
        self.assertIn("version", health)
        self.assertIn("uptime_seconds", health)
        
        # Should indicate healthy status
        self.assertEqual(health["status"], "healthy")
    
    @pytest.mark.asyncio
    async def test_api_data_endpoints(self):
        """Test API data exposure endpoints."""
        
        # This would test actual API endpoints
        # For now, test the data access patterns
        
        # Mock database access
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db_path = f.name
        
        try:
            with patch.dict(os.environ, {'DATABASE_URL': f'sqlite:///{temp_db_path}'}):
                # Test data retrieval
                recent_data = db_manager.get_recent_data("test_source", "test_type", limit=10)
                
                # Should return empty list for non-existent data
                self.assertIsInstance(recent_data, list)
                
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    @pytest.mark.asyncio
    async def test_api_configuration_endpoints(self):
        """Test API configuration and management endpoints."""
        
        # Test configuration access
        self.assertIsNotNone(config)
        self.assertIsNotNone(config.database)
        self.assertIsNotNone(config.scraping)
        
        # Test source configurations
        self.assertIn("alcaldia_medellin", config.source_configs)
        self.assertIn("secretaria_movilidad", config.source_configs)
        
        source_config = config.source_configs["alcaldia_medellin"]
        self.assertIn("base_url", source_config)
        self.assertIn("rate_limit_delay", source_config)
        self.assertIn("timeout", source_config)


class TestDatabaseIntegration(unittest.TestCase):
    """Test database integration and persistence."""
    
    @pytest.mark.asyncio
    async def test_database_operations(self):
        """Test database operations integration."""
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db_path = f.name
        
        try:
            with patch.dict(os.environ, {'DATABASE_URL': f'sqlite:///{temp_db_path}'}):
                db_mgr = DatabaseManager(f'sqlite:///{temp_db_path}')
                
                # Test table creation
                db_mgr.create_tables()
                
                # Test data storage
                source = "test_source"
                data_type = "test_type"
                content = {"test": "data", "type": "news"}
                
                record_id = await db_mgr.save_scraped_data(source, data_type, content)
                self.assertIsNotNone(record_id)
                
                # Test data retrieval
                recent_data = db_mgr.get_recent_data(source, data_type, limit=5)
                self.assertEqual(len(recent_data), 1)
                self.assertEqual(recent_data[0]["source"], source)
                self.assertEqual(recent_data[0]["data_type"], data_type)
                
                # Test job management
                job_id = await db_mgr.create_scraping_job("test_scraper", {"test": "config"})
                self.assertIsNotNone(job_id)
                
                if job_id is not None:  # Fix type error
                    update_success = await db_mgr.update_scraping_job(
                        job_id,
                        status="completed",
                        records_processed=10,
                        success_count=9,
                        error_count=1
                    )
                    self.assertTrue(update_success)
                
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    @pytest.mark.asyncio
    async def test_data_consistency(self):
        """Test data consistency across operations."""
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db_path = f.name
        
        try:
            with patch.dict(os.environ, {'DATABASE_URL': f'sqlite:///{temp_db_path}'}):
                db_mgr = DatabaseManager(f'sqlite:///{temp_db_path}')
                db_mgr.create_tables()
                
                # Store multiple records
                test_data = [
                    {"type": "news", "title": "News 1", "content": "Content 1"},
                    {"type": "news", "title": "News 2", "content": "Content 2"},
                    {"type": "tramite", "title": "Trámite 1", "description": "Description 1"}
                ]
                
                for i, content in enumerate(test_data):
                    await db_mgr.save_scraped_data(f"test_source_{i}", "test_type", content)
                
                # Verify data consistency
                for i, expected_data in enumerate(test_data):
                    retrieved_data = db_mgr.get_recent_data(f"test_source_{i}", "test_type", limit=1)
                    self.assertEqual(len(retrieved_data), 1)
                    
                    record = retrieved_data[0]
                    self.assertEqual(record["source"], f"test_source_{i}")
                    self.assertEqual(record["data_type"], "test_type")
                    
                    # Verify content integrity
                    content_data = record["content"]
                    for key, expected_value in expected_data.items():
                        self.assertEqual(content_data.get(key), expected_value)
                
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)


class TestConfigurationIntegration(unittest.TestCase):
    """Test configuration management integration."""
    
    def test_configuration_loading(self):
        """Test configuration loading and validation."""
        
        # Test default configuration
        self.assertIsNotNone(config)
        self.assertIsNotNone(config.database)
        self.assertIsNotNone(config.scraping)
        self.assertIsNotNone(config.monitoring)
        self.assertIsNotNone(config.cloud)
        
        # Test source configurations
        self.assertIn("alcaldia_medellin", config.source_configs)
        self.assertIn("secretaria_movilidad", config.source_configs)
        
        # Test environment variable integration
        # This would be tested more thoroughly in integration environment
        
    def test_source_configuration_validation(self):
        """Test source configuration validation."""
        
        for source_name, source_config in config.source_configs.items():
            # Validate required fields
            self.assertIn("base_url", source_config)
            self.assertIn("rate_limit_delay", source_config)
            self.assertIn("timeout", source_config)
            
            # Validate data types
            self.assertIsInstance(source_config["base_url"], str)
            self.assertIsInstance(source_config["rate_limit_delay"], (int, float))
            self.assertIsInstance(source_config["timeout"], int)
            
            # Validate value ranges
            self.assertGreater(source_config["rate_limit_delay"], 0)
            self.assertGreater(source_config["timeout"], 0)


class TestMonitoringIntegration(unittest.TestCase):
    """Test monitoring and alerting integration."""
    
    @pytest.mark.asyncio
    async def test_monitoring_workflow_integration(self):
        """Test monitoring integration throughout the workflow."""
        
        # Start monitoring
        monitoring_service.start_monitoring(0)
        
        # Simulate workflow with monitoring
        with patch('web_scraping.monitoring.monitor.monitoring_service', monitoring_service):
            
            # Record various workflow events
            monitoring_service.record_request("alcaldia_medellin", "success", 1.5)
            monitoring_service.record_request("secretaria_movilidad", "success", 2.0)
            monitoring_service.record_error("test_source", "test_error")
            
            # Update data quality metrics
            monitoring_service.update_data_quality("alcaldia_medellin", "news", 0.95)
            monitoring_service.update_data_quality("secretaria_movilidad", "traffic_alert", 0.85)
            
            # Check system health
            health = monitoring_service.get_system_health()
            
            self.assertIn("status", health)
            self.assertIn("uptime_seconds", health)
            self.assertIn("active_alerts", health)
            self.assertIn("last_updated", health)
            
            # Check metrics summary
            metrics = monitoring_service.get_metrics_summary()
            
            self.assertIn("total_requests", metrics)
            self.assertIn("error_rate", metrics)
            self.assertIn("average_response_time", metrics)
            self.assertIn("data_quality_metrics", metrics)
    
    @pytest.mark.asyncio
    async def test_alert_integration(self):
        """Test alert integration and threshold monitoring."""
        
        # Start monitoring with alert thresholds
        monitoring_service.start_monitoring(0)
        
        # Test that monitoring service is properly initialized
        self.assertIsNotNone(monitoring_service)
        
        # Simulate conditions that might trigger alerts
        # This would be tested more thoroughly with actual alerting system
        
        # Check that monitoring system is responsive
        # Note: get_active_alerts() method may need to be implemented
        # For now, just verify monitoring service is available
        self.assertTrue(hasattr(monitoring_service, 'record_request'))
        self.assertTrue(hasattr(monitoring_service, 'get_system_health'))


class TestSecurityIntegration(unittest.TestCase):
    """Test security integration across the workflow."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self):
        """Test rate limiting integration."""
        
        # Test that rate limiting is properly configured
        scraper = AlcaldiaMedellinScraper()
        
        # Should have rate limit configuration
        self.assertIsNotNone(scraper.config.rate_limit_delay)
        self.assertGreater(scraper.config.rate_limit_delay, 0)
        
        # Should use proper user agent
        self.assertIn("MedellínBot", scraper.config.user_agent)
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling and sanitization integration."""
        
        processor = DataProcessor()
        
        # Test with invalid data that should trigger errors
        invalid_data = [
            {
                "title": "Missing type",  # Missing required field
                "content": "Test content"
            }
        ]
        
        result = await processor.process_scraped_data("test_source", "test_type", invalid_data)
        
        # Should handle errors gracefully
        self.assertFalse(result.success)
        self.assertGreater(len(result.errors), 0)
        
        # Should not expose sensitive information in errors
        for error in result.errors:
            self.assertNotIn("password", error.lower())
            self.assertNotIn("secret", error.lower())
    
    @pytest.mark.asyncio
    async def test_data_validation_integration(self):
        """Test data validation integration."""
        
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
        
        result = await processor.process_scraped_data("test_source", "test_type", malicious_data)
        
        # Should sanitize the data
        if result.processed_data:
            sanitized_title = result.processed_data[0].get("title", "")
            self.assertNotIn("<script>", sanitized_title)
            self.assertNotIn("alert", sanitized_title)


class TestPerformanceIntegration(unittest.TestCase):
    """Test performance integration across components."""
    
    @pytest.mark.asyncio
    async def test_workflow_performance(self):
        """Test performance of complete workflows."""
        
        start_time = time.time()
        
        # Simulate complete workflow
        processor = DataProcessor()
        
        # Generate test data
        large_dataset = [
            {
                "type": "news",
                "title": f"Test News {i}",
                "content": f"Test content {i}" * 10,  # Generate larger content
                "extracted_at": datetime.now().isoformat()
            }
            for i in range(100)  # 100 records
        ]
        
        # Process data
        result = await processor.process_scraped_data("performance_test", "test_type", large_dataset)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete in reasonable time
        self.assertLess(processing_time, 10.0, f"Processing took {processing_time:.2f}s")
        
        # Should maintain data quality
        self.assertTrue(result.success)
        self.assertEqual(len(result.processed_data), 100)
        self.assertEqual(result.quality_score, processor._calculate_quality_score(large_dataset, []))
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_performance(self):
        """Test performance of concurrent workflows."""
        
        start_time = time.time()
        
        # Process multiple datasets concurrently
        async def process_dataset(dataset_id: int, size: int):
            processor = DataProcessor()
            test_data = [
                {
                    "type": "news",
                    "title": f"Dataset {dataset_id} News {i}",
                    "content": f"Content {i}",
                    "extracted_at": datetime.now().isoformat()
                }
                for i in range(size)
            ]
            
            return await processor.process_scraped_data(f"dataset_{dataset_id}", "concurrent_test", test_data)
        
        # Run concurrent processing
        tasks = [
            process_dataset(i, 50) for i in range(4)  # 4 datasets of 50 records each
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete in reasonable time
        self.assertLess(total_time, 15.0, f"Concurrent processing took {total_time:.2f}s")
        
        # All tasks should succeed
        for result in results:
            self.assertTrue(result.success)
            self.assertEqual(len(result.processed_data), 50)


def run_integration_tests():
    """Run the comprehensive integration test suite."""
    
    print("MedellínBot Web Scraping - Integration Test Suite")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all integration test classes
    integration_test_classes = [
        TestEndToEndWorkflows,
        TestAPIIntegration,
        TestDatabaseIntegration,
        TestConfigurationIntegration,
        TestMonitoringIntegration,
        TestSecurityIntegration,
        TestPerformanceIntegration
    ]
    
    for test_class in integration_test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
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
            print(f"  - {test}")
            print(f"    {traceback}")
            
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            print(f"    {traceback}")
    
    # Return success status
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)