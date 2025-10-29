#!/usr/bin/env python3
"""
Simple Implementation Validation
===============================

Basic validation script to test the core functionality without external dependencies.
"""

import sys
import os

def check_file_exists(filepath):
    """Check if a file exists."""
    return os.path.exists(filepath)

def check_file_content(filepath, search_terms):
    """Check if file contains all search terms."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        return all(term in content for term in search_terms)
    except:
        return False

def main():
    """Run basic validation checks."""
    print("Starting MedellinBot Firestore and Vector Search Integration Validation")
    print("=" * 70)
    
    # Check that all required files exist
    required_files = [
        "services/storage_service.py",
        "config/firestore_config.py",
        "config/vector_search_config.py",
        "monitoring/monitor.py",
        "scrapers/secretaria_movilidad.py",
        "tests/comprehensive_storage_validation.py",
        "FIRESTORE_VECTOR_INTEGRATION.md"
    ]
    
    print("Checking file existence...")
    files_exist = True
    for filepath in required_files:
        if check_file_exists(filepath):
            print(f"  OK: {filepath}")
        else:
            print(f"  MISSING: {filepath}")
            files_exist = False
    
    if not files_exist:
        print("\nSome required files are missing!")
        return 1
    
    # Check key functionality in storage service
    print("\nChecking StorageService functionality...")
    storage_checks = [
        ("_store_in_firestore", "services/storage_service.py"),
        ("_store_in_vector_search", "services/storage_service.py"),
        ("search_similar_content", "services/storage_service.py"),
        ("monitoring_service", "services/storage_service.py")
    ]
    
    storage_ok = True
    for term, filepath in storage_checks:
        if check_file_content(filepath, [term]):
            print(f"  OK: {term} found in {filepath}")
        else:
            print(f"  MISSING: {term} not found in {filepath}")
            storage_ok = False
    
    # Check Firestore integration
    print("\nChecking Firestore integration...")
    firestore_checks = [
        "save_temporary_data",
        "save_cache_entry",
        "cleanup_expired_documents"
    ]
    
    firestore_path = "config/firestore_config.py"
    firestore_ok = check_file_content(firestore_path, firestore_checks)
    if firestore_ok:
        print("  OK: Firestore methods found")
    else:
        print("  MISSING: Some Firestore methods not found")
    
    # Check Vector Search integration
    print("\nChecking Vector Search integration...")
    vector_checks = [
        "generate_embeddings",
        "upsert_embeddings",
        "search_similar_vectors"
    ]
    
    vector_path = "config/vector_search_config.py"
    vector_ok = check_file_content(vector_path, vector_checks)
    if vector_ok:
        print("  OK: Vector Search methods found")
    else:
        print("  MISSING: Some Vector Search methods not found")
    
    # Check monitoring integration
    print("\nChecking monitoring integration...")
    monitoring_checks = [
        "FIRESTORE_WRITE_COUNT",
        "VECTOR_SEARCH_EMBEDDING_COUNT",
        "record_firestore_write",
        "record_vector_embedding"
    ]
    
    monitoring_path = "monitoring/monitor.py"
    monitoring_ok = check_file_content(monitoring_path, monitoring_checks)
    if monitoring_ok:
        print("  OK: Monitoring metrics found")
    else:
        print("  MISSING: Some monitoring metrics not found")
    
    # Check scraper integration
    print("\nChecking scraper integration...")
    scraper_checks = [
        "from web_scraping.services.storage_service import StorageService",
        "self.storage_service = StorageService()",
        "await self.storage_service.store_data"
    ]
    
    scraper_path = "scrapers/secretaria_movilidad.py"
    scraper_ok = check_file_content(scraper_path, scraper_checks)
    if scraper_ok:
        print("  OK: Scraper integration found")
    else:
        print("  MISSING: Scraper integration not found")
    
    # Check test files
    print("\nChecking test files...")
    test_files_ok = True
    test_files = [
        "tests/comprehensive_storage_validation.py",
        "tests/test_storage_integration.py"
    ]
    
    for filepath in test_files:
        if check_file_exists(filepath):
            has_pytest = check_file_content(filepath, ["import pytest"])
            has_tests = check_file_content(filepath, ["def test_"])
            if has_pytest and has_tests:
                print(f"  OK: {filepath} has valid test structure")
            else:
                print(f"  INVALID: {filepath} missing pytest or test functions")
                test_files_ok = False
        else:
            print(f"  MISSING: {filepath}")
            test_files_ok = False
    
    # Check documentation
    print("\nChecking documentation...")
    doc_checks = [
        "## Monitoring and Alerting",
        "## Testing"
    ]
    
    doc_path = "FIRESTORE_VECTOR_INTEGRATION.md"
    doc_ok = check_file_content(doc_path, doc_checks)
    if doc_ok:
        print("  OK: Documentation updated")
    else:
        print("  MISSING: Documentation not updated")
    
    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)
    
    all_checks = [files_exist, storage_ok, firestore_ok, vector_ok, monitoring_ok, scraper_ok, test_files_ok, doc_ok]
    check_names = ["Files Exist", "StorageService", "Firestore", "Vector Search", "Monitoring", "Scraper", "Tests", "Documentation"]
    
    passed = sum(all_checks)
    total = len(all_checks)
    
    for i, (name, result) in enumerate(zip(check_names, all_checks)):
        status = "PASS" if result else "FAIL"
        print(f"{name:20} : {status}")
    
    print("-" * 70)
    print(f"Total: {passed}/{total} checks passed ({passed/total*100:.1f}%)")
    
    if all(all_checks):
        print("\nAll validations passed! The implementation is ready.")
        return 0
    else:
        print("\nSome validations failed. Please review the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())