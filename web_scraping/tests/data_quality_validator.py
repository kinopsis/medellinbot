#!/usr/bin/env python3
"""
Data Quality and Completeness Validation Script
===============================================

This script validates the quality and completeness of scraped data against
the technical specifications and business requirements.

Author: MedellínBot Development Team
Version: 1.0
Date: October 29, 2025
"""

import sys
import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_scraping.core.database import db_manager
from web_scraping.services.data_processor import DataProcessor, DataQuality
from web_scraping.config.settings import config
from web_scraping.monitoring.monitor import monitoring_service


@dataclass
class ValidationResult:
    """Result of data validation."""
    source: str
    data_type: str
    total_records: int
    valid_records: int
    invalid_records: int
    completeness_score: float
    accuracy_score: float
    consistency_score: float
    freshness_score: float
    overall_quality: DataQuality
    issues: List[str]
    recommendations: List[str]


@dataclass
class QualityMetrics:
    """Quality metrics for a data source."""
    source: str
    data_type: str
    record_count: int
    field_completeness: Dict[str, float]
    data_accuracy: Dict[str, float]
    temporal_freshness: float
    consistency_score: float
    error_rate: float
    duplicate_rate: float
    last_updated: datetime


class DataQualityValidator:
    """Validates data quality and completeness."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.processor = DataProcessor()
        
        # Quality thresholds from technical specifications
        self.quality_thresholds = {
            'completeness_min': 0.95,  # 95% completeness required
            'accuracy_min': 0.90,      # 90% accuracy required
            'consistency_min': 0.85,   # 85% consistency required
            'freshness_max_hours': 24, # Data should be < 24 hours old
            'error_rate_max': 0.05,    # < 5% error rate
            'duplicate_rate_max': 0.02 # < 2% duplicate rate
        }
        
        # Required fields by data type
        self.required_fields = {
            'news': ['title', 'content', 'extracted_at'],
            'tramite': ['title', 'description', 'extracted_at'],
            'contact': ['source_url', 'extracted_at'],
            'traffic_alert': ['title', 'content', 'extracted_at'],
            'pico_placa': ['title', 'content', 'extracted_at'],
            'vial_closure': ['title', 'content', 'extracted_at'],
            'program': ['title', 'description', 'extracted_at']
        }
        
    async def validate_source_data(self, source: str, data_type: str, 
                                 lookback_hours: int = 24) -> ValidationResult:
        """Validate data quality for a specific source and data type."""
        
        self.logger.info(f"Validating data quality for {source}/{data_type}")
        
        try:
            # Get recent data from database
            cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
            raw_data = self._get_recent_data(source, data_type, cutoff_time)
            
            if not raw_data:
                return ValidationResult(
                    source=source,
                    data_type=data_type,
                    total_records=0,
                    valid_records=0,
                    invalid_records=0,
                    completeness_score=0.0,
                    accuracy_score=0.0,
                    consistency_score=0.0,
                    freshness_score=0.0,
                    overall_quality=DataQuality.INVALID,
                    issues=["No data found for the specified time period"],
                    recommendations=["Check if scraping is working properly for this source"]
                )
            
            # Calculate quality metrics
            completeness_score = self._calculate_completeness(raw_data, data_type)
            accuracy_score = self._calculate_accuracy(raw_data, data_type)
            consistency_score = self._calculate_consistency(raw_data)
            freshness_score = self._calculate_freshness(raw_data)
            
            # Determine valid vs invalid records
            valid_records, invalid_records, validation_issues = self._validate_records(raw_data, data_type)
            
            # Calculate overall quality
            overall_quality = self._determine_overall_quality(
                completeness_score, accuracy_score, consistency_score, freshness_score
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                completeness_score, accuracy_score, consistency_score, freshness_score, validation_issues
            )
            
            return ValidationResult(
                source=source,
                data_type=data_type,
                total_records=len(raw_data),
                valid_records=valid_records,
                invalid_records=invalid_records,
                completeness_score=completeness_score,
                accuracy_score=accuracy_score,
                consistency_score=consistency_score,
                freshness_score=freshness_score,
                overall_quality=overall_quality,
                issues=validation_issues,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Error validating {source}/{data_type}: {e}")
            return ValidationResult(
                source=source,
                data_type=data_type,
                total_records=0,
                valid_records=0,
                invalid_records=0,
                completeness_score=0.0,
                accuracy_score=0.0,
                consistency_score=0.0,
                freshness_score=0.0,
                overall_quality=DataQuality.INVALID,
                issues=[f"Validation failed: {str(e)}"],
                recommendations=["Check data source connectivity and format"]
            )
    
    def _get_recent_data(self, source: str, data_type: str, 
                        cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Get recent data from database."""
        try:
            # This would need to be implemented based on your database query capabilities
            # For now, return mock data for testing
            return [
                {
                    "id": 1,
                    "source": source,
                    "data_type": data_type,
                    "content": {
                        "type": data_type,
                        "title": "Test News",
                        "content": "Test content",
                        "extracted_at": datetime.now().isoformat()
                    },
                    "created_at": datetime.now(),
                    "is_valid": True
                }
            ]
        except Exception as e:
            self.logger.error(f"Error getting data from database: {e}")
            return []
    
    def _calculate_completeness(self, data: List[Dict[str, Any]], data_type: str) -> float:
        """Calculate data completeness score."""
        if not data:
            return 0.0
            
        required_fields = self.required_fields.get(data_type, ['type', 'extracted_at'])
        
        total_fields = len(data) * len(required_fields)
        present_fields = 0
        
        for record in data:
            content = record.get('content', {})
            for field in required_fields:
                if field in content and content[field] not in [None, '', []]:
                    present_fields += 1
        
        return present_fields / total_fields if total_fields > 0 else 0.0
    
    def _calculate_accuracy(self, data: List[Dict[str, Any]], data_type: str) -> float:
        """Calculate data accuracy score."""
        if not data:
            return 0.0
            
        # Basic accuracy checks
        valid_records = 0
        total_records = len(data)
        
        for record in data:
            content = record.get('content', {})
            
            # Check required fields
            required_fields = self.required_fields.get(data_type, ['type', 'extracted_at'])
            has_required = all(field in content and content[field] for field in required_fields)
            
            # Check data format validity
            has_valid_format = self._validate_data_format(content, data_type)
            
            if has_required and has_valid_format:
                valid_records += 1
        
        return valid_records / total_records if total_records > 0 else 0.0
    
    def _validate_data_format(self, content: Dict[str, Any], data_type: str) -> bool:
        """Validate data format for specific data type."""
        try:
            if data_type == 'news':
                # News should have title and content
                return content.get('title') and content.get('content')
            elif data_type == 'tramite':
                # Trámite should have title and description
                return content.get('title') and content.get('description')
            elif data_type == 'contact':
                # Contact should have source_url
                return content.get('source_url')
            elif data_type in ['traffic_alert', 'pico_placa', 'vial_closure', 'program']:
                # These should have title and content
                return content.get('title') and content.get('content')
            else:
                # Default validation
                return content.get('title') or content.get('content')
                
        except Exception:
            return False
    
    def _calculate_consistency(self, data: List[Dict[str, Any]]) -> float:
        """Calculate data consistency score."""
        if len(data) < 2:
            return 1.0  # Single record is always consistent
            
        consistent_records = 0
        total_comparisons = 0
        
        # Compare adjacent records for consistency
        for i in range(len(data) - 1):
            record1 = data[i].get('content', {})
            record2 = data[i + 1].get('content', {})
            
            # Check if similar records have consistent data
            if self._are_records_consistent(record1, record2):
                consistent_records += 1
            total_comparisons += 1
        
        return consistent_records / total_comparisons if total_comparisons > 0 else 1.0
    
    def _are_records_consistent(self, record1: Dict[str, Any], record2: Dict[str, Any]) -> bool:
        """Check if two records are consistent with each other."""
        # Basic consistency check - records with same title should have similar content
        title1 = record1.get('title', '')
        title2 = record2.get('title', '')
        
        if title1 and title2 and title1 == title2:
            content1 = record1.get('content', '')
            content2 = record2.get('content', '')
            return content1 == content2
        
        return True  # Different titles are considered consistent
    
    def _calculate_freshness(self, data: List[Dict[str, Any]]) -> float:
        """Calculate data freshness score."""
        if not data:
            return 0.0
            
        now = datetime.now()
        fresh_records = 0
        total_records = len(data)
        
        for record in data:
            extracted_at = record.get('content', {}).get('extracted_at')
            if extracted_at:
                try:
                    extracted_time = datetime.fromisoformat(extracted_at.replace('Z', '+00:00'))
                    age_hours = (now - extracted_time).total_seconds() / 3600
                    
                    # Consider data fresh if extracted within threshold
                    if age_hours <= self.quality_thresholds['freshness_max_hours']:
                        fresh_records += 1
                except (ValueError, TypeError):
                    continue
        
        return fresh_records / total_records if total_records > 0 else 0.0
    
    def _validate_records(self, data: List[Dict[str, Any]], data_type: str) -> Tuple[int, int, List[str]]:
        """Validate individual records and identify issues."""
        valid_records = 0
        invalid_records = 0
        issues = []
        
        for i, record in enumerate(data):
            content = record.get('content', {})
            
            # Check for missing required fields
            required_fields = self.required_fields.get(data_type, ['type', 'extracted_at'])
            missing_fields = [field for field in required_fields if field not in content or not content[field]]
            
            if missing_fields:
                issues.append(f"Record {i}: Missing required fields: {', '.join(missing_fields)}")
                invalid_records += 1
            else:
                # Check data format
                if self._validate_data_format(content, data_type):
                    valid_records += 1
                else:
                    issues.append(f"Record {i}: Invalid data format")
                    invalid_records += 1
        
        return valid_records, invalid_records, issues
    
    def _determine_overall_quality(self, completeness: float, accuracy: float, 
                                 consistency: float, freshness: float) -> DataQuality:
        """Determine overall data quality based on individual scores."""
        
        # Weighted average of quality metrics
        weights = {
            'completeness': 0.3,
            'accuracy': 0.3,
            'consistency': 0.2,
            'freshness': 0.2
        }
        
        overall_score = (
            completeness * weights['completeness'] +
            accuracy * weights['accuracy'] +
            consistency * weights['consistency'] +
            freshness * weights['freshness']
        )
        
        # Determine quality level
        if overall_score >= 0.9:
            return DataQuality.HIGH
        elif overall_score >= 0.7:
            return DataQuality.MEDIUM
        elif overall_score >= 0.5:
            return DataQuality.LOW
        else:
            return DataQuality.INVALID
    
    def _generate_recommendations(self, completeness: float, accuracy: float, 
                                consistency: float, freshness: float, 
                                issues: List[str]) -> List[str]:
        """Generate recommendations based on quality issues."""
        recommendations = []
        
        thresholds = self.quality_thresholds
        
        if completeness < thresholds['completeness_min']:
            recommendations.append(
                f"Improve data completeness: Current {completeness:.2%}, "
                f"Target {thresholds['completeness_min']:.2%}"
            )
        
        if accuracy < thresholds['accuracy_min']:
            recommendations.append(
                f"Improve data accuracy: Current {accuracy:.2%}, "
                f"Target {thresholds['accuracy_min']:.2%}"
            )
        
        if consistency < thresholds['consistency_min']:
            recommendations.append(
                f"Improve data consistency: Current {consistency:.2%}, "
                f"Target {thresholds['consistency_min']:.2%}"
            )
        
        if freshness < 0.8:  # 80% freshness threshold
            recommendations.append("Improve data freshness - consider more frequent scraping")
        
        if issues:
            recommendations.append(f"Address {len(issues)} data validation issues")
        
        if not recommendations:
            recommendations.append("Data quality meets all requirements")
        
        return recommendations


