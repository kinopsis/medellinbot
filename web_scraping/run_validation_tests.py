#!/usr/bin/env python3
"""
Simplified Validation Test Runner
================================

This script runs validation tests for the web scraping implementation
without requiring full database dependencies.
"""

import sys
import os
import asyncio
import json
import logging
import unittest
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import importlib.util

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

@dataclass
class ValidationResult:
    """Individual test result."""
    test_name: str
    passed: bool
    score: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    critical_issues: int
    high_priority_issues: int
    recommendations: List[str]
    action_items: List[str]
    execution_time: float
    timestamp: datetime

@dataclass
class ComprehensiveValidationResult:
    """Comprehensive validation result."""
    timestamp: datetime
    total_execution_time: float
    validation_results: List[ValidationResult]
    overall_score: float
    overall_status: str
    critical_issues_summary: List[str]
    recommendations_summary: List[str]
    action_items_summary: List[str]

class SimplifiedValidationRunner:
    """Runs simplified validation tests."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.results: List[ValidationResult] = []
        
        # Test configurations for available tests
        self.available_tests = [
            {
                'name': 'Base Scraper Tests',
                'file': 'tests/test_base_scraper.py',
                'critical': True
            },
            {
                'name': 'Data Processor Tests', 
                'file': 'tests/test_data_processor.py',
                'critical': True
            },
            {
                'name': 'Integration Tests',
                'file': 'tests/integration_tests.py',
                'critical': False
            },
            {
                'name': 'Security Compliance Tests',
                'file': 'tests/security_compliance_checks.py',
                'critical': True
            }
        ]
        
    def run_unit_tests(self) -> ValidationResult:
        """Run unit tests using unittest."""
        print("Running Unit Tests...")
        
        start_time = datetime.now()
        
        # Discover and run tests
        test_loader = unittest.TestLoader()
        test_suite = test_loader.discover('tests', pattern='test_*.py')
        
        # Run tests
        test_runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
        result = test_runner.run(test_suite)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Calculate metrics
        total_tests = result.testsRun
        passed_tests = total_tests - len(result.failures) - len(result.errors)
        failed_tests = len(result.failures) + len(result.errors)
        critical_issues = len(result.errors)  # Errors are more critical than failures
        high_priority_issues = len(result.failures)
        
        # Calculate score (70% for passed tests, 30% for critical issues)
        if total_tests > 0:
            test_score = (passed_tests / total_tests) * 70
            issue_penalty = critical_issues * 10 + high_priority_issues * 5
            score = max(0, test_score - issue_penalty)
        else:
            score = 0
            
        # Generate recommendations
        recommendations = []
        if critical_issues > 0:
            recommendations.append(f"Fix {critical_issues} critical errors in unit tests")
        if high_priority_issues > 0:
            recommendations.append(f"Address {high_priority_issues} test failures")
        if score < 70:
            recommendations.append("Improve overall test coverage and fix failing tests")
            
        # Generate action items
        action_items = []
        if critical_issues > 0:
            action_items.append("Resolve critical test errors before deployment")
        if high_priority_issues > 0:
            action_items.append("Fix failing tests to improve code quality")
            
        validation_result = ValidationResult(
            test_name="Unit Tests",
            passed=score >= 70,
            score=score,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            critical_issues=critical_issues,
            high_priority_issues=high_priority_issues,
            recommendations=recommendations,
            action_items=action_items,
            execution_time=execution_time,
            timestamp=start_time
        )
        
        self.results.append(validation_result)
        
        status_text = "PASS" if validation_result.passed else "FAIL"
        print(f"  {status_text} Completed in {execution_time:.2f}s - Score: {score:.1f}%")
        
        return validation_result
    
    def validate_code_quality(self) -> ValidationResult:
        """Validate code quality metrics."""
        print("Running Code Quality Validation...")
        
        start_time = datetime.now()
        
        # Check for basic code quality indicators
        issues = []
        recommendations = []
        action_items = []
        
        # Check if core files exist
        core_files = [
            'core/base_scraper.py',
            'core/database.py', 
            'services/data_processor.py',
            'main.py'
        ]
        
        missing_files = []
        for file_path in core_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
                issues.append(f"Missing core file: {file_path}")
                
        if missing_files:
            recommendations.append(f"Create missing core files: {', '.join(missing_files)}")
            action_items.append("Implement missing core functionality")
            
        # Check for test files
        test_files = [
            'tests/test_base_scraper.py',
            'tests/test_data_processor.py'
        ]
        
        missing_tests = []
        for test_file in test_files:
            if not os.path.exists(test_file):
                missing_tests.append(test_file)
                issues.append(f"Missing test file: {test_file}")
                
        if missing_tests:
            recommendations.append(f"Create missing test files: {', '.join(missing_tests)}")
            action_items.append("Implement comprehensive test coverage")
            
        # Check for documentation
        if not os.path.exists('README.md'):
            issues.append("Missing README.md")
            recommendations.append("Create project documentation")
            action_items.append("Document project structure and usage")
            
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Calculate score
        total_checks = len(core_files) + len(test_files) + 1  # +1 for README
        passed_checks = (len(core_files) - len(missing_files) + 
                        len(test_files) - len(missing_tests) + 
                        (1 if os.path.exists('README.md') else 0))
        
        score = (passed_checks / total_checks) * 100
        
        validation_result = ValidationResult(
            test_name="Code Quality",
            passed=score >= 80,
            score=score,
            total_tests=total_checks,
            passed_tests=passed_checks,
            failed_tests=len(issues),
            critical_issues=len([i for i in issues if 'core file' in i]),
            high_priority_issues=len([i for i in issues if 'test file' in i]),
            recommendations=recommendations,
            action_items=action_items,
            execution_time=execution_time,
            timestamp=start_time
        )
        
        self.results.append(validation_result)
        
        status_text = "PASS" if validation_result.passed else "FAIL"
        print(f"  {status_text} Completed in {execution_time:.2f}s - Score: {score:.1f}%")
        
        return validation_result
    
    def validate_implementation_plan(self) -> ValidationResult:
        """Validate implementation against the technical plan."""
        print("Running Implementation Plan Validation...")
        
        start_time = datetime.now()
        
        # Read the implementation plan
        plan_file = '../web_scraping_implementation_plan.md'
        if not os.path.exists(plan_file):
            plan_file = 'web_scraping_implementation_plan.md'
            
        issues = []
        recommendations = []
        action_items = []
        
        if os.path.exists(plan_file):
            with open(plan_file, 'r', encoding='utf-8') as f:
                plan_content = f.read()
                
            # Check for key components in the plan
            required_sections = [
                '## 🎯 Technical Requirements',
                '## 🏗️ Architecture Overview', 
                '## 📋 Implementation Roadmap',
                '## 📊 Performance Requirements',
                '## 🔒 Security and Compliance'
            ]
            
            missing_sections = []
            for section in required_sections:
                if section not in plan_content:
                    missing_sections.append(section)
                    issues.append(f"Missing plan section: {section}")
                    
            if missing_sections:
                recommendations.append(f"Add missing plan sections: {', '.join(missing_sections)}")
                action_items.append("Complete technical implementation plan")
        else:
            issues.append("Missing implementation plan document")
            recommendations.append("Create comprehensive implementation plan")
            action_items.append("Document technical requirements and architecture")
            
        # Check for code files mentioned in plan
        code_files_mentioned = []
        if os.path.exists(plan_file):
            with open(plan_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '```python' in line or '.py' in line:
                        # Extract potential file names
                        if '.py' in line:
                            parts = line.split('.py')
                            for part in parts[:-1]:
                                if 'web_scraping/' in part:
                                    file_name = part.split('web_scraping/')[-1] + '.py'
                                    if file_name not in code_files_mentioned:
                                        code_files_mentioned.append(file_name)
                                        
        # Validate that mentioned files exist
        missing_mentioned_files = []
        for file_name in code_files_mentioned:
            if not os.path.exists(file_name):
                missing_mentioned_files.append(file_name)
                issues.append(f"Mentioned but missing file: {file_name}")
                
        if missing_mentioned_files:
            recommendations.append(f"Create files mentioned in plan: {', '.join(missing_mentioned_files)}")
            action_items.append("Implement missing components from plan")
            
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Calculate score based on completeness
        total_items = len(required_sections) + len(code_files_mentioned)
        if total_items > 0:
            passed_items = (len(required_sections) - len(missing_sections) + 
                           len(code_files_mentioned) - len(missing_mentioned_files))
            score = (passed_items / total_items) * 100
        else:
            score = 50  # Base score if no plan found
            
        validation_result = ValidationResult(
            test_name="Implementation Plan",
            passed=score >= 70,
            score=score,
            total_tests=total_items,
            passed_tests=passed_items if total_items > 0 else 0,
            failed_tests=len(issues),
            critical_issues=len([i for i in issues if 'Missing implementation plan' in i]),
            high_priority_issues=len([i for i in issues if 'core file' in i]),
            recommendations=recommendations,
            action_items=action_items,
            execution_time=execution_time,
            timestamp=start_time
        )
        
        self.results.append(validation_result)
        
        status_text = "PASS" if validation_result.passed else "FAIL"
        print(f"  {status_text} Completed in {execution_time:.2f}s - Score: {score:.1f}%")
        
        return validation_result
    
    def generate_comprehensive_result(self) -> ComprehensiveValidationResult:
        """Generate comprehensive validation result."""
        
        # Calculate overall metrics
        total_tests = sum(r.total_tests for r in self.results)
        total_passed = sum(r.passed_tests for r in self.results)
        total_failed = sum(r.failed_tests for r in self.results)
        critical_issues = sum(r.critical_issues for r in self.results)
        high_priority_issues = sum(r.high_priority_issues for r in self.results)
        
        # Calculate overall score
        if total_tests > 0:
            overall_score = (total_passed / total_tests * 70)  # 70% weight for test results
            # Subtract penalties for critical and high priority issues
            issue_penalty = critical_issues * 10 + high_priority_issues * 5
            overall_score = max(0, overall_score - issue_penalty)
        else:
            overall_score = 0
            
        # Determine overall status
        if critical_issues == 0 and overall_score >= 70:
            overall_status = "PASS"
        elif critical_issues <= 2 and overall_score >= 50:
            overall_status = "PARTIAL"
        else:
            overall_status = "FAIL"
            
        # Collect all recommendations and action items
        all_recommendations = []
        all_action_items = []
        critical_issues_summary = []
        
        for result in self.results:
            all_recommendations.extend(result.recommendations)
            all_action_items.extend(result.action_items)
            
            if result.critical_issues > 0:
                critical_issues_summary.append(f"{result.test_name}: {result.critical_issues} critical issues")
                
        return ComprehensiveValidationResult(
            timestamp=datetime.now(),
            total_execution_time=sum(r.execution_time for r in self.results),
            validation_results=self.results,
            overall_score=overall_score,
            overall_status=overall_status,
            critical_issues_summary=critical_issues_summary,
            recommendations_summary=list(set(all_recommendations)),  # Remove duplicates
            action_items_summary=list(set(all_action_items)),  # Remove duplicates
        )
    
    def print_comprehensive_summary(self, result: ComprehensiveValidationResult):
        """Print comprehensive validation summary."""
        
        print("\n" + "=" * 70)
        print("COMPREHENSIVE VALIDATION SUMMARY")
        print("=" * 70)
        
        print(f"Overall Status: {result.overall_status}")
        print(f"Overall Score: {result.overall_score:.1f}%")
        print(f"Total Execution Time: {result.total_execution_time:.2f}s")
        print()
        
        # Print individual test results
        print("Individual Test Results:")
        for test_result in result.validation_results:
            status_text = "PASS" if test_result.passed else "FAIL"
            print(f"  {status_text} {test_result.test_name}")
            print(f"    Score: {test_result.score:.1f}% | Passed: {test_result.passed_tests}/{test_result.total_tests}")
            print(f"    Critical Issues: {test_result.critical_issues} | High Priority: {test_result.high_priority_issues}")
            print(f"    Execution Time: {test_result.execution_time:.2f}s")
            print()
            
        # Print critical issues
        if result.critical_issues_summary:
            print("🚨 Critical Issues:")
            for issue in result.critical_issues_summary:
                print(f"  • {issue}")
            print()
            
        # Print recommendations
        if result.recommendations_summary:
            print("💡 Top Recommendations:")
            for i, recommendation in enumerate(result.recommendations_summary[:5], 1):  # Show top 5
                print(f"  {i}. {recommendation}")
            print()
            
        # Print action items
        if result.action_items_summary:
            print("🎯 Priority Action Items:")
            for i, action_item in enumerate(result.action_items_summary[:5], 1):  # Show top 5
                print(f"  {i}. {action_item}")
            print()
            
        # Final assessment
        if result.overall_status == "PASS":
            print("🎉 COMPREHENSIVE VALIDATION PASSED!")
            print("All critical requirements are met. The implementation is ready for deployment.")
        elif result.overall_status == "PARTIAL":
            print("⚠️ COMPREHENSIVE VALIDATION PARTIAL")
            print("Some issues need to be addressed before deployment.")
        else:
            print("❌ COMPREHENSIVE VALIDATION FAILED")
            print("Critical issues must be resolved before deployment.")
    
    def generate_final_reports(self, result: ComprehensiveValidationResult):
        """Generate final validation reports."""
        
        print("\nGenerating Final Reports...")
        
        # Create reports directory
        reports_dir = "validation_reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Generate JSON report
        json_report = {
            'validation_summary': {
                'timestamp': result.timestamp.isoformat(),
                'overall_status': result.overall_status,
                'overall_score': result.overall_score,
                'total_execution_time': result.total_execution_time,
                'critical_issues_count': len(result.critical_issues_summary)
            },
            'test_results': [
                {
                    'test_name': r.test_name,
                    'passed': r.passed,
                    'score': r.score,
                    'total_tests': r.total_tests,
                    'passed_tests': r.passed_tests,
                    'failed_tests': r.failed_tests,
                    'critical_issues': r.critical_issues,
                    'high_priority_issues': r.high_priority_issues,
                    'execution_time': r.execution_time
                }
                for r in result.validation_results
            ],
            'critical_issues': result.critical_issues_summary,
            'recommendations': result.recommendations_summary,
            'action_items': result.action_items_summary
        }
        
        json_path = os.path.join(reports_dir, f'comprehensive_validation_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)
            
        print(f"  ✅ JSON Report: {json_path}")
        
        # Generate Markdown report
        markdown_content = f"""
