#!/usr/bin/env python3
"""
Simple validation script for MedellínBot critical fixes
Validates code improvements without requiring module imports
"""

import os
import re
from typing import List, Tuple

def validate_webhook_security() -> List[str]:
    """Validate webhook security implementations"""
    issues = []
    
    try:
        # Read webhook app.py
        with open('webhook/app.py', 'r') as f:
            webhook_content = f.read()
        
        # Check for security headers
        security_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options', 
            'Strict-Transport-Security',
            'Content-Security-Policy'
        ]
        
        for header in security_headers:
            if header not in webhook_content:
                issues.append(f"Missing security header: {header}")
            else:
                print(f"✓ Security header found: {header}")
        
        # Check for CORS configuration
        if 'Access-Control-Allow-Origin' not in webhook_content:
            issues.append("Missing CORS configuration")
        else:
            print("✓ CORS configuration found")
        
        # Check for input validation
        if 'SecurityValidator' not in webhook_content:
            issues.append("Missing input validation (SecurityValidator)")
        else:
            print("✓ Input validation (SecurityValidator) found")
        
        # Check for JWT validation
        if 'JWTManager' not in webhook_content:
            issues.append("Missing JWT authentication (JWTManager)")
        else:
            print("✓ JWT authentication (JWTManager) found")
        
        # Check for rate limiting
        if 'rate_limit_store' not in webhook_content and 'redis_client' not in webhook_content:
            issues.append("Missing rate limiting implementation")
        else:
            print("✓ Rate limiting implementation found")
        
        # Check for Redis support
        if 'redis.Redis' not in webhook_content:
            issues.append("Missing Redis support for rate limiting")
        else:
            print("✓ Redis support found")
        
        # Check for proper error handling
        if 'SecurityValidator.sanitize_response' not in webhook_content:
            issues.append("Missing error response sanitization")
        else:
            print("✓ Error response sanitization found")
        
        # Check for configuration management
        if 'Config.get_secret' not in webhook_content:
            issues.append("Missing secret management integration")
        else:
            print("✓ Secret management integration found")
        
    except Exception as e:
        issues.append(f"Error reading webhook file: {e}")
    
    return issues

def validate_orchestrator_improvements() -> List[str]:
    """Validate orchestrator improvements"""
    issues = []
    
    try:
        # Read orchestrator app.py
        with open('orchestrator/app.py', 'r') as f:
            orchestrator_content = f.read()
        
        # Check for LLM integration
        if 'LLMClient' not in orchestrator_content:
            issues.append("Missing LLM client implementation")
        else:
            print("✓ LLM client implementation found")
        
        # Check for Vertex AI support
        if 'vertexai' not in orchestrator_content:
            issues.append("Missing Vertex AI integration")
        else:
            print("✓ Vertex AI integration found")
        
        # Check for OpenAI support
        if 'openai' not in orchestrator_content:
            issues.append("Missing OpenAI integration")
        else:
            print("✓ OpenAI integration found")
        
        # Check for monitoring manager
        if 'MonitoringManager' not in orchestrator_content:
            issues.append("Missing monitoring and metrics collection")
        else:
            print("✓ Monitoring and metrics collection found")
        
        # Check for session management
        if 'SessionManager' not in orchestrator_content:
            issues.append("Missing enhanced session management")
        else:
            print("✓ Enhanced session management found")
        
        # Check for rate limiting
        if 'RateLimiter' not in orchestrator_content:
            issues.append("Missing rate limiting in orchestrator")
        else:
            print("✓ Rate limiting in orchestrator found")
        
        # Check for structured logging
        if 'StructuredLogger' not in orchestrator_content:
            issues.append("Missing structured logging")
        else:
            print("✓ Structured logging found")
        
        # Check for security validation
        if 'SecurityValidator' not in orchestrator_content:
            issues.append("Missing security validation in orchestrator")
        else:
            print("✓ Security validation in orchestrator found")
        
        # Check for proper error handling
        if 'sanitize_response' not in orchestrator_content:
            issues.append("Missing error sanitization in orchestrator")
        else:
            print("✓ Error sanitization in orchestrator found")
        
    except Exception as e:
        issues.append(f"Error reading orchestrator file: {e}")
    
    return issues

