#!/usr/bin/env python3
"""
Comprehensive Test Runner for MedellínBot System
Executes all test suites and generates detailed reports
"""

import pytest
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestRunner:
    """Comprehensive test runner for MedellínBot"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        self.test_dir = Path(__file__).parent
        self.reports_dir = self.test_dir / "reports"
        
        # Create reports directory
        self.reports_dir.mkdir(exist_ok=True)
    
    def run_unit_tests(self):
        """Run unit tests for webhook and orchestrator"""
        logger.info("Running unit tests...")
        
        # Run webhook unit tests
        webhook_result = self._run_pytest_suite(
            "test_webhook.py",
            "Webhook Handler Unit Tests"
        )
        
        # Run orchestrator unit tests
        orchestrator_result = self._run_pytest_suite(
            "test_orchestrator.py", 
            "Orchestrator Unit Tests"
        )
        
        self.test_results['unit_tests'] = {
            'webhook': webhook_result,
            'orchestrator': orchestrator_result
        }
    
    def run_integration_tests(self):
        """Run integration tests"""
        logger.info("Running integration tests...")
        
        integration_result = self._run_pytest_suite(
            "test_integration.py",
            "System Integration Tests"
        )
        
        self.test_results['integration_tests'] = integration_result
    
    def run_security_tests(self):
        """Run security-focused tests"""
        logger.info("Running security tests...")
        
        # Run security-related tests from existing suites
        security_result = self._run_pytest_suite(
            "test_webhook.py::TestSecurityAndValidation",
            "Webhook Security Tests"
        )
        
        security_result_orchestrator = self._run_pytest_suite(
            "test_orchestrator.py::TestSecurityAndValidation", 
            "Orchestrator Security Tests"
        )
        
        security_result_integration = self._run_pytest_suite(
            "test_integration.py::TestSecurityIntegration",
            "Integration Security Tests"
        )
        
        self.test_results['security_tests'] = {
            'webhook': security_result,
            'orchestrator': security_result_orchestrator,
            'integration': security_result_integration
        }
    
    def run_performance_tests(self):
        """Run performance tests"""
        logger.info("Running performance tests...")
        
        # Run performance tests
        performance_result = self._run_pytest_suite(
            "test_webhook.py::TestPerformance",
            "Webhook Performance Tests"
        )
        
        performance_result_orchestrator = self._run_pytest_suite(
            "test_orchestrator.py::TestPerformanceRequirements",
            "Orchestrator Performance Tests"
        )
        
        performance_result_integration = self._run_pytest_suite(
            "test_integration.py::TestPerformanceIntegration",
            "Integration Performance Tests"
        )
        
        self.test_results['performance_tests'] = {
            'webhook': performance_result,
            'orchestrator': performance_result_orchestrator,
            'integration': performance_result_integration
        }
    
    def _run_pytest_suite(self, test_file, test_name):
        """Run a specific pytest suite and capture results"""
        try:
            # Build test path
            test_path = self.test_dir / test_file
            
            if not test_path.exists():
                logger.warning(f"Test file not found: {test_path}")
                return {
                    'status': 'skipped',
                    'message': f"Test file not found: {test_path}",
                    'duration': 0,
                    'tests_run': 0,
                    'passed': 0,
                    'failed': 0,
                    'skipped': 0
                }
            
            # Run pytest with detailed output
            cmd = [
                sys.executable, '-m', 'pytest',
                str(test_path),
                '-v',
                '--tb=short',
                '--json-report',
                f'--json-report-file={self.reports_dir}/{test_file.replace("/", "_").replace(".py", "")}_report.json'
            ]
            
            start_time = time.time()
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.test_dir
            )
            
            duration = time.time() - start_time
            
            # Parse pytest output
            tests_run = 0
            passed = 0
            failed = 0
            skipped = 0
            
            # Parse stdout for test results
            if result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'passed' in line and 'deselected' not in line:
                        # Extract numbers from line like "=== 10 passed, 2 skipped in 1.23s ==="
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'passed':
                                passed = int(parts[i-1]) if i > 0 and parts[i-1].isdigit() else 0
                            elif part == 'failed':
                                failed = int(parts[i-1]) if i > 0 and parts[i-1].isdigit() else 0
                            elif part == 'skipped':
                                skipped = int(parts[i-1]) if i > 0 and parts[i-1].isdigit() else 0
                        tests_run = passed + failed + skipped
                        break
            
            status = 'passed' if result.returncode == 0 else 'failed'
            
            return {
                'status': status,
                'return_code': result.returncode,
                'duration': round(duration, 3),
                'tests_run': tests_run,
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except Exception as e:
            logger.error(f"Error running test suite {test_name}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'duration': 0,
                'tests_run': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0
            }
    
    def run_linting_and_static_analysis(self):
        """Run linting and static analysis tools"""
        logger.info("Running linting and static analysis...")
        
        linting_results = {}
        
        # Check for common Python files that need linting
        python_files = list(self.test_dir.glob("*.py")) + \
                      list((self.test_dir / "webhook").glob("*.py")) + \
                      list((self.test_dir / "orchestrator").glob("*.py"))
        
        if python_files:
            # Run pylint if available
            try:
                pylint_cmd = ['pylint'] + [str(f) for f in python_files]
                pylint_result = subprocess.run(pylint_cmd, capture_output=True, text=True)
                
                linting_results['pylint'] = {
                    'status': 'passed' if pylint_result.returncode == 0 else 'failed',
                    'return_code': pylint_result.returncode,
                    'output': pylint_result.stdout + pylint_result.stderr
                }
            except FileNotFoundError:
                logger.warning("pylint not found, skipping")
                linting_results['pylint'] = {'status': 'skipped', 'message': 'pylint not available'}
            
            # Run flake8 if available
            try:
                flake8_cmd = ['flake8'] + [str(f) for f in python_files]
                flake8_result = subprocess.run(flake8_cmd, capture_output=True, text=True)
                
                linting_results['flake8'] = {
                    'status': 'passed' if flake8_result.returncode == 0 else 'failed',
                    'return_code': flake8_result.returncode,
                    'output': flake8_result.stdout + flake8_result.stderr
                }
            except FileNotFoundError:
                logger.warning("flake8 not found, skipping")
                linting_results['flake8'] = {'status': 'skipped', 'message': 'flake8 not available'}
        
        self.test_results['linting'] = linting_results
    
    def generate_comprehensive_report(self):
        """Generate comprehensive test report"""
        logger.info("Generating comprehensive test report...")
        
        report = {
            'test_execution': {
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': self.end_time.isoformat() if self.end_time else None,
                'duration': round((self.end_time - self.start_time).total_seconds(), 3) if self.start_time and self.end_time else 0,
                'timestamp': datetime.now().isoformat()
            },
            'summary': self._generate_summary(),
            'detailed_results': self.test_results,
            'requirements_validation': self._validate_requirements(),
            'security_assessment': self._assess_security(),
            'performance_assessment': self._assess_performance()
        }
        
        # Save detailed report
        report_file = self.reports_dir / f"comprehensive_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Generate markdown summary
        markdown_report = self._generate_markdown_report(report)
        markdown_file = self.reports_dir / f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(markdown_file, 'w') as f:
            f.write(markdown_report)
        
        return report, report_file, markdown_file
    
    def _generate_summary(self):
        """Generate test summary"""
        summary = {
            'total_tests_run': 0,
            'total_passed': 0,
            'total_failed': 0,
            'total_skipped': 0,
            'overall_status': 'passed'
        }
        
        # Aggregate results from all test categories
        for category, results in self.test_results.items():
            if isinstance(results, dict):
                for subcategory, result in results.items():
                    if isinstance(result, dict):
                        summary['total_tests_run'] += result.get('tests_run', 0)
                        summary['total_passed'] += result.get('passed', 0)
                        summary['total_failed'] += result.get('failed', 0)
                        summary['total_skipped'] += result.get('skipped', 0)
            elif isinstance(results, list):
                for result in results:
                    if isinstance(result, dict):
                        summary['total_tests_run'] += result.get('tests_run', 0)
                        summary['total_passed'] += result.get('passed', 0)
                        summary['total_failed'] += result.get('failed', 0)
                        summary['total_skipped'] += result.get('skipped', 0)
        
        # Determine overall status
        if summary['total_failed'] > 0:
            summary['overall_status'] = 'failed'
        elif summary['total_tests_run'] == 0:
            summary['overall_status'] = 'no_tests'
        
        return summary
    
    def _validate_requirements(self):
        """Validate test coverage against requirements"""
        requirements = {
            'functional_requirements': {
                'RF-1': {'description': 'Intelligent Procedure Guide', 'tested': False, 'status': 'pending'},
                'RF-2': {'description': 'PQRSD Router', 'tested': False, 'status': 'pending'},
                'RF-3': {'description': 'Social Programs', 'tested': False, 'status': 'pending'},
                'RF-4': {'description': 'Proactive Notifications', 'tested': False, 'status': 'pending'},
                'RF-5': {'description': '24/7 Attention', 'tested': False, 'status': 'pending'},
                'RF-6': {'description': 'Multi-turn Conversations', 'tested': False, 'status': 'pending'}
            },
            'non_functional_requirements': {
                'RNF-1': {'description': 'Scalability', 'tested': False, 'status': 'pending'},
                'RNF-2': {'description': 'Security and Privacy', 'tested': True, 'status': 'in_progress'},
                'RNF-3': {'description': 'Latency', 'tested': True, 'status': 'in_progress'},
                'RNF-4': {'description': 'Availability', 'tested': False, 'status': 'pending'},
                'RNF-5': {'description': 'Maintainability', 'tested': False, 'status': 'pending'},
                'RNF-6': {'description': 'Usability', 'tested': False, 'status': 'pending'}
            },
            'success_criteria': {
                'SC-1': {'description': 'Functional prototype in 4 weeks', 'tested': False, 'status': 'pending'},
                'SC-2': {'description': 'Precision >80% in classification', 'tested': True, 'status': 'in_progress'},
                'SC-3': {'description': '100 active beta users in pilot', 'tested': False, 'status': 'pending'},
                'SC-4': {'description': 'Responses in <3 seconds', 'tested': True, 'status': 'in_progress'},
                'SC-5': {'description': 'High user satisfaction (NPS >60)', 'tested': False, 'status': 'pending'}
            }
        }
        
        # Update status based on test results
        if 'security_tests' in self.test_results:
            requirements['non_functional_requirements']['RNF-2']['status'] = 'completed'
        
        if 'performance_tests' in self.test_results:
            requirements['non_functional_requirements']['RNF-3']['status'] = 'completed'
            requirements['success_criteria']['SC-4']['status'] = 'completed'
        
        return requirements
    
    def _assess_security(self):
        """Assess security posture based on test results"""
        security_issues = []
        security_score = 100
        
        # Check for security test failures
        if 'security_tests' in self.test_results:
            for category, result in self.test_results['security_tests'].items():
                if result.get('status') == 'failed':
                    security_issues.append(f"Security test failure in {category}")
                    security_score -= 20
        
        # Check for authentication issues
        if 'unit_tests' in self.test_results:
            webhook_tests = self.test_results['unit_tests'].get('webhook', {})
            if webhook_tests.get('status') == 'failed':
                security_score -= 10
        
        return {
            'security_score': max(0, security_score),
            'issues': security_issues,
            'risk_level': 'low' if security_score >= 80 else 'medium' if security_score >= 60 else 'high',
            'recommendations': self._generate_security_recommendations(security_issues)
        }
    
    def _assess_performance(self):
        """Assess performance based on test results"""
        performance_issues = []
        performance_score = 100
        
        # Check performance test results
        if 'performance_tests' in self.test_results:
            for category, result in self.test_results['performance_tests'].items():
                if result.get('status') == 'failed':
                    performance_issues.append(f"Performance test failure in {category}")
                    performance_score -= 25
        
        # Check for timeout issues
        if 'integration_tests' in self.test_results:
            integration_result = self.test_results['integration_tests']
            if integration_result.get('status') == 'failed':
                performance_issues.append("Integration test failures may indicate performance issues")
                performance_score -= 15
        
        return {
            'performance_score': max(0, performance_score),
            'issues': performance_issues,
            'latency_compliance': performance_score >= 80,
            'recommendations': self._generate_performance_recommendations(performance_issues)
        }
    
    def _generate_security_recommendations(self, security_issues):
        """Generate security recommendations"""
        recommendations = []
        
        if not security_issues:
            recommendations.append("Security posture is good. Continue regular security testing.")
        else:
            recommendations.append("Address identified security issues before production deployment.")
            recommendations.append("Implement regular security audits and penetration testing.")
            recommendations.append("Ensure all secrets are properly managed and rotated.")
        
        return recommendations
    
    def _generate_performance_recommendations(self, performance_issues):
        """Generate performance recommendations"""
        recommendations = []
        
        if not performance_issues:
            recommendations.append("Performance requirements are met. Continue monitoring.")
        else:
            recommendations.append("Optimize components with performance issues.")
            recommendations.append("Implement caching for frequently accessed data.")
            recommendations.append("Consider load balancing for high-traffic scenarios.")
        
        return recommendations
    
    def _generate_markdown_report(self, report):
        """Generate markdown report"""
        markdown = f"""