# Comprehensive Validation Report

*Generated on: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*

## Executive Summary

**Overall Status:** {result.overall_status}
**Overall Score:** {result.overall_score:.1f}%
**Total Execution Time:** {result.total_execution_time:.2f}s
**Critical Issues:** {len(result.critical_issues_summary)}

## Test Results

"""
        
        for test_result in result.validation_results:
            status_prefix = "PASS" if test_result.passed else "FAIL"
            markdown_content += f"""
### {status_prefix} {test_result.test_name}

- **Score:** {test_result.score:.1f}%
- **Tests:** {test_result.passed_tests}/{test_result.total_tests} passed
- **Critical Issues:** {test_result.critical_issues}
- **High Priority Issues:** {test_result.high_priority_issues}
- **Execution Time:** {test_result.execution_time:.2f}s

"""
            
        if result.critical_issues_summary:
            markdown_content += "## Critical Issues\n\n"
            for issue in result.critical_issues_summary:
                markdown_content += f"- {issue}\n"
            markdown_content += "\n"
            
        if result.recommendations_summary:
            markdown_content += "## Recommendations\n\n"
            for i, recommendation in enumerate(result.recommendations_summary[:10], 1):  # Show top 10
                markdown_content += f"{i}. {recommendation}\n"
            markdown_content += "\n"
            
        if result.action_items_summary:
            markdown_content += "## Action Items\n\n"
            for i, action_item in enumerate(result.action_items_summary[:10], 1):  # Show top 10
                markdown_content += f"{i}. {action_item}\n"
            markdown_content += "\n"
            
        markdown_content += f"""
