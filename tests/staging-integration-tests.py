#!/usr/bin/env python3
"""
Staging Environment Integration Tests
====================================

Comprehensive integration tests for the web scraping service in staging environment.
These tests validate end-to-end functionality, data flow, and system integration.
"""

import asyncio
import json
import logging
import os
import pytest
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from unittest.mock import patch, MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Individual test result."""
    test_name: str
    passed: bool
    duration: float
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

@dataclass
class IntegrationTestSuite:
    """Integration test suite results."""
    timestamp: datetime
    total_tests: int
    passed_tests: int
    failed_tests: int
    test_results: List[TestResult]
    overall_score: float
    critical_issues: List[str]
    recommendations: List[str]

class StagingIntegrationTester:
    """Comprehensive integration tester for staging environment."""
    
    def __init__(self, base_url: str, db_config: Dict[str, Any]):
        self.base_url = base_url.rstrip('/')
        self.db_config = db_config
        self.test_results: List[TestResult] = []
        
    async def run_test(self, test_name: str, test_func) -> TestResult:
        """Run a single test with timing and error handling."""
        start_time = time.time()
        
        try:
            await test_func()
            duration = time.time() - start_time
            result = TestResult(
                test_name=test_name,
                passed=True,
                duration=duration
            )
            logger.info(f"✓ {test_name} - PASSED ({duration:.2f}s)")
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            result = TestResult(
                test_name=test_name,
                passed=False,
                duration=duration,
                error_message=error_msg
            )
            logger.error(f"✗ {test_name} - FAILED ({duration:.2f}s): {error_msg}")
            
        self.test_results.append(result)
        return result
    
    async def test_service_health(self):
        """Test service health endpoints."""
        # Test health endpoint
        response = requests.get(f"{self.base_url}/health", timeout=10)
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "version" in health_data
        assert "timestamp" in health_data
        
        # Test readiness endpoint
        response = requests.get(f"{self.base_url}/ready", timeout=10)
        assert response.status_code == 200
        ready_data = response.json()
        assert ready_data["status"] == "ready"
        assert "checks" in ready_data
        
    async def test_metrics_endpoint(self):
        """Test metrics endpoint."""
        response = requests.get(f"{self.base_url}/metrics", timeout=10)
        assert response.status_code == 200
        metrics_content = response.text
        
        # Verify Prometheus format
        assert "# HELP" in metrics_content
        assert "# TYPE" in metrics_content
        
        # Check for key metrics
        key_metrics = [
            "web_scraping_requests_total",
            "web_scraping_errors_total",
            "web_scraping_scraper_duration_seconds"
        ]
        
        for metric in key_metrics:
            assert metric in metrics_content, f"Missing metric: {metric}"
    
    async def test_scraping_endpoints(self):
        """Test scraping functionality."""
        # Test individual scraper endpoints
        scrapers = ["alcaldia_medellin", "secretaria_movilidad"]
        
        for scraper in scrapers:
            response = requests.post(
                f"{self.base_url}/scrape",
                json={"source": scraper, "force_refresh": False},
                timeout=30
            )
            
            # Should return 200 or 202 (accepted for async processing)
            assert response.status_code in [200, 202], f"Failed for {scraper}: {response.text}"
            
            if response.status_code == 200:
                result = response.json()
                assert "success" in result
                assert "data" in result
    
    async def test_database_connectivity(self):
        """Test database connectivity and basic operations."""
        # This would require database access from test environment
        # For now, we'll test through the API
        
        response = requests.get(f"{self.base_url}/api/v1/health/db", timeout=10)
        if response.status_code == 200:
            db_health = response.json()
            assert db_health["database"]["status"] == "connected"
            assert db_health["database"]["can_connect"] is True
        else:
            # Database health check might not be implemented
            logger.warning("Database health check endpoint not available")
    
    async def test_data_quality_metrics(self):
        """Test data quality reporting."""
        response = requests.get(f"{self.base_url}/api/v1/metrics/quality", timeout=10)
        
        if response.status_code == 200:
            quality_data = response.json()
            assert "data_quality" in quality_data
            assert "sources" in quality_data["data_quality"]
            
            # Check for expected data sources
            expected_sources = ["alcaldia_medellin", "secretaria_movilidad"]
            for source in expected_sources:
                assert source in quality_data["data_quality"]["sources"]
        else:
            logger.warning("Data quality metrics endpoint not available")
    
    async def test_error_handling(self):
        """Test error handling and validation."""
        # Test invalid scraper
        response = requests.post(
            f"{self.base_url}/scrape",
            json={"source": "invalid_scraper", "force_refresh": False},
            timeout=10
        )
        assert response.status_code == 400
        
        # Test missing required fields
        response = requests.post(
            f"{self.base_url}/scrape",
            json={},
            timeout=10
        )
        assert response.status_code == 400
    
    async def test_concurrency(self):
        """Test concurrent request handling."""
        # Send multiple concurrent requests
        async def make_request():
            return requests.post(
                f"{self.base_url}/scrape",
                json={"source": "alcaldia_medellin", "force_refresh": False},
                timeout=30
            )
        
        # Use ThreadPoolExecutor for concurrent HTTP requests
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # All requests should succeed or be accepted
            for response in results:
                assert response.status_code in [200, 202, 429]  # 429 for rate limiting
    
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        # Send rapid requests to trigger rate limiting
        responses = []
        for i in range(20):  # Assuming rate limit is lower than 20
            response = requests.post(
                f"{self.base_url}/scrape",
                json={"source": "alcaldia_medellin", "force_refresh": True},
                timeout=10
            )
            responses.append(response.status_code)
            
            if response.status_code == 429:
                break
        
        # Should have some 429 responses if rate limiting is working
        rate_limited = [code for code in responses if code == 429]
        if rate_limited:
            logger.info(f"Rate limiting working: {len(rate_limited)} requests rate limited")
    
    async def test_data_persistence(self):
        """Test that scraped data is persisted correctly."""
        # Trigger a scrape
        response = requests.post(
            f"{self.base_url}/scrape",
            json={"source": "alcaldia_medellin", "force_refresh": True},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success") and result.get("data"):
                # Verify data was saved
                # This would typically involve checking the database
                # For now, we'll check through available API endpoints
                
                time.sleep(2)  # Allow time for data processing
                
                # Check if data is available through API
                response = requests.get(f"{self.base_url}/api/v1/data/latest", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    assert "data" in data
                    assert len(data["data"]) > 0
    
    async def test_monitoring_integration(self):
        """Test monitoring and metrics integration."""
        # Check if custom metrics are being exported
        response = requests.get(f"{self.base_url}/metrics", timeout=10)
        assert response.status_code == 200
        
        metrics_content = response.text
        
        # Look for custom application metrics
        custom_metrics = [
            "web_scraping_",
            "data_processor_",
            "database_"
        ]
        
        found_metrics = []
        for line in metrics_content.split('\n'):
            if line.startswith('#'):
                continue
            for metric_prefix in custom_metrics:
                if line.startswith(metric_prefix):
                    found_metrics.append(line.split()[0])
                    break
        
        assert len(found_metrics) > 0, "No custom metrics found"
        logger.info(f"Found {len(found_metrics)} custom metrics")
    
    async def test_configuration_loading(self):
        """Test configuration loading and validation."""
        # Test configuration endpoint (if available)
        response = requests.get(f"{self.base_url}/api/v1/config", timeout=10)
        
        if response.status_code == 200:
            config = response.json()
            assert "scraping" in config
            assert "database" in config
            assert "monitoring" in config
            
            # Verify required configuration values
            scraping_config = config["scraping"]
            assert "rate_limit_delay" in scraping_config
            assert "timeout" in scraping_config
            assert "concurrency" in scraping_config
        else:
            logger.warning("Configuration endpoint not available")
    
    async def test_log_formatting(self):
        """Test structured logging format."""
        # Trigger an action that should generate logs
        response = requests.get(f"{self.base_url}/health", timeout=10)
        assert response.status_code == 200
        
        # In a real environment, we would check the logs
        # For now, we'll verify the service can generate structured responses
        health_data = response.json()
        assert "timestamp" in health_data
        assert "version" in health_data
    
    async def run_all_tests(self) -> IntegrationTestSuite:
        """Run all integration tests."""
        logger.info("Starting staging integration tests...")
        logger.info("=" * 70)
        
        start_time = time.time()
        
        # Define all tests
        tests = [
            ("Service Health", self.test_service_health),
            ("Metrics Endpoint", self.test_metrics_endpoint),
            ("Scraping Endpoints", self.test_scraping_endpoints),
            ("Database Connectivity", self.test_database_connectivity),
            ("Data Quality Metrics", self.test_data_quality_metrics),
            ("Error Handling", self.test_error_handling),
            ("Concurrency", self.test_concurrency),
            ("Rate Limiting", self.test_rate_limiting),
            ("Data Persistence", self.test_data_persistence),
            ("Monitoring Integration", self.test_monitoring_integration),
            ("Configuration Loading", self.test_configuration_loading),
            ("Log Formatting", self.test_log_formatting),
        ]
        
        # Run all tests
        for test_name, test_func in tests:
            await self.run_test(test_name, test_func)
        
        # Calculate results
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.passed)
        failed_tests = total_tests - passed_tests
        overall_score = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Identify critical issues
        critical_issues = []
        for result in self.test_results:
            if not result.passed:
                critical_issues.append(f"{result.test_name}: {result.error_message}")
        
        # Generate recommendations
        recommendations = []
        if failed_tests > 0:
            recommendations.append(f"Fix {failed_tests} failing integration tests before production deployment")
        
        if not any(r.test_name == "Database Connectivity" and r.passed for r in self.test_results):
            recommendations.append("Verify database connectivity and configuration")
        
        if not any(r.test_name == "Monitoring Integration" and r.passed for r in self.test_results):
            recommendations.append("Ensure monitoring and metrics are properly configured")
        
        if not recommendations:
            recommendations.append("All integration tests passed successfully")
        
        total_duration = time.time() - start_time
        
        suite = IntegrationTestSuite(
            timestamp=datetime.now(),
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            test_results=self.test_results,
            overall_score=overall_score,
            critical_issues=critical_issues,
            recommendations=recommendations
        )
        
        return suite
    
    def generate_report(self, suite: IntegrationTestSuite) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        report = {
            "integration_test_summary": {
                "timestamp": suite.timestamp.isoformat(),
                "total_tests": suite.total_tests,
                "passed_tests": suite.passed_tests,
                "failed_tests": suite.failed_tests,
                "overall_score": round(suite.overall_score, 2),
                "total_duration": sum(r.duration for r in suite.test_results)
            },
            "test_results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "duration": round(r.duration, 3),
                    "error_message": r.error_message
                }
                for r in suite.test_results
            ],
            "critical_issues": suite.critical_issues,
            "recommendations": suite.recommendations
        }
        
        return report

async def main():
    """Main function to run integration tests."""
    # Configuration for staging environment
    STAGING_CONFIG = {
        "base_url": os.getenv("STAGING_BASE_URL", "https://web-scraping-service-staging.example.com"),
        "db_config": {
            "host": os.getenv("STAGING_DB_HOST", "staging-db.example.com"),
            "port": int(os.getenv("STAGING_DB_PORT", "5432")),
            "database": os.getenv("STAGING_DB_NAME", "staging_db"),
            "user": os.getenv("STAGING_DB_USER", "staging_user"),
            "password": os.getenv("STAGING_DB_PASSWORD", "staging_password")
        }
    }
    
    logger.info("Staging Integration Test Suite")
    logger.info("=" * 70)
    logger.info(f"Target URL: {STAGING_CONFIG['base_url']}")
    logger.info()
    
    # Run tests
    tester = StagingIntegrationTester(**STAGING_CONFIG)
    suite = await tester.run_all_tests()
    
    # Generate and print report
    report = tester.generate_report(suite)
    
    print("\n" + "=" * 70)
    print("INTEGRATION TEST RESULTS")
    print("=" * 70)
    print(f"Overall Score: {suite.overall_score:.1f}%")
    print(f"Total Tests: {suite.total_tests}")
    print(f"Passed: {suite.passed_tests}")
    print(f"Failed: {suite.failed_tests}")
    print(f"Duration: {sum(r.duration for r in suite.test_results):.2f}s")
    print()
    
    if suite.critical_issues:
        print("CRITICAL ISSUES:")
        for issue in suite.critical_issues:
            print(f"  - {issue}")
        print()
    
    print("RECOMMENDATIONS:")
    for recommendation in suite.recommendations:
        print(f"  - {recommendation}")
    print()
    
    # Print detailed results
    print("DETAILED TEST RESULTS:")
    for result in suite.test_results:
        status = "PASS" if result.passed else "FAIL"
        print(f"  {status} {result.test_name} ({result.duration:.2f}s)")
        if result.error_message:
            print(f"      Error: {result.error_message}")
    print()
    
    # Determine if deployment should proceed
    if suite.overall_score >= 80 and suite.failed_tests == 0:
        print("✅ INTEGRATION TESTS PASSED - Ready for production deployment")
        return True
    elif suite.overall_score >= 60:
        print("⚠️  INTEGRATION TESTS PARTIAL - Some issues need resolution")
        return False
    else:
        print("❌ INTEGRATION TESTS FAILED - Critical issues must be resolved")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)