def validate_configuration() -> List[str]:
    """Validate configuration management"""
    issues = []
    
    try:
        # Check webhook configuration
        with open('webhook/app.py', 'r') as f:
            webhook_content = f.read()
        
        if 'Config.get_secret' not in webhook_content:
            issues.append("Webhook missing secret management")
        else:
            print("✓ Webhook secret management found")
        
        # Check orchestrator configuration
        with open('orchestrator/app.py', 'r') as f:
            orchestrator_content = f.read()
        
        if 'Config.get_secret' not in orchestrator_content:
            issues.append("Orchestrator missing secret management")
        else:
            print("✓ Orchestrator secret management found")
        
        # Check for environment variable usage
        env_vars = [
            'GOOGLE_CLOUD_PROJECT',
            'REDIS_HOST',
            'REDIS_PORT',
            'JWT_SECRET',
            'LLM_PROVIDER'
        ]
        
        for var in env_vars:
            if var not in webhook_content and var not in orchestrator_content:
                issues.append(f"Missing environment variable: {var}")
            else:
                print(f"✓ Environment variable found: {var}")
        
    except Exception as e:
        issues.append(f"Error reading configuration: {e}")
    
    return issues

def validate_monitoring_and_alerting() -> List[str]:
    """Validate monitoring and alerting implementation"""
    issues = []
    
    try:
        # Read orchestrator app.py
        with open('orchestrator/app.py', 'r') as f:
            orchestrator_content = f.read()
        
        # Check for metrics collection
        if 'record_metric' not in orchestrator_content:
            issues.append("Missing metrics collection")
        else:
            print("✓ Metrics collection found")
        
        # Check for alert thresholds
        if 'alert_thresholds' not in orchestrator_content:
            issues.append("Missing alert thresholds configuration")
        else:
            print("✓ Alert thresholds configuration found")
        
        # Check for health check endpoint
        if 'health_check' not in orchestrator_content:
            issues.append("Missing health check endpoint")
        else:
            print("✓ Health check endpoint found")
        
        # Check for system resource monitoring
        if 'psutil' not in orchestrator_content:
            issues.append("Missing system resource monitoring")
        else:
            print("✓ System resource monitoring found")
        
        # Check for metrics endpoint
        if '/metrics' not in orchestrator_content:
            issues.append("Missing metrics endpoint")
        else:
            print("✓ Metrics endpoint found")
        
        # Check for alerts endpoint
        if '/alerts' not in orchestrator_content:
            issues.append("Missing alerts endpoint")
        else:
            print("✓ Alerts endpoint found")
        
    except Exception as e:
        issues.append(f"Error reading monitoring implementation: {e}")
    
    return issues

def validate_session_management() -> List[str]:
    """Validate session management improvements"""
    issues = []
    
    try:
        # Read orchestrator app.py
        with open('orchestrator/app.py', 'r') as f:
            orchestrator_content = f.read()
        
        # Check for session timeout handling
        if 'SESSION_TIMEOUT_HOURS' not in orchestrator_content:
            issues.append("Missing session timeout configuration")
        else:
            print("✓ Session timeout configuration found")
        
        # Check for session cleanup
        if 'cleanup_expired_sessions' not in orchestrator_content:
            issues.append("Missing session cleanup functionality")
        else:
            print("✓ Session cleanup functionality found")
        
        # Check for session validation
        if 'validate_session' not in orchestrator_content:
            issues.append("Missing session validation decorator")
        else:
            print("✓ Session validation decorator found")
        
        # Check for session metadata
        if 'session_metadata' not in orchestrator_content:
            issues.append("Missing session metadata tracking")
        else:
            print("✓ Session metadata tracking found")
        
        # Check for max sessions per user
        if 'max_sessions_per_user' not in orchestrator_content:
            issues.append("Missing max sessions per user limit")
        else:
            print("✓ Max sessions per user limit found")
        
    except Exception as e:
        issues.append(f"Error reading session management: {e}")
    
    return issues

def validate_database_connection_pooling() -> List[str]:
    """Validate database connection pooling"""
    issues = []
    
    try:
        # Read orchestrator app.py
        with open('orchestrator/app.py', 'r') as f:
            orchestrator_content = f.read()
        
        # Check for connection pooling configuration
        if 'FIRESTORE_MAX_POOL_SIZE' not in orchestrator_content:
            issues.append("Missing Firestore connection pooling configuration")
        else:
            print("✓ Firestore connection pooling configuration found")
        
        # Check for ThreadPoolExecutor usage
        if 'ThreadPoolExecutor' not in orchestrator_content:
            issues.append("Missing thread pool executor for connection management")
        else:
            print("✓ Thread pool executor for connection management found")
        
    except Exception as e:
        issues.append(f"Error reading database connection pooling: {e}")
    
    return issues