## Final Assessment

{result.overall_status} - {'All critical requirements are met. The implementation is ready for deployment.' if result.overall_status == 'PASS' else 'Some issues need to be addressed before deployment.' if result.overall_status == 'PARTIAL' else 'Critical issues must be resolved before deployment.'}

---

*Generated by MedellínBot Simplified Validation Framework*
"""
        
        markdown_path = os.path.join(reports_dir, f'comprehensive_validation_{timestamp}.md')
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
        print(f"  Markdown Report: {markdown_path}")
        
        # Generate executive summary
        executive_summary = f"""
COMPREHENSIVE VALIDATION EXECUTIVE SUMMARY
=================================================
 
Status: {result.overall_status}
Score: {result.overall_score:.1f}%
Execution Time: {result.total_execution_time:.2f}s

CRITICAL METRICS:
- Total Tests: {sum(r.total_tests for r in result.validation_results)}
- Passed Tests: {sum(r.passed_tests for r in result.validation_results)}
- Critical Issues: {len(result.critical_issues_summary)}
- High Priority Issues: {sum(r.high_priority_issues for r in result.validation_results)}

TOP RECOMMENDATIONS:
"""
        
        for i, recommendation in enumerate(result.recommendations_summary[:3], 1):  # Show top 3
            executive_summary += f"{i}. {recommendation}\n"
            
        executive_summary += f"""

