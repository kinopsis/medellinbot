#!/usr/bin/env python3
"""
Implementation Validation Script
===============================

Simple validation script to test the core functionality without external dependencies.
This script validates that the new storage integration components are properly implemented.
"""

import sys
import os
import importlib.util
from datetime import datetime
from typing import Dict, List, Any

def validate_module_imports():
    """Validate that all required modules can be imported."""
    print("Validating module imports...")
    
    # Test basic module structure
    modules_to_test = [
        ("web_scraping.services.storage_service", "StorageService"),
        ("web_scraping.config.firestore_config", "FirestoreManager"),
        ("web_scraping.config.vector_search_config", "VectorSearchManager"),
        ("web_scraping.monitoring.monitor", "MonitoringService"),
        ("web_scraping.scrapers.secretaria_movilidad", "SecretariaMovilidadScraper"),
    ]
    
    results = {}
    for module_path, class_name in modules_to_test:
        try:
            # Convert module path to file path
            file_path = module_path.replace(".", "/") + ".py"
            if os.path.exists(file_path):
                spec = importlib.util.spec_from_file_location(module_path, file_path)
                if spec is None:
                    results[module_path] = False
                    print(f"❌ {module_path} - Spec not found")
                    continue
                module = importlib.util.module_from_spec(spec)
                if spec.loader is None:
                    results[module_path] = False
                    print(f"❌ {module_path} - Loader not found")
                    continue
                spec.loader.exec_module(module)
                
                # Check if class exists
                if hasattr(module, class_name):
                    results[module_path] = True
                    print(f"✅ {module_path}.{class_name} - OK")
                else:
                    results[module_path] = False
                    print(f"❌ {module_path}.{class_name} - Class not found")
            else:
                results[module_path] = False
                print(f"❌ {module_path} - File not found")
                
        except Exception as e:
            results[module_path] = False
            print(f"❌ {module_path} - Import error: {e}")
    
    return all(results.values())

def validate_storage_service_structure():
    """Validate StorageService class structure."""
    print("\nValidating StorageService structure...")
    
    try:
        file_path = "web_scraping/services/storage_service.py"
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for required methods
        required_methods = [
            "_store_in_firestore",
            "_store_in_vector_search",
            "search_similar_content",
            "_extract_text_for_embedding",
            "cleanup_expired_data"
        ]
        
        results = {}
        for method in required_methods:
            if f"def {method}" in content:
                results[method] = True
                print(f"✅ {method} - Found")
            else:
                results[method] = False
                print(f"❌ {method} - Not found")
        
        # Check for monitoring integration
        if "monitoring_service" in content:
            print("✅ Monitoring integration - Found")
            results["monitoring"] = True
        else:
            print("❌ Monitoring integration - Not found")
            results["monitoring"] = False
        
        return all(results.values())
        
    except Exception as e:
        print(f"❌ StorageService validation failed: {e}")
        return False

def validate_firestore_integration():
    """Validate Firestore integration."""
    print("\nValidating Firestore integration...")
    
    try:
        file_path = "web_scraping/config/firestore_config.py"
        with open(file_path, 'r') as f:
            content = f.read()
        
        required_elements = [
            "save_temporary_data",
            "save_cache_entry",
            "cleanup_expired_documents",
            "get_collection_ref"
        ]
        
        results = {}
        for element in required_elements:
            if f"def {element}" in content or f"async def {element}" in content:
                results[element] = True
                print(f"✅ {element} - Found")
            else:
                results[element] = False
                print(f"❌ {element} - Not found")
        
        return all(results.values())
        
    except Exception as e:
        print(f"❌ Firestore integration validation failed: {e}")
        return False

def validate_vector_search_integration():
    """Validate Vector Search integration."""
    print("\nValidating Vector Search integration...")
    
    try:
        file_path = "web_scraping/config/vector_search_config.py"
        with open(file_path, 'r') as f:
            content = f.read()
        
        required_elements = [
            "generate_embeddings",
            "upsert_embeddings",
            "search_similar_vectors"
        ]
        
        results = {}
        for element in required_elements:
            if f"def {element}" in content or f"async def {element}" in content:
                results[element] = True
                print(f"✅ {element} - Found")
            else:
                results[element] = False
                print(f"❌ {element} - Not found")
        
        return all(results.values())
        
    except Exception as e:
        print(f"❌ Vector Search integration validation failed: {e}")
        return False

