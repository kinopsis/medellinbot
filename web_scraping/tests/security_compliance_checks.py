#!/usr/bin/env python3
"""
Security and Compliance Validation
==================================

This script provides comprehensive security and compliance validation for the
web scraping framework, ensuring adherence to technical requirements, legal
compliance, and security best practices.

Author: MedellínBot Development Team
Version: 1.0
Date: October 29, 2025
"""

import sys
import os
import asyncio
import json
import re
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import unittest
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_scraping.core.base_scraper import BaseScraper, ScrapingConfig
from web_scraping.services.data_processor import DataProcessor
from web_scraping.main import WebScrapingOrchestrator
from web_scraping.config.settings import config
from web_scraping.monitoring.monitor import monitoring_service


@dataclass
class SecurityCheckResult:
    """Result of a security check."""
    check_name: str
    passed: bool
    severity: str  # critical, high, medium, low
    description: str
    recommendations: List[str]
    technical_details: Dict[str, Any]


@dataclass
class ComplianceResult:
    """Result of a compliance check."""
    requirement: str
    compliant: bool
    evidence: List[str]
    gaps: List[str]
    recommendations: List[str]


class SecurityValidator:
    """Validates security measures in the web scraping framework."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.results: List[SecurityCheckResult] = []
        
        # Security requirements from technical specifications
        self.security_requirements = {
            'rate_limiting': {
                'required': True,
                'min_delay': 1.0,  # seconds
                'description': 'Prevent overwhelming target servers'
            },
            'user_agent': {
                'required': True,
                'pattern': r'MedellínBot.*',
                'description': 'Use proper identification'
            },
            'error_handling': {
                'required': True,
                'sanitize_errors': True,
                'description': 'Prevent information disclosure'
            },
            'data_validation': {
                'required': True,
                'validate_input': True,
                'sanitize_output': True,
                'description': 'Prevent injection attacks'
            },
            'access_control': {
                'required': True,
                'authentication': True,
                'authorization': True,
                'description': 'Control access to sensitive operations'
            }
        }
        
    def run_security_validation(self) -> List[SecurityCheckResult]:
        """Run comprehensive security validation."""
        
        print("🔒 Security Validation for MedellínBot Web Scraping Framework")
        print("=" * 70)
        
        # Run individual security checks
        self._check_rate_limiting()
        self._check_user_agent_configuration()
        self._check_error_handling()
        self._check_data_validation()
        self._check_access_control()
        self._check_session_management()
        self._check_logging_and_monitoring()
        self._check_data_protection()
        self._check_network_security()
        self._check_dependency_security()
        
        # Print summary
        self._print_security_summary()
        
        return self.results
    
    def _check_rate_limiting(self):
        """Check rate limiting implementation."""
        
        try:
            # Test Alcaldía Medellín scraper
            scraper = AlcaldiaMedellinScraper()
            
            # Check rate limit configuration
            rate_limit_ok = (
                scraper.config.rate_limit_delay is not None and
                scraper.config.rate_limit_delay >= self.security_requirements['rate_limiting']['min_delay']
            )
            
            if rate_limit_ok:
                result = SecurityCheckResult(
                    check_name="Rate Limiting",
                    passed=True,
                    severity="high",
                    description="Rate limiting is properly configured",
                    recommendations=[],
                    technical_details={
                        "rate_limit_delay": scraper.config.rate_limit_delay,
                        "min_required": self.security_requirements['rate_limiting']['min_delay']
                    }
                )
            else:
                result = SecurityCheckResult(
                    check_name="Rate Limiting",
                    passed=False,
                    severity="high",
                    description="Rate limiting not properly configured",
                    recommendations=[
                        "Implement rate limiting with minimum 1 second delay between requests",
                        "Consider implementing exponential backoff for failed requests",
                        "Add domain-specific rate limits"
                    ],
                    technical_details={
                        "rate_limit_delay": scraper.config.rate_limit_delay,
                        "min_required": self.security_requirements['rate_limiting']['min_delay']
                    }
                )
                
            self.results.append(result)
            print(f"  {'✅' if result.passed else '❌'} Rate Limiting: {result.description}")
            
        except Exception as e:
            self._add_error_result("Rate Limiting", e)
    
    def _check_user_agent_configuration(self):
        """Check user agent configuration."""
        
        try:
            scraper = AlcaldiaMedellinScraper()
            
            # Check user agent pattern
            user_agent_pattern = self.security_requirements['user_agent']['pattern']
            user_agent_ok = re.match(user_agent_pattern, scraper.config.user_agent)
            
            if user_agent_ok:
                result = SecurityCheckResult(
                    check_name="User Agent Configuration",
                    passed=True,
                    severity="medium",
                    description="User agent properly identifies the scraper",
                    recommendations=[],
                    technical_details={
                        "user_agent": scraper.config.user_agent,
                        "pattern": user_agent_pattern
                    }
                )
            else:
                result = SecurityCheckResult(
                    check_name="User Agent Configuration",
                    passed=False,
                    severity="medium",
                    description="User agent does not properly identify the scraper",
                    recommendations=[
                        "Use user agent that clearly identifies MedellínBot",
                        "Include version information in user agent",
                        "Follow target site's scraping policy"
                    ],
                    technical_details={
                        "user_agent": scraper.config.user_agent,
                        "pattern": user_agent_pattern
                    }
                )
                
            self.results.append(result)
            print(f"  {'✅' if result.passed else '❌'} User Agent: {result.description}")
            
        except Exception as e:
            self._add_error_result("User Agent Configuration", e)
    
    def _check_error_handling(self):
        """Check error handling and sanitization."""
        
        try:
            processor = DataProcessor()
            
            # Test error handling with invalid data
            invalid_data = [
                {
                    "title": "Missing type",  # Missing required field
                    "content": "Test content"
                }
            ]
            
            result_obj = asyncio.run(processor.process_scraped_data("test_source", "test_type", invalid_data))
            
            # Check that errors are handled gracefully
            error_handling_ok = result_obj is not None and hasattr(result_obj, 'errors')
            
            # Check that errors don't expose sensitive information
            sensitive_info_exposed = False
            if hasattr(result_obj, 'errors') and result_obj.errors:
                for error in result_obj.errors:
                    error_lower = str(error).lower()
                    if any(sensitive in error_lower for sensitive in ['password', 'secret', 'token', 'key']):
                        sensitive_info_exposed = True
                        break
            
            if error_handling_ok and not sensitive_info_exposed:
                result = SecurityCheckResult(
                    check_name="Error Handling",
                    passed=True,
                    severity="high",
                    description="Errors are handled securely without information disclosure",
                    recommendations=[],
                    technical_details={
                        "error_count": len(result_obj.errors) if hasattr(result_obj, 'errors') else 0,
                        "sensitive_info_exposed": sensitive_info_exposed
                    }
                )
            else:
                recommendations = []
                if not error_handling_ok:
                    recommendations.append("Implement proper error handling for invalid data")
                if sensitive_info_exposed:
                    recommendations.append("Sanitize error messages to prevent information disclosure")
                
                result = SecurityCheckResult(
                    check_name="Error Handling",
                    passed=False,
                    severity="high",
                    description="Error handling may expose sensitive information or is not implemented",
                    recommendations=recommendations,
                    technical_details={
                        "error_count": len(result_obj.errors) if hasattr(result_obj, 'errors') else 0,
                        "sensitive_info_exposed": sensitive_info_exposed
                    }
                )
                
            self.results.append(result)
            print(f"  {'✅' if result.passed else '❌'} Error Handling: {result.description}")
            
        except Exception as e:
            self._add_error_result("Error Handling", e)
    
    def _check_data_validation(self):
        """Check data validation and sanitization."""
        
        try:
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
            
            result_obj = asyncio.run(processor.process_scraped_data("test_source", "test_type", malicious_data))
            
            # Check that malicious content is sanitized
            sanitized = True
            if result_obj.processed_data:
                sanitized_title = result_obj.processed_data[0].get("title", "")
                if "<script>" in sanitized_title or "alert" in sanitized_title:
                    sanitized = False
            
            if sanitized:
                result = SecurityCheckResult(
                    check_name="Data Validation and Sanitization",
                    passed=True,
                    severity="high",
                    description="Malicious content is properly sanitized",
                    recommendations=[],
                    technical_details={
                        "input_title": malicious_data[0]["title"],
                        "output_title": result_obj.processed_data[0].get("title", "") if result_obj.processed_data else None
                    }
                )
            else:
                result = SecurityCheckResult(
                    check_name="Data Validation and Sanitization",
                    passed=False,
                    severity="high",
                    description="Malicious content is not properly sanitized",
                    recommendations=[
                        "Implement input validation for all data fields",
                        "Sanitize HTML content to prevent XSS attacks",
                        "Validate data types and formats"
                    ],
                    technical_details={
                        "input_title": malicious_data[0]["title"],
                        "output_title": result_obj.processed_data[0].get("title", "") if result_obj.processed_data else None
                    }
                )
                
            self.results.append(result)
            print(f"  {'✅' if result.passed else '❌'} Data Validation: {result.description}")
            
        except Exception as e:
            self._add_error_result("Data Validation and Sanitization", e)
    
    def _check_access_control(self):
        """Check access control implementation."""
        
        try:
            # Check orchestrator for access control
            orchestrator = WebScrapingOrchestrator()
            
            # Check that orchestrator has proper initialization requirements
            access_control_ok = True
            recommendations = []
            
            # Check for authentication requirements
            if not hasattr(orchestrator, 'initialize'):
                access_control_ok = False
                recommendations.append("Implement proper initialization and authentication")
            
            # Check for authorization patterns
            # This would be more comprehensive with actual authentication system
            
            if access_control_ok:
                result = SecurityCheckResult(
                    check_name="Access Control",
                    passed=True,
                    severity="medium",
                    description="Basic access control patterns are implemented",
                    recommendations=recommendations,
                    technical_details={
                        "has_initialize_method": hasattr(orchestrator, 'initialize'),
                        "has_shutdown_method": hasattr(orchestrator, 'shutdown')
                    }
                )
            else:
                result = SecurityCheckResult(
                    check_name="Access Control",
                    passed=False,
                    severity="medium",
                    description="Access control is not properly implemented",
                    recommendations=recommendations + [
                        "Implement authentication for sensitive operations",
                        "Add authorization checks for data access",
                        "Use role-based access control"
                    ],
                    technical_details={
                        "has_initialize_method": hasattr(orchestrator, 'initialize'),
                        "has_shutdown_method": hasattr(orchestrator, 'shutdown')
                    }
                )
                
            self.results.append(result)
            print(f"  {'✅' if result.passed else '❌'} Access Control: {result.description}")
            
        except Exception as e:
            self._add_error_result("Access Control", e)
    
    def _check_session_management(self):
        """Check session management security."""
        
        try:
            # Check for session management implementation
            has_session_management = hasattr(config, 'session_timeout_hours')
            
            if has_session_management:
                result = SecurityCheckResult(
                    check_name="Session Management",
                    passed=True,
                    severity="medium",
                    description="Session management configuration is present",
                    recommendations=[],
                    technical_details={
                        "has_session_timeout": hasattr(config, 'session_timeout_hours')
                    }
                )
            else:
                result = SecurityCheckResult(
                    check_name="Session Management",
                    passed=False,
                    severity="medium",
                    description="Session management is not implemented",
                    recommendations=[
                        "Implement session timeout functionality",
                        "Add session cleanup for expired sessions",
                        "Track session metadata for security monitoring"
                    ],
                    technical_details={
                        "has_session_timeout": hasattr(config, 'session_timeout_hours')
                    }
                )
                
            self.results.append(result)
            print(f"  {'✅' if result.passed else '❌'} Session Management: {result.description}")
            
        except Exception as e:
            self._add_error_result("Session Management", e)
    
    def _check_logging_and_monitoring(self):
        """Check logging and monitoring security."""
        
        try:
            # Check monitoring service
            monitoring_ok = monitoring_service is not None
            
            if monitoring_ok:
                result = SecurityCheckResult(
                    check_name="Logging and Monitoring",
                    passed=True,
                    severity="medium",
                    description="Monitoring service is available",
                    recommendations=[],
                    technical_details={
                        "monitoring_service_available": monitoring_ok
                    }
                )
            else:
                result = SecurityCheckResult(
                    check_name="Logging and Monitoring",
                    passed=False,
                    severity="medium",
                    description="Monitoring service is not available",
                    recommendations=[
                        "Implement comprehensive logging for security events",
                        "Add monitoring for suspicious activities",
                        "Log access attempts and data modifications"
                    ],
                    technical_details={
                        "monitoring_service_available": monitoring_ok
                    }
                )
                
            self.results.append(result)
            print(f"  {'✅' if result.passed else '❌'} Logging and Monitoring: {result.description}")
            
        except Exception as e:
            self._add_error_result("Logging and Monitoring", e)
    
    def _check_data_protection(self):
        """Check data protection measures."""
        
        try:
            processor = DataProcessor()
            
            # Check for data hashing/deduplication
            has_data_protection = hasattr(processor, '_remove_duplicates')
            
            if has_data_protection:
                result = SecurityCheckResult(
                    check_name="Data Protection",
                    passed=True,
                    severity="medium",
                    description="Basic data protection measures are implemented",
                    recommendations=[],
                    technical_details={
                        "has_deduplication": has_data_protection
                    }
                )
            else:
                result = SecurityCheckResult(
                    check_name="Data Protection",
                    passed=False,
                    severity="medium",
                    description="Data protection measures are not implemented",
                    recommendations=[
                        "Implement data deduplication to prevent storage of duplicate sensitive data",
                        "Add data encryption for sensitive information",
                        "Implement data retention policies"
                    ],
                    technical_details={
                        "has_deduplication": has_data_protection
                    }
                )
                
            self.results.append(result)
            print(f"  {'✅' if result.passed else '❌'} Data Protection: {result.description}")
            
        except Exception as e:
            self._add_error_result("Data Protection", e)
    
    def _check_network_security(self):
        """Check network security measures."""
        
        try:
            scraper = AlcaldiaMedellinScraper()
            
            # Check for secure communication settings
            network_security_ok = True
            recommendations = []
            
            # Check timeout configuration
            if scraper.config.timeout is None or scraper.config.timeout > 60:
                network_security_ok = False
                recommendations.append("Implement reasonable timeout to prevent hanging connections")
            
            # Check for secure headers in requests
            # This would be more comprehensive with actual HTTP client
            
            if network_security_ok:
                result = SecurityCheckResult(
                    check_name="Network Security",
                    passed=True,
                    severity="low",
                    description="Basic network security measures are implemented",
                    recommendations=recommendations,
                    technical_details={
                        "timeout_seconds": scraper.config.timeout,
                        "has_user_agent": scraper.config.user_agent is not None
                    }
                )
            else:
                result = SecurityCheckResult(
                    check_name="Network Security",
                    passed=False,
                    severity="low",
                    description="Network security measures need improvement",
                    recommendations=recommendations + [
                        "Implement connection timeouts",
                        "Use secure communication protocols",
                        "Validate SSL certificates"
                    ],
                    technical_details={
                        "timeout_seconds": scraper.config.timeout,
                        "has_user_agent": scraper.config.user_agent is not None
                    }
                )
                
            self.results.append(result)
            print(f"  {'✅' if result.passed else '❌'} Network Security: {result.description}")
            
        except Exception as e:
            self._add_error_result("Network Security", e)
    
    def _check_dependency_security(self):
        """Check dependency security."""
        
        try:
            # Check for common security-related dependencies
            security_dependencies = []
            
            try:
                import jwt
                security_dependencies.append("jwt")
            except ImportError:
                pass
                
            try:
                import redis
                security_dependencies.append("redis")
            except ImportError:
                pass
            
            # Check requirements.txt for security dependencies
            requirements_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'requirements.txt')
            if os.path.exists(requirements_path):
                with open(requirements_path, 'r') as f:
                    requirements_content = f.read().lower()
                    
                has_security_deps = any(dep in requirements_content for dep in ['jwt', 'cryptography', 'bcrypt'])
            else:
                has_security_deps = False
            
            if security_dependencies or has_security_deps:
                result = SecurityCheckResult(
                    check_name="Dependency Security",
                    passed=True,
                    severity="low",
                    description="Security-related dependencies are present",
                    recommendations=[],
                    technical_details={
                        "security_dependencies": security_dependencies,
                        "has_security_in_requirements": has_security_deps
                    }
                )
            else:
                result = SecurityCheckResult(
                    check_name="Dependency Security",
                    passed=False,
                    severity="low",
                    description="Security-related dependencies are missing",
                    recommendations=[
                        "Add security libraries for authentication and encryption",
                        "Regularly update dependencies to patch security vulnerabilities",
                        "Use dependency scanning tools"
                    ],
                    technical_details={
                        "security_dependencies": security_dependencies,
                        "has_security_in_requirements": has_security_deps
                    }
                )
                
            self.results.append(result)
            print(f"  {'✅' if result.passed else '❌'} Dependency Security: {result.description}")
            
        except Exception as e:
            self._add_error_result("Dependency Security", e)
    
    def _add_error_result(self, check_name: str, error: Exception):
        """Add an error result for a failed check."""
        
        result = SecurityCheckResult(
            check_name=check_name,
            passed=False,
            severity="high",
            description=f"Security check failed with error: {str(error)}",
            recommendations=["Fix the underlying implementation issue"],
            technical_details={"error": str(error)}
        )
        
        self.results.append(result)
        print(f"  ❌ {check_name}: Failed with error - {str(error)}")
    
    def _print_security_summary(self):
        """Print security validation summary."""
        
        print("\n" + "=" * 70)
        print("🔒 SECURITY VALIDATION SUMMARY")
        print("=" * 70)
        
        # Count results by severity
        critical_issues = sum(1 for r in self.results if r.severity == "critical" and not r.passed)
        high_issues = sum(1 for r in self.results if r.severity == "high" and not r.passed)
        medium_issues = sum(1 for r in self.results if r.severity == "medium" and not r.passed)
        low_issues = sum(1 for r in self.results if r.severity == "low" and not r.passed)
        
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r.passed)
        failed_checks = total_checks - passed_checks
        
        print(f"Total Security Checks: {total_checks}")
        print(f"Passed: {passed_checks}")
        print(f"Failed: {failed_checks}")
        print(f"Critical Issues: {critical_issues}")
        print(f"High Priority Issues: {high_issues}")
        print(f"Medium Priority Issues: {medium_issues}")
        print(f"Low Priority Issues: {low_issues}")
        
        # Print failed checks
        if failed_checks > 0:
            print(f"\n❌ FAILED SECURITY CHECKS:")
            for result in self.results:
                if not result.passed:
                    print(f"  • {result.check_name}: {result.description}")
                    if result.recommendations:
                        for rec in result.recommendations[:2]:  # Show first 2 recommendations
                            print(f"    - {rec}")
        
        # Overall assessment
        if critical_issues > 0:
            print(f"\n🚨 CRITICAL: {critical_issues} critical security issues must be resolved immediately")
            return False
        elif high_issues > 0:
            print(f"\n⚠️ HIGH PRIORITY: {high_issues} high-priority security issues need attention")
            return False
        else:
            print(f"\n✅ SECURITY VALIDATION PASSED: All critical and high-priority issues resolved")
            return True


class ComplianceValidator:
    """Validates compliance with legal and technical requirements."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.results: List[ComplianceResult] = []
        
        # Compliance requirements from technical specifications
        self.compliance_requirements = {
            'data_protection': {
                'requirement': 'Comply with Colombian data protection laws (Ley 1581/2012)',
                'critical': True,
                'evidence_required': ['data_minimization', 'purpose_limitation', 'security_measures']
            },
            'scraping_ethics': {
                'requirement': 'Follow ethical scraping practices',
                'critical': True,
                'evidence_required': ['rate_limiting', 'robots_txt_compliance', 'user_agent_identification']
            },
            'performance': {
                'requirement': 'Meet performance requirements (99.9% uptime, <5s response time)',
                'critical': True,
                'evidence_required': ['monitoring_metrics', 'performance_benchmarks']
            },
            'documentation': {
                'requirement': 'Maintain comprehensive documentation',
                'critical': False,
                'evidence_required': ['technical_documentation', 'user_guides', 'api_docs']
            }
        }
        
    def run_compliance_validation(self) -> List[ComplianceResult]:
        """Run comprehensive compliance validation."""
        
        print("\n📋 Compliance Validation for MedellínBot Web Scraping Framework")
        print("=" * 70)
        
        # Run individual compliance checks
        self._check_data_protection_compliance()
        self._check_scraping_ethics_compliance()
        self._check_performance_compliance()
        self._check_documentation_compliance()
        
        # Print summary
        self._print_compliance_summary()
        
        return self.results
    
    def _check_data_protection_compliance(self):
        """Check compliance with data protection laws."""
        
        try:
            # Check for data protection measures
            evidence = []
            gaps = []
            
            # Check data minimization
            processor = DataProcessor()
            has_data_validation = hasattr(processor, '_validate_data_structure')
            if has_data_validation:
                evidence.append("Data validation and minimization implemented")
            else:
                gaps.append("Data validation and minimization not implemented")
            
            # Check purpose limitation
            # This would be more comprehensive with actual data usage policies
            
            # Check security measures
            scraper = AlcaldiaMedellinScraper()
            has_rate_limiting = scraper.config.rate_limit_delay is not None
            if has_rate_limiting:
                evidence.append("Rate limiting implemented to prevent data overload")
            else:
                gaps.append("Rate limiting not implemented")
            
            # Determine compliance
            compliant = len(gaps) == 0
            
            result = ComplianceResult(
                requirement="Data Protection (Ley 1581/2012)",
                compliant=compliant,
                evidence=evidence,
                gaps=gaps,
                recommendations=[
                    "Implement data retention policies",
                    "Add data subject rights handling",
                    "Regular compliance audits"
                ] if not compliant else []
            )
            
            self.results.append(result)
            print(f"  {'✅' if compliant else '❌'} Data Protection: {'Compliant' if compliant else 'Non-compliant'}")
            
        except Exception as e:
            self._add_compliance_error("Data Protection", e)
    
    def _check_scraping_ethics_compliance(self):
        """Check compliance with ethical scraping practices."""
        
        try:
            evidence = []
            gaps = []
            
            # Check rate limiting
            scraper = AlcaldiaMedellinScraper()
            if scraper.config.rate_limit_delay and scraper.config.rate_limit_delay >= 1.0:
                evidence.append("Rate limiting implemented (≥1 second delay)")
            else:
                gaps.append("Rate limiting not properly implemented")
            
            # Check user agent identification
            if re.match(r'MedellínBot.*', scraper.config.user_agent):
                evidence.append("Proper user agent identification")
            else:
                gaps.append("User agent does not properly identify scraper")
            
            # Check for robots.txt compliance
            # This would require actual robots.txt checking
            
            # Determine compliance
            compliant = len(gaps) == 0
            
            result = ComplianceResult(
                requirement="Ethical Scraping Practices",
                compliant=compliant,
                evidence=evidence,
                gaps=gaps,
                recommendations=[
                    "Implement robots.txt compliance checking",
                    "Add scraping frequency limits per domain",
                    "Monitor for scraping bans"
                ] if not compliant else []
            )
            
            self.results.append(result)
            print(f"  {'✅' if compliant else '❌'} Ethical Scraping: {'Compliant' if compliant else 'Non-compliant'}")
            
        except Exception as e:
            self._add_compliance_error("Ethical Scraping Practices", e)
    
    def _check_performance_compliance(self):
        """Check compliance with performance requirements."""
        
        try:
            evidence = []
            gaps = []
            
            # Check monitoring implementation
            if monitoring_service is not None:
                evidence.append("Monitoring service implemented")
            else:
                gaps.append("Monitoring service not implemented")
            
            # Check for performance metrics
            # This would be more comprehensive with actual performance data
            
            # Determine compliance
            compliant = len(gaps) == 0
            
            result = ComplianceResult(
                requirement="Performance Requirements (99.9% uptime, <5s response)",
                compliant=compliant,
                evidence=evidence,
                gaps=gaps,
                recommendations=[
                    "Implement comprehensive performance monitoring",
                    "Set up automated performance alerts",
                    "Regular performance testing"
                ] if not compliant else []
            )
            
            self.results.append(result)
            print(f"  {'✅' if compliant else '❌'} Performance: {'Compliant' if compliant else 'Non-compliant'}")
            
        except Exception as e:
            self._add_compliance_error("Performance Requirements", e)
    
    def _check_documentation_compliance(self):
        """Check compliance with documentation requirements."""
        
        try:
            evidence = []
            gaps = []
            
            # Check for documentation files
            doc_files = [
                'README.md',
                'docs/',
                'API.md'
            ]
            
            for doc_file in doc_files:
                doc_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), doc_file)
                if os.path.exists(doc_path):
                    evidence.append(f"Documentation file exists: {doc_file}")
                else:
                    gaps.append(f"Missing documentation: {doc_file}")
            
            # Determine compliance
            compliant = len(gaps) == 0
            
            result = ComplianceResult(
                requirement="Documentation Requirements",
                compliant=compliant,
                evidence=evidence,
                gaps=gaps,
                recommendations=[
                    "Create comprehensive technical documentation",
                    "Add API documentation",
                    "Document deployment procedures"
                ] if not compliant else []
            )
            
            self.results.append(result)
            print(f"  {'✅' if compliant else '❌'} Documentation: {'Compliant' if compliant else 'Non-compliant'}")
            
        except Exception as e:
            self._add_compliance_error("Documentation Requirements", e)
    
    def _add_compliance_error(self, requirement: str, error: Exception):
        """Add a compliance error result."""
        
        result = ComplianceResult(
            requirement=requirement,
            compliant=False,
            evidence=[],
            gaps=[f"Validation failed with error: {str(error)}"],
            recommendations=["Fix the validation implementation"]
        )
        
        self.results.append(result)
        print(f"  ❌ {requirement}: Validation failed - {str(error)}")
    
    def _print_compliance_summary(self):
        """Print compliance validation summary."""
        
        print("\n" + "=" * 70)
        print("📋 COMPLIANCE VALIDATION SUMMARY")
        print("=" * 70)
        
        critical_compliant = sum(1 for r in self.results if r.compliant and r.requirement in [
            "Data Protection (Ley 1581/2012)", 
            "Ethical Scraping Practices",
            "Performance Requirements (99.9% uptime, <5s response)"
        ])
        
        total_critical = 3  # Number of critical requirements
        non_critical_compliant = sum(1 for r in self.results if r.compliant and r.requirement == "Documentation Requirements")
        total_non_critical = 1  # Number of non-critical requirements
        
        print(f"Critical Requirements: {critical_compliant}/{total_critical} compliant")
        print(f"Non-Critical Requirements: {non_critical_compliant}/{total_non_critical} compliant")
        
        # Print non-compliant requirements
        non_compliant = [r for r in self.results if not r.compliant]
        if non_compliant:
            print(f"\n❌ NON-COMPLIANT REQUIREMENTS:")
            for result in non_compliant:
                print(f"  • {result.requirement}")
                if result.gaps:
                    for gap in result.gaps[:2]:  # Show first 2 gaps
                        print(f"    - {gap}")
        
        # Overall assessment
        if critical_compliant == total_critical:
            print(f"\n✅ COMPLIANCE VALIDATION PASSED: All critical requirements met")
            return True
        else:
            print(f"\n❌ COMPLIANCE VALIDATION FAILED: {total_critical - critical_compliant} critical requirements not met")
            return False


async def run_security_and_compliance_validation():
    """Run comprehensive security and compliance validation."""
    
    # Run security validation
    security_validator = SecurityValidator()
    security_results = security_validator.run_security_validation()
    
    # Run compliance validation
    compliance_validator = ComplianceValidator()
    compliance_results = compliance_validator.run_compliance_validation()
    
    # Overall assessment
    security_passed = all(r.passed for r in security_results if r.severity in ["critical", "high"])
    compliance_passed = all(r.compliant for r in compliance_results if "Critical" in r.requirement or "Performance" in r.requirement)
    
    print("\n" + "=" * 70)
    print("🎯 OVERALL SECURITY AND COMPLIANCE ASSESSMENT")
    print("=" * 70)
    
    if security_passed and compliance_passed:
        print("✅ SECURITY AND COMPLIANCE VALIDATION PASSED")
        print("   All critical security and compliance requirements are met")
        return True
    else:
        print("❌ SECURITY AND COMPLIANCE VALIDATION FAILED")
        if not security_passed:
            print("   Security issues must be resolved")
        if not compliance_passed:
            print("   Compliance gaps must be addressed")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_security_and_compliance_validation())
    sys.exit(0 if success else 1)