IMMEDIATE ACTION REQUIRED:
{result.overall_status} - {'No immediate action required.' if result.overall_status == 'PASS' else 'Address critical issues before deployment.' if result.overall_status == 'PARTIAL' else 'Resolve all critical issues before deployment.'}

Report generated: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        summary_path = os.path.join(reports_dir, f'executive_summary_{timestamp}.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(executive_summary)
            
        print(f"  Executive Summary: {summary_path}")
        
        print(f"\nAll reports generated in: {reports_dir}")
    
    def run_comprehensive_validation(self) -> ComprehensiveValidationResult:
        """Run comprehensive validation tests."""
        
        print("Simplified Validation Test Suite")
        print("=" * 70)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Run all validation tests
        self.run_unit_tests()
        self.validate_code_quality()
        self.validate_implementation_plan()
        
        # Generate comprehensive results
        comprehensive_result = self.generate_comprehensive_result()
        
        # Print comprehensive summary
        self.print_comprehensive_summary(comprehensive_result)
        
        # Generate final reports
        self.generate_final_reports(comprehensive_result)
        
        return comprehensive_result

def run_comprehensive_validation():
    """Run comprehensive validation tests."""
    
    runner = SimplifiedValidationRunner()
    result = runner.run_comprehensive_validation()
    
    # Return exit code based on overall status
    return result.overall_status == "PASS"

if __name__ == "__main__":
    success = run_comprehensive_validation()
    sys.exit(0 if success else 1)