# MedellínBot Test Report

**Generated:** {report['test_execution']['timestamp']}
**Duration:** {report['test_execution']['duration']} seconds

## Executive Summary

- **Overall Status:** {report['summary']['overall_status'].upper()}
- **Total Tests Run:** {report['summary']['total_tests_run']}
- **Passed:** {report['summary']['total_passed']}
- **Failed:** {report['summary']['total_failed']}
- **Skipped:** {report['summary']['total_skipped']}
- **Success Rate:** {round(report['summary']['total_passed']/report['summary']['total_tests_run']*100, 2) if report['summary']['total_tests_run'] > 0 else 0}%

## Security Assessment

- **Security Score:** {report['security_assessment']['security_score']}/100
- **Risk Level:** {report['security_assessment']['risk_level'].upper()}
- **Issues Found:** {len(report['security_assessment']['issues'])}

### Security Issues
"""
        
        if report['security_assessment']['issues']:
            for issue in report['security_assessment']['issues']:
                markdown += f"- {issue}\n"
        else:
            markdown += "- No critical security issues found\n"
        
        markdown += "\n### Security Recommendations\n"
        for rec in report['security_assessment']['recommendations']:
            markdown += f"- {rec}\n"
        
        markdown += f"""
## Performance Assessment

- **Performance Score:** {report['performance_assessment']['performance_score']}/100
- **Latency Compliance:** {"✅ PASS" if report['performance_assessment']['latency_compliance'] else "❌ FAIL"}
- **Issues Found:** {len(report['performance_assessment']['issues'])}