class CompletenessChecker:
    """Checks data completeness against source coverage requirements."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Expected data sources and types from technical plan
        self.expected_sources = {
            'alcaldia_medellin': ['news', 'tramite', 'contact', 'program'],
            'secretaria_movilidad': ['traffic_alert', 'pico_placa', 'vial_closure', 'contact'],
            'epm': ['service', 'contact'],
            'metro_medellin': ['service', 'schedule', 'contact'],
            'emvarias': ['service', 'contact']
        }
        
        # Critical data types that must be available
        self.critical_data_types = ['news', 'tramite', 'contact', 'traffic_alert', 'pico_placa']
        
    async def check_source_coverage(self) -> Dict[str, Any]:
        """Check coverage of all expected data sources."""
        
        coverage_report = {
            'total_expected_sources': len(self.expected_sources),
            'available_sources': 0,
            'missing_sources': [],
            'source_details': {},
            'critical_data_availability': {}
        }
        
        for source, expected_types in self.expected_sources.items():
            source_status = await self._check_source_availability(source, expected_types)
            coverage_report['source_details'][source] = source_status
            
            if source_status['available']:
                coverage_report['available_sources'] += 1
            else:
                coverage_report['missing_sources'].append(source)
        
        # Check critical data availability
        coverage_report['critical_data_availability'] = await self._check_critical_data_availability()
        
        return coverage_report
    
    async def _check_source_availability(self, source: str, expected_types: List[str]) -> Dict[str, Any]:
        """Check availability of a specific source."""
        
        source_status = {
            'source': source,
            'expected_data_types': expected_types,
            'available_data_types': [],
            'missing_data_types': [],
            'available': False,
            'last_updated': None
        }
        
        # Check each data type
        for data_type in expected_types:
            try:
                # This would check actual database for data availability
                # For now, mock the check
                has_data = await self._has_data_for_type(source, data_type)
                
                if has_data:
                    source_status['available_data_types'].append(data_type)
                else:
                    source_status['missing_data_types'].append(data_type)
                    
            except Exception as e:
                self.logger.error(f"Error checking {source}/{data_type}: {e}")
                source_status['missing_data_types'].append(data_type)
        
        source_status['available'] = len(source_status['missing_data_types']) == 0
        
        return source_status
    
    async def _has_data_for_type(self, source: str, data_type: str) -> bool:
        """Check if data exists for a specific source and type."""
        # Mock implementation - would check actual database
        # Return True for some sources to simulate partial availability
        available_combinations = [
            ('alcaldia_medellin', 'news'),
            ('alcaldia_medellin', 'tramite'),
            ('alcaldia_medellin', 'contact'),
            ('secretaria_movilidad', 'traffic_alert'),
            ('secretaria_movilidad', 'pico_placa'),
        ]
        
        return (source, data_type) in available_combinations
    
    async def _check_critical_data_availability(self) -> Dict[str, Any]:
        """Check availability of critical data types."""
        
        critical_status = {}
        
        for data_type in self.critical_data_types:
            try:
                # Check if critical data is available from any source
                available_sources = await self._find_sources_for_data_type(data_type)
                
                critical_status[data_type] = {
                    'available': len(available_sources) > 0,
                    'sources': available_sources,
                    'priority': self._get_data_type_priority(data_type)
                }
                
            except Exception as e:
                self.logger.error(f"Error checking critical data {data_type}: {e}")
                critical_status[data_type] = {
                    'available': False,
                    'sources': [],
                    'priority': self._get_data_type_priority(data_type),
                    'error': str(e)
                }
        
        return critical_status
    
    async def _find_sources_for_data_type(self, data_type: str) -> List[str]:
        """Find sources that provide a specific data type."""
        
        # Mock implementation
        data_type_sources = {
            'news': ['alcaldia_medellin'],
            'tramite': ['alcaldia_medellin'],
            'contact': ['alcaldia_medellin', 'secretaria_movilidad'],
            'traffic_alert': ['secretaria_movilidad'],
            'pico_placa': ['secretaria_movilidad']
        }
        
        return data_type_sources.get(data_type, [])
    
    def _get_data_type_priority(self, data_type: str) -> str:
        """Get priority level for a data type."""
        priorities = {
            'news': 'high',
            'tramite': 'high',
            'contact': 'medium',
            'traffic_alert': 'high',
            'pico_placa': 'high'
        }
        
        return priorities.get(data_type, 'low')


async def run_data_quality_validation():
    """Run comprehensive data quality validation."""
    
    print("MedellínBot Web Scraping - Data Quality Validation")
    print("=" * 60)
    
    validator = DataQualityValidator()
    completeness_checker = CompletenessChecker()
    
    # Validate individual sources
    print("\n🔍 Validating Individual Sources...")
    print("-" * 40)
    
    sources_to_validate = [
        ('alcaldia_medellin', 'news'),
        ('alcaldia_medellin', 'tramite'),
        ('secretaria_movilidad', 'traffic_alert'),
        ('secretaria_movilidad', 'pico_placa')
    ]
    
    all_results = []
    
    for source, data_type in sources_to_validate:
        result = await validator.validate_source_data(source, data_type)
        all_results.append(result)
        
        print(f"\n📊 {source}/{data_type}:")
        print(f"   Overall Quality: {result.overall_quality.value.upper()}")
        print(f"   Completeness: {result.completeness_score:.2%}")
        print(f"   Accuracy: {result.accuracy_score:.2%}")
        print(f"   Consistency: {result.consistency_score:.2%}")
        print(f"   Freshness: {result.freshness_score:.2%}")
        print(f"   Valid Records: {result.valid_records}/{result.total_records}")
        
        if result.issues:
            print(f"   Issues: {len(result.issues)} found")
            for issue in result.issues[:3]:  # Show first 3 issues
                print(f"     - {issue}")
        
        if result.recommendations:
            print(f"   Recommendations: {len(result.recommendations)}")
            for rec in result.recommendations[:2]:  # Show first 2 recommendations
                print(f"     - {rec}")
    
    # Check source coverage
    print(f"\n🌐 Checking Source Coverage...")
    print("-" * 40)
    
    coverage_report = await completeness_checker.check_source_coverage()
    
    print(f"Sources Available: {coverage_report['available_sources']}/{coverage_report['total_expected_sources']}")
    print(f"Missing Sources: {len(coverage_report['missing_sources'])}")
    
    if coverage_report['missing_sources']:
        print("Missing Sources:")
        for source in coverage_report['missing_sources'][:3]:
            print(f"  - {source}")
    
    # Critical data availability
    print(f"\n🚨 Critical Data Availability:")
    unavailable_critical = []
    
    for data_type, status in coverage_report['critical_data_availability'].items():
        availability = "✅ Available" if status['available'] else "❌ Unavailable"
        sources = ", ".join(status['sources']) if status['sources'] else "None"
        print(f"  {data_type}: {availability} ({sources})")
        
        if not status['available']:
            unavailable_critical.append(data_type)
    
    # Generate summary
    print(f"\n📈 Quality Summary:")
    high_quality_count = sum(1 for r in all_results if r.overall_quality == DataQuality.HIGH)
    medium_quality_count = sum(1 for r in all_results if r.overall_quality == DataQuality.MEDIUM)
    low_quality_count = sum(1 for r in all_results if r.overall_quality == DataQuality.LOW)
    invalid_count = sum(1 for r in all_results if r.overall_quality == DataQuality.INVALID)
    
    print(f"  High Quality: {high_quality_count}")
    print(f"  Medium Quality: {medium_quality_count}")
    print(f"  Low Quality: {low_quality_count}")
    print(f"  Invalid: {invalid_count}")
    
    # Recommendations
    print(f"\n💡 Key Recommendations:")
    
    if unavailable_critical:
        print(f"  • Implement missing critical data sources: {', '.join(unavailable_critical)}")
    
    low_quality_sources = [f"{r.source}/{r.data_type}" for r in all_results if r.overall_quality in [DataQuality.LOW, DataQuality.INVALID]]
    if low_quality_sources:
        print(f"  • Improve quality for sources: {', '.join(low_quality_sources)}")
    
    # Overall assessment
    total_quality_score = sum(r.completeness_score + r.accuracy_score + r.consistency_score + r.freshness_score 
                             for r in all_results) / (len(all_results) * 4) if all_results else 0
    
    print(f"\n🎯 Overall Data Quality Score: {total_quality_score:.2%}")
    
    if total_quality_score >= 0.8:
        print("✅ Data quality meets requirements")
        return True
    else:
        print("❌ Data quality needs improvement")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_data_quality_validation())
    sys.exit(0 if success else 1)