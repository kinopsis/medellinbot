"""
Test Runner
===========

Script to run all tests for the web scraping framework.
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_pytest(test_dir, verbose=False, coverage=False):
    """Run pytest with specified options."""
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
        
    if coverage:
        cmd.extend(["--cov=web_scraping", "--cov-report=html", "--cov-report=term"])
        
    cmd.append(test_dir)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def run_linting():
    """Run linting checks."""
    cmd = ["python", "-m", "flake8", "web_scraping/"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def run_type_checking():
    """Run type checking with mypy."""
    cmd = ["python", "-m", "mypy", "web_scraping/"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def print_section(title):
    """Print a section header."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_subsection(title):
    """Print a subsection header."""
    print(f"\n--- {title} ---")

def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run web scraping framework tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", "-c", action="store_true", help="Generate coverage report")
    parser.add_argument("--lint", "-l", action="store_true", help="Run linting checks")
    parser.add_argument("--types", "-t", action="store_true", help="Run type checking")
    parser.add_argument("--all", "-a", action="store_true", help="Run all checks")
    
    args = parser.parse_args()
    
    # If no specific options are given, run all checks
    if not any([args.verbose, args.coverage, args.lint, args.types, args.all]):
        args.all = True
        
    if args.all:
        args.verbose = True
        args.coverage = True
        args.lint = True
        args.types = True
    
    print_section("Web Scraping Framework Test Suite")
    
    all_passed = True
    
    # Run unit tests
    print_subsection("Running Unit Tests")
    test_dir = Path(__file__).parent
    test_passed, test_stdout, test_stderr = run_pytest(test_dir, args.verbose, args.coverage)
    
    if test_passed:
        print("✅ Unit tests passed")
    else:
        print("❌ Unit tests failed")
        all_passed = False
        
    if test_stdout:
        print(test_stdout)
    if test_stderr:
        print("STDERR:", test_stderr)
    
    # Run linting
    if args.lint:
        print_subsection("Running Linting Checks")
        lint_passed, lint_stdout, lint_stderr = run_linting()
        
        if lint_passed:
            print("✅ Linting checks passed")
        else:
            print("❌ Linting checks failed")
            all_passed = False
            
        if lint_stdout:
            print(lint_stdout)
        if lint_stderr:
            print("STDERR:", lint_stderr)
    
    # Run type checking
    if args.types:
        print_subsection("Running Type Checking")
        types_passed, types_stdout, types_stderr = run_type_checking()
        
        if types_passed:
            print("✅ Type checking passed")
        else:
            print("❌ Type checking failed")
            all_passed = False
            
        if types_stdout:
            print(types_stdout)
        if types_stderr:
            print("STDERR:", types_stderr)
    
    # Print summary
    print_section("Test Summary")
    
    if all_passed:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()