### Performance Issues
"""
        
        if report['performance_assessment']['issues']:
            for issue in report['performance_assessment']['issues']:
                markdown += f"- {issue}\n"
        else:
            markdown += "- No critical performance issues found\n"
        
        markdown += "\n### Performance Recommendations\n"
        for rec in report['performance_assessment']['recommendations']:
            markdown += f"- {rec}\n"
        
        markdown += """
## Test Categories

### Unit Tests
"""
        
        if 'unit_tests' in report['detailed_results']:
            for category, result in report['detailed_results']['unit_tests'].items():
                status = "✅ PASS" if result['status'] == 'passed' else "❌ FAIL"
                markdown += f"- **{category.upper()}**: {status} ({result['tests_run']} tests, {result['passed']} passed, {result['failed']} failed)\n"
        
        markdown += """
### Integration Tests
"""
        
        if 'integration_tests' in report['detailed_results']:
            result = report['detailed_results']['integration_tests']
            status = "✅ PASS" if result['status'] == 'passed' else "❌ FAIL"
            markdown += f"- **Integration**: {status} ({result['tests_run']} tests, {result['passed']} passed, {result['failed']} failed)\n"
        
        markdown += """
### Security Tests
"""
        
        if 'security_tests' in report['detailed_results']:
            for category, result in report['detailed_results']['security_tests'].items():
                status = "✅ PASS" if result['status'] == 'passed' else "❌ FAIL"
                markdown += f"- **{category.upper()}**: {status} ({result['tests_run']} tests, {result['passed']} passed, {result['failed']} failed)\n"
        
        markdown += """