def validate_monitoring_integration():
    """Validate monitoring integration."""
    print("\nValidating monitoring integration...")
    
    try:
        file_path = "web_scraping/monitoring/monitor.py"
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for Firestore metrics
        firestore_metrics = [
            "FIRESTORE_WRITE_COUNT",
            "FIRESTORE_READ_COUNT",
            "FIRESTORE_WRITE_DURATION",
            "FIRESTORE_READ_DURATION"
        ]
        
        vector_metrics = [
            "VECTOR_SEARCH_EMBEDDING_COUNT",
            "VECTOR_SEARCH_UPSERT_COUNT",
            "VECTOR_SEARCH_SEARCH_COUNT"
        ]
        
        results = {}
        
        # Check Firestore metrics
        for metric in firestore_metrics:
            if metric in content:
                results[metric] = True
            else:
                results[metric] = False
                print(f"❌ {metric} - Not found")
        
        # Check Vector metrics
        for metric in vector_metrics:
            if metric in content:
                results[metric] = True
                print(f"✅ {metric} - Found")
            else:
                results[metric] = False
                print(f"❌ {metric} - Not found")
        
        # Check monitoring methods
        monitoring_methods = [
            "record_firestore_write",
            "record_vector_embedding",
            "record_vector_upsert"
        ]
        
        for method in monitoring_methods:
            if f"def {method}" in content:
                results[method] = True
                print(f"✅ {method} - Found")
            else:
                results[method] = False
                print(f"❌ {method} - Not found")
        
        return all(results.values())
        
    except Exception as e:
        print(f"❌ Monitoring integration validation failed: {e}")
        return False

def validate_scraper_integration():
    """Validate scraper integration with storage service."""
    print("\nValidating scraper integration...")
    
    try:
        file_path = "web_scraping/scrapers/secretaria_movilidad.py"
        with open(file_path, 'r') as f:
            content = f.read()
        
        results = {}
        
        # Check for storage service import
        if "from web_scraping.services.storage_service import StorageService" in content:
            results["import"] = True
            print("✅ StorageService import - Found")
        else:
            results["import"] = False
            print("❌ StorageService import - Not found")
        
        # Check for storage service initialization
        if "self.storage_service = StorageService()" in content:
            results["initialization"] = True
            print("✅ StorageService initialization - Found")
        else:
            results["initialization"] = False
            print("❌ StorageService initialization - Not found")
        
        # Check for storage service usage in scrape method
        if "await self.storage_service.store_data" in content:
            results["usage"] = True
            print("✅ StorageService usage - Found")
        else:
            results["usage"] = False
            print("❌ StorageService usage - Not found")
        
        return all(results.values())
        
    except Exception as e:
        print(f"❌ Scraper integration validation failed: {e}")
        return False

def validate_test_files():
    """Validate test files exist and have proper structure."""
    print("\nValidating test files...")
    
    test_files = [
        "web_scraping/tests/comprehensive_storage_validation.py",
        "web_scraping/tests/test_storage_integration.py"
    ]
    
    results = {}
    for test_file in test_files:
        try:
            if os.path.exists(test_file):
                with open(test_file, 'r') as f:
                    content = f.read()
                
                # Check for basic test structure
                if "import pytest" in content and "def test_" in content:
                    results[test_file] = True
                    print(f"✅ {test_file} - Valid test structure")
                else:
                    results[test_file] = False
                    print(f"❌ {test_file} - Invalid test structure")
            else:
                results[test_file] = False
                print(f"❌ {test_file} - File not found")
                
        except Exception as e:
            results[test_file] = False
            print(f"❌ {test_file} - Error: {e}")
    
    return all(results.values())

def validate_documentation():
    """Validate documentation is updated."""
    print("\nValidating documentation...")
    
    try:
        file_path = "web_scraping/FIRESTORE_VECTOR_INTEGRATION.md"
        with open(file_path, 'r') as f:
            content = f.read()
        
        required_sections = [
            "## Monitoring and Alerting",
            "## Testing and Validation",
            "comprehensive_storage_validation.py"
        ]
        
        results = {}
        for section in required_sections:
            if section in content:
                results[section] = True
                print(f"✅ {section} - Found")
            else:
                results[section] = False
                print(f"❌ {section} - Not found")
        
        return all(results.values())
        
    except Exception as e:
        print(f"❌ Documentation validation failed: {e}")
        return False

def main():
    """Run all validation checks."""
    print("Starting MedellinBot Firestore and Vector Search Integration Validation")
    print("=" * 80)
    
    validation_functions = [
        ("Module Imports", validate_module_imports),
        ("Storage Service Structure", validate_storage_service_structure),
        ("Firestore Integration", validate_firestore_integration),
        ("Vector Search Integration", validate_vector_search_integration),
        ("Monitoring Integration", validate_monitoring_integration),
        ("Scraper Integration", validate_scraper_integration),
        ("Test Files", validate_test_files),
        ("Documentation", validate_documentation),
    ]
    
    results = {}
    for name, func in validation_functions:
        try:
            results[name] = func()
        except Exception as e:
            print(f"❌ {name} validation failed with exception: {e}")
            results[name] = False
    
    print("\n" + "=" * 80)
    print("📊 VALIDATION RESULTS")
    print("=" * 80)
    
    total_checks = len(results)
    passed_checks = sum(results.values())
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:25} : {status}")
    
    print("-" * 80)
    print(f"Total Checks: {total_checks}")
    print(f"Passed: {passed_checks}")
    print(f"Failed: {total_checks - passed_checks}")
    print(f"Success Rate: {(passed_checks/total_checks)*100:.1f}%")
    
    if all(results.values()):
        print("\n🎉 ALL VALIDATIONS PASSED! The implementation is ready.")
        return 0
    else:
        print("\n⚠️  SOME VALIDATIONS FAILED! Please review the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())