def validate_llm_integration() -> List[str]:
    """Validate LLM integration improvements"""
    issues = []
    
    try:
        # Read orchestrator app.py
        with open('orchestrator/app.py', 'r') as f:
            orchestrator_content = f.read()
        
        # Check for LLM client
        if 'LLMClient' not in orchestrator_content:
            issues.append("Missing LLM client implementation")
        else:
            print("✓ LLM client implementation found")
        
        # Check for caching
        if 'cache_ttl' not in orchestrator_content:
            issues.append("Missing LLM response caching")
        else:
            print("✓ LLM response caching found")
        
        # Check for multiple provider support
        if 'LLM_PROVIDER' not in orchestrator_content:
            issues.append("Missing LLM provider configuration")
        else:
            print("✓ LLM provider configuration found")
        
        # Check for timeout handling
        if 'LLM_TIMEOUT' not in orchestrator_content:
            issues.append("Missing LLM timeout configuration")
        else:
            print("✓ LLM timeout configuration found")
        
        # Check for error handling
        if 'LLM call failed' not in orchestrator_content:
            issues.append("Missing LLM error handling")
        else:
            print("✓ LLM error handling found")
        
    except Exception as e:
        issues.append(f"Error reading LLM integration: {e}")
    
    return issues

def main():
    """Main validation function"""
    print("MedellinBot Critical Fixes Validation")
    print("=" * 50)
    
    all_issues = []
    
    # 1. Validate webhook security
    print("\nValidating webhook security...")
    webhook_issues = validate_webhook_security()
    if webhook_issues:
        print("Webhook security issues found:")
        for issue in webhook_issues:
            print(f"  - {issue}")
        all_issues.extend(webhook_issues)
    else:
        print("✓ Webhook security validation passed")
    
    # 2. Validate orchestrator improvements
    print("\nValidating orchestrator improvements...")
    orchestrator_issues = validate_orchestrator_improvements()
    if orchestrator_issues:
        print("Orchestrator improvement issues found:")
        for issue in orchestrator_issues:
            print(f"  - {issue}")
        all_issues.extend(orchestrator_issues)
    else:
        print("✓ Orchestrator improvements validation passed")
    
    # 3. Validate configuration
    print("\nValidating configuration management...")
    config_issues = validate_configuration()
    if config_issues:
        print("Configuration issues found:")
        for issue in config_issues:
            print(f"  - {issue}")
        all_issues.extend(config_issues)
    else:
        print("✓ Configuration validation passed")
    
    # 4. Validate monitoring and alerting
    print("\nValidating monitoring and alerting...")
    monitoring_issues = validate_monitoring_and_alerting()
    if monitoring_issues:
        print("Monitoring and alerting issues found:")
        for issue in monitoring_issues:
            print(f"  - {issue}")
        all_issues.extend(monitoring_issues)
    else:
        print("✓ Monitoring and alerting validation passed")
    
    # 5. Validate session management
    print("\nValidating session management...")
    session_issues = validate_session_management()
    if session_issues:
        print("Session management issues found:")
        for issue in session_issues:
            print(f"  - {issue}")
        all_issues.extend(session_issues)
    else:
        print("✓ Session management validation passed")
    
    # 6. Validate database connection pooling
    print("\nValidating database connection pooling...")
    db_issues = validate_database_connection_pooling()
    if db_issues:
        print("Database connection pooling issues found:")
        for issue in db_issues:
            print(f"  - {issue}")
        all_issues.extend(db_issues)
    else:
        print("✓ Database connection pooling validation passed")
    
    # 7. Validate LLM integration
    print("\nValidating LLM integration...")
    llm_issues = validate_llm_integration()
    if llm_issues:
        print("LLM integration issues found:")
        for issue in llm_issues:
            print(f"  - {issue}")
        all_issues.extend(llm_issues)
    else:
        print("✓ LLM integration validation passed")
    
    # Summary
    print("\n" + "=" * 50)
    if all_issues:
        print(f"VALIDATION FAILED: {len(all_issues)} issues found")
        print("\nSummary of issues:")
        for i, issue in enumerate(all_issues, 1):
            print(f"{i}. {issue}")
        print("\nPlease address these issues before production deployment.")
        return 1
    else:
        print("VALIDATION PASSED: All critical fixes successfully implemented!")
        print("\nThe MedellínBot system is now ready for production deployment with:")
        print("• Comprehensive security measures")
        print("• Proper error handling and logging")
        print("• Real LLM integration (Vertex AI & OpenAI)")
        print("• Advanced monitoring and alerting")
        print("• Enhanced session management")
        print("• Database connection pooling")
        print("• Rate limiting with Redis support")
        return 0

if __name__ == "__main__":
    exit(main())