### Performance Tests
"""
        
        if 'performance_tests' in report['detailed_results']:
            for category, result in report['detailed_results']['performance_tests'].items():
                status = "✅ PASS" if result['status'] == 'passed' else "❌ FAIL"
                markdown += f"- **{category.upper()}**: {status} ({result['tests_run']} tests, {result['passed']} passed, {result['failed']} failed)\n"
        
        markdown += """
## Requirements Validation

### Functional Requirements
"""
        
        for req_id, req in report['requirements_validation']['functional_requirements'].items():
            status = "✅" if req['status'] == 'completed' else "⏳" if req['status'] == 'in_progress' else "❌"
            markdown += f"- **{req_id}**: {req['description']} {status}\n"
        
        markdown += """
### Non-Functional Requirements
"""
        
        for req_id, req in report['requirements_validation']['non_functional_requirements'].items():
            status = "✅" if req['status'] == 'completed' else "⏳" if req['status'] == 'in_progress' else "❌"
            markdown += f"- **{req_id}**: {req['description']} {status}\n"
        
        markdown += """
### Success Criteria
"""
        
        for req_id, req in report['requirements_validation']['success_criteria'].items():
            status = "✅" if req['status'] == 'completed' else "⏳" if req['status'] == 'in_progress' else "❌"
            markdown += f"- **{req_id}**: {req['description']} {status}\n"
        
        return markdown
    
    def run_all_tests(self):
        """Run all test suites"""
        logger.info("Starting comprehensive test execution...")
        self.start_time = datetime.now()
        
        try:
            # Run all test categories
            self.run_unit_tests()
            self.run_integration_tests()
            self.run_security_tests()
            self.run_performance_tests()
            self.run_linting_and_static_analysis()
            
            # Generate final report
            self.end_time = datetime.now()
            report, report_file, markdown_file = self.generate_comprehensive_report()
            
            # Print summary
            summary = report['summary']
            print(f"\n{'='*60}")
            print("TEST EXECUTION SUMMARY")
            print(f"{'='*60}")
            print(f"Overall Status: {summary['overall_status'].upper()}")
            print(f"Total Tests: {summary['total_tests_run']}")
            print(f"Passed: {summary['total_passed']}")
            print(f"Failed: {summary['total_failed']}")
            print(f"Skipped: {summary['total_skipped']}")
            print(f"Success Rate: {round(summary['total_passed']/summary['total_tests_run']*100, 2) if summary['total_tests_run'] > 0 else 0}%")
            print(f"Duration: {summary['duration']} seconds")
            print(f"\nDetailed report saved to: {report_file}")
            print(f"Markdown summary saved to: {markdown_file}")
            print(f"{'='*60}")
            
            # Return exit code based on test results
            return 0 if summary['overall_status'] == 'passed' else 1
            
        except Exception as e:
            logger.error(f"Error during test execution: {e}")
            return 1

def main():
    """Main entry point"""
    runner = TestRunner()
    exit_code = runner.run_all_tests()
    sys.exit(exit_code)

if __name__ == '__main__':
    main()