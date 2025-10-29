#!/usr/bin/env python3
"""
Post-Deployment Validation Tests for MedellínBot
This script validates that all components are working correctly after production deployment.
"""

import requests
import time
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PostDeploymentValidator:
    def __init__(self, project_id: str = "medellinbot-prd-440915"):
        self.project_id = project_id
        self.base_urls = {
            'webhook': f'https://medellinbot-webhook-{self.project_id}.a.run.app',
            'orchestrator': f'https://medellinbot-orchestrator-{self.project_id}.a.run.app',
            'tramites': f'https://medellinbot-tramites-{self.project_id}.a.run.app',
            'pqrsd': f'https://medellinbot-pqrsd-{self.project_id}.a.run.app',
            'programas': f'https://medellinbot-programas-{self.project_id}.a.run.app',
            'notificaciones': f'https://medellinbot-notificaciones-{self.project_id}.a.run.app'
        }
        self.results = {}
        self.failures = []

    def validate_service_health(self) -> bool:
        """Validate that all services are responding to health checks."""
        logger.info("Validating service health...")
        health_results = {}
        
        for service, url in self.base_urls.items():
            try:
                # Test health endpoint
                health_url = f"{url}/health"
                response = requests.get(health_url, timeout=10)
                
                if response.status_code == 200:
                    health_results[service] = True
                    logger.info(f"✓ {service} health check passed")
                else:
                    health_results[service] = False
                    self.failures.append(f"{service} health check failed with status {response.status_code}")
                    logger.error(f"✗ {service} health check failed with status {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                health_results[service] = False
                self.failures.append(f"{service} health check failed: {str(e)}")
                logger.error(f"✗ {service} health check failed: {str(e)}")
        
        self.results['health_checks'] = health_results
        return all(health_results.values())

    def validate_service_readiness(self) -> bool:
        """Validate that all services are ready to accept traffic."""
        logger.info("Validating service readiness...")
        readiness_results = {}
        
        for service, url in self.base_urls.items():
            try:
                # Test readiness endpoint
                readiness_url = f"{url}/ready"
                response = requests.get(readiness_url, timeout=10)
                
                if response.status_code == 200:
                    readiness_results[service] = True
                    logger.info(f"✓ {service} readiness check passed")
                else:
                    readiness_results[service] = False
                    self.failures.append(f"{service} readiness check failed with status {response.status_code}")
                    logger.error(f"✗ {service} readiness check failed with status {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                readiness_results[service] = False
                self.failures.append(f"{service} readiness check failed: {str(e)}")
                logger.error(f"✗ {service} readiness check failed: {str(e)}")
        
        self.results['readiness_checks'] = readiness_results
        return all(readiness_results.values())

    def validate_webhook_functionality(self) -> bool:
        """Validate webhook functionality with a test message."""
        logger.info("Validating webhook functionality...")
        
        try:
            webhook_url = self.base_urls['webhook']
            
            # Test with a sample Telegram message
            test_message = {
                "update_id": 123456789,
                "message": {
                    "message_id": 1,
                    "from": {
                        "id": 123456789,
                        "is_bot": False,
                        "first_name": "Test",
                        "username": "testuser",
                        "language_code": "en"
                    },
                    "chat": {
                        "id": 123456789,
                        "first_name": "Test",
                        "username": "testuser",
                        "type": "private"
                    },
                    "date": int(time.time()),
                    "text": "/start"
                }
            }
            
            response = requests.post(
                f"{webhook_url}/webhook",
                json=test_message,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info("✓ Webhook functionality test passed")
                self.results['webhook_functionality'] = True
                return True
            else:
                self.failures.append(f"Webhook functionality test failed with status {response.status_code}")
                logger.error(f"✗ Webhook functionality test failed with status {response.status_code}")
                self.results['webhook_functionality'] = False
                return False
                
        except requests.exceptions.RequestException as e:
            self.failures.append(f"Webhook functionality test failed: {str(e)}")
            logger.error(f"✗ Webhook functionality test failed: {str(e)}")
            self.results['webhook_functionality'] = False
            return False

    def validate_orchestrator_routing(self) -> bool:
        """Validate orchestrator can route requests to agents."""
        logger.info("Validating orchestrator routing...")
        
        try:
            orchestrator_url = self.base_urls['orchestrator']
            
            # Test intent classification
            test_request = {
                "user_id": "test_user_123",
                "message": "Quiero hacer un trámite de registro civil",
                "session_id": "test_session_123"
            }
            
            response = requests.post(
                f"{orchestrator_url}/api/v1/classify",
                json=test_request,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if 'intent' in result and 'confidence' in result:
                        logger.info("✓ Orchestrator routing test passed")
                        self.results['orchestrator_routing'] = True
                        return True
                    else:
                        self.failures.append("Orchestrator routing test failed: Invalid response format")
                        logger.error("✗ Orchestrator routing test failed: Invalid response format")
                        self.results['orchestrator_routing'] = False
                        return False
                except json.JSONDecodeError:
                    self.failures.append("Orchestrator routing test failed: Invalid JSON response")
                    logger.error("✗ Orchestrator routing test failed: Invalid JSON response")
                    self.results['orchestrator_routing'] = False
                    return False
            else:
                self.failures.append(f"Orchestrator routing test failed with status {response.status_code}")
                logger.error(f"✗ Orchestrator routing test failed with status {response.status_code}")
                self.results['orchestrator_routing'] = False
                return False
                
        except requests.exceptions.RequestException as e:
            self.failures.append(f"Orchestrator routing test failed: {str(e)}")
            logger.error(f"✗ Orchestrator routing test failed: {str(e)}")
            self.results['orchestrator_routing'] = False
            return False

    def validate_agent_responses(self) -> bool:
        """Validate that specialized agents can respond to requests."""
        logger.info("Validating agent responses...")
        
        agents = ['tramites', 'pqrsd', 'programas', 'notificaciones']
        agent_results = {}
        
        for agent in agents:
            try:
                agent_url = self.base_urls[agent]
                
                # Test agent with a simple request
                test_request = {
                    "user_id": "test_user_123",
                    "message": "Hola",
                    "session_id": "test_session_123",
                    "context": {}
                }
                
                response = requests.post(
                    f"{agent_url}/api/v1/respond",
                    json=test_request,
                    timeout=30,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        if 'response' in result:
                            agent_results[agent] = True
                            logger.info(f"✓ {agent} agent response test passed")
                        else:
                            agent_results[agent] = False
                            self.failures.append(f"{agent} agent response test failed: Invalid response format")
                            logger.error(f"✗ {agent} agent response test failed: Invalid response format")
                    except json.JSONDecodeError:
                        agent_results[agent] = False
                        self.failures.append(f"{agent} agent response test failed: Invalid JSON response")
                        logger.error(f"✗ {agent} agent response test failed: Invalid JSON response")
                else:
                    agent_results[agent] = False
                    self.failures.append(f"{agent} agent response test failed with status {response.status_code}")
                    logger.error(f"✗ {agent} agent response test failed with status {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                agent_results[agent] = False
                self.failures.append(f"{agent} agent response test failed: {str(e)}")
                logger.error(f"✗ {agent} agent response test failed: {str(e)}")
        
        self.results['agent_responses'] = agent_results
        return all(agent_results.values())

    def validate_database_connectivity(self) -> bool:
        """Validate database connectivity through orchestrator."""
        logger.info("Validating database connectivity...")
        
        try:
            orchestrator_url = self.base_urls['orchestrator']
            
            # Test database connectivity
            response = requests.get(
                f"{orchestrator_url}/api/v1/health/db",
                timeout=15
            )
            
            if response.status_code == 200:
                logger.info("✓ Database connectivity test passed")
                self.results['database_connectivity'] = True
                return True
            else:
                self.failures.append(f"Database connectivity test failed with status {response.status_code}")
                logger.error(f"✗ Database connectivity test failed with status {response.status_code}")
                self.results['database_connectivity'] = False
                return False
                
        except requests.exceptions.RequestException as e:
            self.failures.append(f"Database connectivity test failed: {str(e)}")
            logger.error(f"✗ Database connectivity test failed: {str(e)}")
            self.results['database_connectivity'] = False
            return False

    def validate_authentication(self) -> bool:
        """Validate authentication and authorization mechanisms."""
        logger.info("Validating authentication...")
        
        auth_results = {}
        
        # Test services that require authentication
        protected_endpoints = [
            (self.base_urls['webhook'], '/api/v1/admin/status'),
            (self.base_urls['orchestrator'], '/api/v1/admin/metrics')
        ]
        
        for url, endpoint in protected_endpoints:
            try:
                # Test without authentication (should fail)
                response = requests.get(f"{url}{endpoint}", timeout=10)
                
                if response.status_code == 401 or response.status_code == 403:
                    auth_results[endpoint] = True
                    logger.info(f"✓ {endpoint} authentication test passed")
                else:
                    auth_results[endpoint] = False
                    self.failures.append(f"{endpoint} authentication test failed: Expected 401/403, got {response.status_code}")
                    logger.error(f"✗ {endpoint} authentication test failed: Expected 401/403, got {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                auth_results[endpoint] = False
                self.failures.append(f"{endpoint} authentication test failed: {str(e)}")
                logger.error(f"✗ {endpoint} authentication test failed: {str(e)}")
        
        self.results['authentication'] = auth_results
        return all(auth_results.values())

    def validate_response_times(self) -> bool:
        """Validate that response times are within acceptable limits."""
        logger.info("Validating response times...")
        
        response_time_results = {}
        max_response_time = 5.0  # seconds
        
        for service, url in self.base_urls.items():
            try:
                start_time = time.time()
                response = requests.get(f"{url}/health", timeout=10)
                end_time = time.time()
                
                response_time = end_time - start_time
                
                if response.status_code == 200 and response_time <= max_response_time:
                    response_time_results[service] = True
                    logger.info(f"✓ {service} response time test passed ({response_time:.2f}s)")
                else:
                    response_time_results[service] = False
                    self.failures.append(f"{service} response time test failed: {response_time:.2f}s (max: {max_response_time}s)")
                    logger.error(f"✗ {service} response time test failed: {response_time:.2f}s (max: {max_response_time}s)")
                    
            except requests.exceptions.RequestException as e:
                response_time_results[service] = False
                self.failures.append(f"{service} response time test failed: {str(e)}")
                logger.error(f"✗ {service} response time test failed: {str(e)}")
        
        self.results['response_times'] = response_time_results
        return all(response_time_results.values())

    def validate_ssl_certificates(self) -> bool:
        """Validate SSL certificates are valid and not expired."""
        logger.info("Validating SSL certificates...")
        
        import ssl
        import socket
        from datetime import datetime
        
        ssl_results = {}
        
        for service, url in self.base_urls.items():
            try:
                # Extract hostname from URL
                hostname = url.replace('https://', '').split('/')[0]
                
                # Get SSL certificate
                context = ssl.create_default_context()
                with socket.create_connection((hostname, 443), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                        cert = ssock.getpeercert()
                        
                        # Check expiration
                        if cert and 'notAfter' in cert:
                            expiry_str = cert['notAfter']
                            if isinstance(expiry_str, str):
                                expiry_date = datetime.strptime(expiry_str, '%b %d %H:%M:%S %Y %Z')
                                days_until_expiry = (expiry_date - datetime.now()).days
                            else:
                                days_until_expiry = 0
                        else:
                            days_until_expiry = 0
                        
                        if days_until_expiry > 30:  # Certificate expires in more than 30 days
                            ssl_results[service] = True
                            logger.info(f"✓ {service} SSL certificate valid ({days_until_expiry} days until expiry)")
                        else:
                            ssl_results[service] = False
                            self.failures.append(f"{service} SSL certificate expires soon ({days_until_expiry} days)")
                            logger.error(f"✗ {service} SSL certificate expires soon ({days_until_expiry} days)")
                            
            except Exception as e:
                ssl_results[service] = False
                self.failures.append(f"{service} SSL certificate validation failed: {str(e)}")
                logger.error(f"✗ {service} SSL certificate validation failed: {str(e)}")
        
        self.results['ssl_certificates'] = ssl_results
        return all(ssl_results.values())

    def run_all_tests(self) -> Dict:
        """Run all validation tests and return comprehensive results."""
        logger.info("Starting comprehensive post-deployment validation...")
        
        # Run all validation tests
        tests = [
            ("Service Health", self.validate_service_health),
            ("Service Readiness", self.validate_service_readiness),
            ("Webhook Functionality", self.validate_webhook_functionality),
            ("Orchestrator Routing", self.validate_orchestrator_routing),
            ("Agent Responses", self.validate_agent_responses),
            ("Database Connectivity", self.validate_database_connectivity),
            ("Authentication", self.validate_authentication),
            ("Response Times", self.validate_response_times),
            ("SSL Certificates", self.validate_ssl_certificates)
        ]
        
        test_results = {}
        overall_success = True
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'='*50}")
            
            try:
                result = test_func()
                test_results[test_name] = result
                if not result:
                    overall_success = False
            except Exception as e:
                test_results[test_name] = False
                self.failures.append(f"{test_name} failed with exception: {str(e)}")
                logger.error(f"✗ {test_name} failed with exception: {str(e)}")
                overall_success = False
        
        # Generate final report
        self.results['test_results'] = test_results
        self.results['overall_success'] = overall_success
        self.results['timestamp'] = datetime.now().isoformat()
        self.results['total_failures'] = len(self.failures)
        
        return self.results

    def generate_report(self) -> str:
        """Generate a comprehensive validation report."""
        report = []
        report.append("=" * 80)
        report.append("POST-DEPLOYMENT VALIDATION REPORT")
        report.append("=" * 80)
        report.append(f"Project: {self.project_id}")
        report.append(f"Timestamp: {self.results.get('timestamp', 'N/A')}")
        report.append(f"Overall Status: {'PASS' if self.results.get('overall_success', False) else 'FAIL'}")
        report.append(f"Total Failures: {self.results.get('total_failures', 0)}")
        report.append("")
        
        # Test results summary
        report.append("TEST RESULTS SUMMARY:")
        report.append("-" * 40)
        test_results = self.results.get('test_results', {})
        for test_name, result in test_results.items():
            status = "PASS" if result else "FAIL"
            report.append(f"{test_name:25} : {status}")
        report.append("")
        
        # Detailed failures
        if self.failures:
            report.append("DETAILED FAILURES:")
            report.append("-" * 40)
            for i, failure in enumerate(self.failures, 1):
                report.append(f"{i}. {failure}")
            report.append("")
        
        # Individual test details
        report.append("DETAILED TEST RESULTS:")
        report.append("-" * 40)
        
        for test_category, results in self.results.items():
            if test_category not in ['test_results', 'overall_success', 'timestamp', 'total_failures']:
                report.append(f"\n{test_category.upper()}:")
                if isinstance(results, dict):
                    for key, value in results.items():
                        status = "PASS" if value else "FAIL"
                        report.append(f"  {key}: {status}")
                else:
                    status = "PASS" if results else "FAIL"
                    report.append(f"  {test_category}: {status}")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)

    def save_results(self, filename: str = "post_deployment_validation.json"):
        """Save validation results to a file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"post_deployment_validation_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Validation results saved to {filename}")

def main():
    """Main function to run post-deployment validation."""
    print("MedellínBot - Post-Deployment Validation")
    print("=" * 50)
    
    # Parse command line arguments
    project_id = "medellinbot-prd-440915"
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
    
    # Run validation
    validator = PostDeploymentValidator(project_id)
    results = validator.run_all_tests()
    
    # Generate and display report
    report = validator.generate_report()
    print(report)
    
    # Save results
    validator.save_results()
    
    # Exit with appropriate code
    sys.exit(0 if results['overall_success'] else 1)

if __name__ == "__main__":
    main()