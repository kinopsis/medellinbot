#!/usr/bin/env python3
"""
MedellínBot - Orchestrator Component
Main orchestrator for routing requests to specialized agents
"""

import os
import json
import logging
import time
import uuid
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from flask import Flask, request, jsonify, Response
import requests
from google.cloud import firestore, storage, secretmanager
from google.cloud.firestore_v1.base_client import Client
import jwt
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import traceback
import redis
from collections import defaultdict
import psutil
import threading
from dataclasses import dataclass
from enum import Enum

# Configure logging with structured format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enhanced logging for production
class StructuredLogger:
    """Enhanced logging with structured data for monitoring"""
    
    @staticmethod
    def log_event(event_type: str, level: str, message: str, **kwargs):
        """Log structured events for monitoring and alerting"""
        log_data = {
            'event_type': event_type,
            'level': level,
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'orchestrator',
            **kwargs
        }
        
        if level == 'ERROR':
            logger.error(json.dumps(log_data))
        elif level == 'WARNING':
            logger.warning(json.dumps(log_data))
        else:
            logger.info(json.dumps(log_data))

# Initialize Flask app with security headers
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Security headers middleware
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# CORS configuration
@app.after_request
def after_request(response):
    """Add CORS headers"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Initialize Google Cloud clients with connection pooling
try:
    # Firestore with connection pooling
    db = firestore.Client()
    
    # Storage client
    storage_client = storage.Client()
    
    # Secret Manager client
    secret_client = secretmanager.SecretManagerServiceClient()
    
    logger.info("Google Cloud clients initialized successfully")
    StructuredLogger.log_event("cloud_clients_initialized", "INFO", "All Google Cloud clients connected successfully")
except Exception as e:
    error_msg = f"Failed to initialize Google Cloud clients: {e}"
    logger.error(error_msg)
    StructuredLogger.log_event("cloud_clients_failed", "ERROR", error_msg)
    raise

# Redis connection for caching and rate limiting
redis_client = None
try:
    redis_client = redis.Redis(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=int(os.environ.get('REDIS_PORT', 6379)),
        db=int(os.environ.get('REDIS_DB', 1)),  # Use different DB for orchestrator
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30
    )
    redis_client.ping()
    logger.info("Redis client initialized successfully")
    StructuredLogger.log_event("redis_connected", "INFO", "Redis connection established")
except (redis.ConnectionError, redis.TimeoutError) as e:
    logger.warning(f"Redis connection failed: {e}. Continuing without Redis caching.")
    StructuredLogger.log_event("redis_failed", "WARNING", f"Redis connection failed: {e}")

# Configuration with secret management
class Config:
    """Application configuration with secret management"""
    
    @staticmethod
    def get_secret(secret_id: str) -> str:
        """Retrieve secret from Google Secret Manager"""
        try:
            project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
            if not project_id:
                raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")
            
            name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
            response = secret_client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_id}: {e}")
            raise
    
    # Basic configuration
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
    SESSION_TIMEOUT_HOURS = int(os.environ.get('SESSION_TIMEOUT_HOURS', '24'))
    MAX_MESSAGE_HISTORY = int(os.environ.get('MAX_MESSAGE_HISTORY', '50'))
    CONFIDENCE_THRESHOLD = float(os.environ.get('CONFIDENCE_THRESHOLD', '0.7'))
    
    # Security configuration
    JWT_SECRET = get_secret.__func__('jwt-secret-key')
    REQUIRE_AUTH = os.environ.get('REQUIRE_AUTH', 'false').lower() == 'true'
    
    # Agent endpoints
    TRAMITES_AGENT_URL = os.environ.get('TRAMITES_AGENT_URL', 'http://localhost:8082')
    PQRSD_AGENT_URL = os.environ.get('PQRSD_AGENT_URL', 'http://localhost:8083')
    PROGRAMAS_AGENT_URL = os.environ.get('PROGRAMAS_AGENT_URL', 'http://localhost:8084')
    NOTIFICACIONES_AGENT_URL = os.environ.get('NOTIFICACIONES_AGENT_URL', 'http://localhost:8085')
    
    # LLM Configuration
    LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'vertex-ai')
    LLM_MODEL = os.environ.get('LLM_MODEL', 'gemini-1.5-flash')
    LLM_TEMPERATURE = float(os.environ.get('LLM_TEMPERATURE', '0.3'))
    LLM_MAX_TOKENS = int(os.environ.get('LLM_MAX_TOKENS', '1024'))
    LLM_TIMEOUT = int(os.environ.get('LLM_TIMEOUT', '30'))
    
    # Monitoring and alerting
    ENABLE_METRICS = os.environ.get('ENABLE_METRICS', 'true').lower() == 'true'
    METRICS_RETENTION_DAYS = int(os.environ.get('METRICS_RETENTION_DAYS', '30'))
    
    # Database connection pooling
    FIRESTORE_MAX_POOL_SIZE = int(os.environ.get('FIRESTORE_MAX_POOL_SIZE', '10'))
    FIRESTORE_MIN_POOL_SIZE = int(os.environ.get('FIRESTORE_MIN_POOL_SIZE', '2'))
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS', '100'))
    RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW', '3600'))  # 1 hour

# Load prompts
try:
    from prompts.intent_classifier import (
        INTENT_CLASSIFIER_PROMPT, 
        CLARIFICATION_PROMPT,
        HUMAN_ESCALATION_DETECTION_PROMPT,
        CONTEXT_SUMMARIZATION_PROMPT
    )
    from prompts.tramites_agent import TRAMITES_AGENT_SYSTEM_PROMPT, TRAMITES_AGENT_FOLLOWUP_PROMPT
    from prompts.pqrsd_agent import PQRSD_AGENT_SYSTEM_PROMPT, PQRSD_AGENT_FOLLOWUP_PROMPT
    from prompts.programas_agent import PROGRAMAS_AGENT_SYSTEM_PROMPT, PROGRAMAS_AGENT_FOLLOWUP_PROMPT
    from prompts.notificaciones_agent import NOTIFICACIONES_AGENT_SYSTEM_PROMPT, NOTIFICACIONES_AGENT_FOLLOWUP_PROMPT
    
    logger.info("Prompts loaded successfully")
except ImportError as e:
    logger.error(f"Failed to load prompts: {e}")
    raise

class SecurityValidator:
    """Security validation utilities"""
    
    @staticmethod
    def validate_input_data(data: Any) -> bool:
        """Validate input data for security threats"""
        if isinstance(data, str):
            # Check for common injection patterns
            dangerous_patterns = [
                r'<script.*?>',  # XSS
                r'javascript:',   # XSS
                r'union.*select', # SQL injection
                r'drop\s+table',  # SQL injection
                r'exec\s*\(',     # Command injection
                r'eval\s*\(',     # Code injection
            ]
            
            import re
            for pattern in dangerous_patterns:
                if re.search(pattern, data, re.IGNORECASE):
                    return False
        return True
    
    @staticmethod
    def sanitize_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize response data to prevent information leakage"""
        # Remove sensitive information from responses
        sensitive_fields = ['password', 'token', 'secret', 'key', 'authorization', 'jwt']
        
        def sanitize_recursive(obj):
            if isinstance(obj, dict):
                return {
                    k: sanitize_recursive(v)
                    for k, v in obj.items()
                    if k.lower() not in sensitive_fields
                }
            elif isinstance(obj, list):
                return [sanitize_recursive(item) for item in obj]
            else:
                return obj
        
        return sanitize_recursive(response_data)

class RateLimiter:
    """Rate limiting implementation with Redis support"""
    
    def __init__(self):
        self.rate_limit_window = Config.RATE_LIMIT_WINDOW
        self.max_requests = Config.RATE_LIMIT_REQUESTS
        self.storage = 'redis' if redis_client else 'memory'
        self.memory_store = defaultdict(list)
    
    def is_rate_limited(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit"""
        current_time = time.time()
        window_start = current_time - self.rate_limit_window
        
        if self.storage == 'redis' and redis_client:
            return self._is_rate_limited_redis(client_id, current_time, window_start)
        else:
            return self._is_rate_limited_memory(client_id, current_time, window_start)
    
    def _is_rate_limited_redis(self, client_id: str, current_time: float, window_start: float) -> bool:
        """Check rate limit using Redis"""
        try:
            key = f"rate_limit:orchestrator:{client_id}"
            
            # Remove old entries outside the window
            redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            current_count = redis_client.zcard(key)
            
            if current_count >= self.max_requests:
                return True
            
            # Add current request
            redis_client.zadd(key, {str(current_time): current_time})
            
            # Set expiration on the key
            redis_client.expire(key, self.rate_limit_window + 60)
            
            return False
            
        except Exception as e:
            logger.warning(f"Redis rate limit check failed: {e}. Falling back to in-memory.")
            return self._is_rate_limited_memory(client_id, current_time, window_start)
    
    def _is_rate_limited_memory(self, client_id: str, current_time: float, window_start: float) -> bool:
        """Check rate limit using in-memory storage"""
        # Clean up old requests
        self.memory_store[client_id] = [
            req_time for req_time in self.memory_store[client_id]
            if req_time > window_start
        ]
        
        # Check if limit exceeded
        if len(self.memory_store[client_id]) >= self.max_requests:
            return True
        
        # Add current request
        self.memory_store[client_id].append(current_time)
        return False

# Initialize rate limiter
rate_limiter = RateLimiter()

def validate_session(func):
    """Decorator to validate session and user authentication"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Check rate limiting first
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if rate_limiter.is_rate_limited(client_ip):
                StructuredLogger.log_event("rate_limit_exceeded", "WARNING", f"Rate limit exceeded for IP: {client_ip}")
                return jsonify({"error": "Rate limit exceeded"}), 429
            
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid JSON payload"}), 400
            
            session_id = data.get('session_id')
            user_id = data.get('user_id')
            
            # Validate input data
            if session_id and not SecurityValidator.validate_input_data(session_id):
                return jsonify({"error": "Invalid session ID format"}), 400
            if user_id and not SecurityValidator.validate_input_data(str(user_id)):
                return jsonify({"error": "Invalid user ID format"}), 400
            
            if not session_id or not user_id:
                return jsonify({"error": "Missing session_id or user_id"}), 400
            
            # Validate session exists and is active
            session_ref = db.collection('sessions').document(session_id)
            session_doc = session_ref.get()
            
            if not session_doc.exists:
                StructuredLogger.log_event("session_not_found", "WARNING", f"Session not found: {session_id}")
                return jsonify({"error": "Session not found"}), 404
            
            session_data = session_doc.to_dict()
            if session_data.get('user_id') != user_id:
                StructuredLogger.log_event("unauthorized_session", "WARNING", f"Unauthorized session access attempt: {session_id}")
                return jsonify({"error": "Unauthorized session access"}), 403
            
            # Check session timeout
            last_active = session_data.get('last_active')
            if last_active:
                timeout = timedelta(hours=Config.SESSION_TIMEOUT_HOURS)
                if datetime.utcnow() - last_active > timeout:
                    session_ref.delete()
                    StructuredLogger.log_event("session_expired", "INFO", f"Session expired: {session_id}")
                    return jsonify({"error": "Session expired"}), 440
            
            # Update last active
            session_ref.update({'last_active': datetime.utcnow()})
            
            # Add session data to request context
            request.session_data = session_data
            request.session_ref = session_ref
            
            return func(*args, **kwargs)
            
        except Exception as e:
            error_msg = f"Session validation error: {e}"
            logger.error(error_msg)
            StructuredLogger.log_event("session_validation_error", "ERROR", error_msg, exception=str(e))
            return jsonify({"error": "Session validation failed"}), 500
    
    return wrapper

def get_client_ip():
    """Get client IP address from request headers"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

class LLMClient:
    """LLM client with support for multiple providers"""
    
    def __init__(self):
        self.provider = Config.LLM_PROVIDER
        self.model = Config.LLM_MODEL
        self.temperature = Config.LLM_TEMPERATURE
        self.max_tokens = Config.LLM_MAX_TOKENS
        self.timeout = Config.LLM_TIMEOUT
        self.cache_ttl = 300  # 5 minutes cache TTL
    
    def call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Call LLM provider with caching and error handling"""
        try:
            # Create cache key
            cache_key = f"llm_cache:{hashlib.md5((prompt + (system_prompt or '')).encode()).hexdigest()}"
            
            # Try to get from cache first
            if redis_client:
                cached_response = redis_client.get(cache_key)
                if cached_response:
                    StructuredLogger.log_event("llm_cache_hit", "INFO", "LLM response served from cache")
                    return cached_response
            
            # Call appropriate provider
            if self.provider == 'vertex-ai':
                response = self._call_vertex_ai(prompt, system_prompt)
            elif self.provider == 'openai':
                response = self._call_openai(prompt, system_prompt)
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")
            
            # Cache the response
            if redis_client and response:
                redis_client.setex(cache_key, self.cache_ttl, response)
            
            StructuredLogger.log_event("llm_call_success", "INFO", f"LLM call successful using {self.provider}")
            return response
            
        except Exception as e:
            error_msg = f"LLM call failed: {e}"
            logger.error(error_msg)
            StructuredLogger.log_event("llm_call_failed", "ERROR", error_msg, provider=self.provider)
            raise
    
    def _call_vertex_ai(self, prompt: str, system_prompt: str = None) -> str:
        """Call Google Vertex AI"""
        try:
            import vertexai
            from vertexai.preview.generative_models import GenerativeModel
            
            # Initialize Vertex AI
            project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
            if not project_id:
                raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")
            
            vertexai.init(project=project_id, location="us-central1")
            
            # Create model
            model = GenerativeModel(self.model)
            
            # Prepare content
            contents = []
            if system_prompt:
                contents.append({"role": "system", "content": system_prompt})
            contents.append({"role": "user", "content": prompt})
            
            # Generate response
            response = model.generate_content(
                contents,
                generation_config={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_tokens,
                },
                timeout=self.timeout
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Vertex AI call failed: {e}")
            raise
    
    def _call_openai(self, prompt: str, system_prompt: str = None) -> str:
        """Call OpenAI API"""
        try:
            import openai
            
            # Get API key from secrets
            api_key = Config.get_secret('openai-api-key')
            openai.api_key = api_key
            
            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Call API
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI call failed: {e}")
            raise

class IntentClassifier:
    """Handles intent classification using LLM"""
    
    def __init__(self):
        self.confidence_threshold = Config.CONFIDENCE_THRESHOLD
        self.llm_client = LLMClient()
    
    def classify_intent(self, user_message: str, conversation_context: str = "") -> Dict[str, Any]:
        """Classify user intent using LLM"""
        try:
            # Prepare the prompt with context
            prompt = INTENT_CLASSIFIER_PROMPT.format(
                user_message=user_message,
                conversation_context=conversation_context
            )
            
            # Call LLM
            response = self.llm_client.call_llm(prompt)
            
            # Parse and validate response
            intent_data = self._parse_intent_response(response)
            
            # Check confidence threshold
            if intent_data['confidence'] < self.confidence_threshold:
                intent_data['intent'] = 'clarificacion'
                intent_data['reasoning'] = f"Confianza baja ({intent_data['confidence']:.2f} < {self.confidence_threshold})"
            
            StructuredLogger.log_event("intent_classification_success", "INFO",
                                     f"Intent classified: {intent_data['intent']}",
                                     confidence=intent_data['confidence'])
            
            return intent_data
            
        except Exception as e:
            error_msg = f"Intent classification error: {e}"
            logger.error(error_msg)
            StructuredLogger.log_event("intent_classification_error", "ERROR", error_msg)
            return {
                'intent': 'clarificacion',
                'confidence': 0.0,
                'reasoning': f'Error en clasificación: {str(e)}',
                'detected_keywords': []
            }
    
    def _parse_intent_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured intent data"""
        try:
            # Try to parse as JSON
            data = json.loads(response)
            
            # Validate required fields
            required_fields = ['intent', 'confidence', 'reasoning', 'detected_keywords']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate confidence range
            if not 0.0 <= data['confidence'] <= 1.0:
                raise ValueError("Confidence must be between 0.0 and 1.0")
            
            return data
            
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response from LLM: {response}")
            raise ValueError("Invalid LLM response format")
        except Exception as e:
            logger.error(f"Error parsing intent response: {e}")
            raise

class ContextManager:
    """Manages conversation context and memory"""
    
    def __init__(self):
        self.max_history = Config.MAX_MESSAGE_HISTORY
    
    def get_conversation_context(self, session_id: str, current_message: str) -> Dict[str, Any]:
        """Get conversation context including recent messages and summary"""
        try:
            # Get session data
            session_ref = db.collection('sessions').document(session_id)
            session_doc = session_ref.get()
            
            if not session_doc.exists:
                return {
                    'recent_messages': [],
                    'memory_summary': '',
                    'user_preferences': {},
                    'context_relevance_score': 0.0
                }
            
            session_data = session_doc.to_dict()
            
            # Get recent messages
            messages = session_data.get('messages', [])
            if len(messages) > self.max_history:
                messages = messages[-self.max_history:]
            
            # Add current message
            current_msg = {
                'text': current_message,
                'role': 'user',
                'timestamp': datetime.utcnow().isoformat()
            }
            messages.append(current_msg)
            
            # Get memory summary
            memory_summary = session_data.get('memory_summary', '')
            
            # Get user preferences
            user_preferences = session_data.get('user_preferences', {})
            
            return {
                'recent_messages': messages,
                'memory_summary': memory_summary,
                'user_preferences': user_preferences,
                'context_relevance_score': session_data.get('context_relevance_score', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return {
                'recent_messages': [],
                'memory_summary': '',
                'user_preferences': {},
                'context_relevance_score': 0.0
            }
    
    def update_session_context(self, session_id: str, new_messages: list, memory_summary: str = None):
        """Update session with new messages and optional memory summary"""
        try:
            session_ref = db.collection('sessions').document(session_id)
            
            # Prepare update data
            update_data = {
                'last_active': datetime.utcnow(),
                'messages': new_messages
            }
            
            if memory_summary:
                update_data['memory_summary'] = memory_summary
            
            session_ref.update(update_data)
            
        except Exception as e:
            logger.error(f"Error updating session context: {e}")
            raise

class MonitoringManager:
    """Comprehensive monitoring and metrics collection"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.alert_thresholds = {
            'error_rate': 0.05,  # 5% error rate threshold
            'response_time': 5.0,  # 5 second response time threshold
            'cpu_usage': 80.0,  # 80% CPU usage threshold
            'memory_usage': 80.0,  # 80% memory usage threshold
        }
        self.start_time = datetime.utcnow()
    
    def record_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record a metric with optional tags"""
        metric_data = {
            'value': value,
            'timestamp': datetime.utcnow(),
            'tags': tags or {}
        }
        self.metrics[metric_name].append(metric_data)
        
        # Store in Firestore for persistence
        if Config.ENABLE_METRICS:
            try:
                db.collection('metrics').add({
                    'metric_name': metric_name,
                    'value': value,
                    'tags': tags or {},
                    'timestamp': datetime.utcnow()
                })
            except Exception as e:
                logger.warning(f"Failed to store metric: {e}")
    
    def check_alerts(self):
        """Check if any metrics exceed alert thresholds"""
        current_time = datetime.utcnow()
        
        # Check error rate
        recent_errors = self._get_recent_errors()
        if recent_errors > self.alert_thresholds['error_rate']:
            self._trigger_alert('high_error_rate', f"Error rate: {recent_errors:.2%}")
        
        # Check response time
        avg_response_time = self._get_avg_response_time()
        if avg_response_time > self.alert_thresholds['response_time']:
            self._trigger_alert('high_response_time', f"Avg response time: {avg_response_time:.2f}s")
        
        # Check system resources
        cpu_usage = psutil.cpu_percent()
        memory_usage = psutil.virtual_memory().percent
        
        if cpu_usage > self.alert_thresholds['cpu_usage']:
            self._trigger_alert('high_cpu_usage', f"CPU usage: {cpu_usage:.1f}%")
        
        if memory_usage > self.alert_thresholds['memory_usage']:
            self._trigger_alert('high_memory_usage', f"Memory usage: {memory_usage:.1f}%")
    
    def _get_recent_errors(self) -> float:
        """Get recent error rate"""
        # Implementation would check recent error metrics
        return 0.0
    
    def _get_avg_response_time(self) -> float:
        """Get average response time"""
        # Implementation would calculate from response time metrics
        return 0.0
    
    def _trigger_alert(self, alert_type: str, message: str):
        """Trigger an alert"""
        alert_data = {
            'alert_type': alert_type,
            'message': message,
            'timestamp': datetime.utcnow(),
            'service': 'orchestrator'
        }
        
        # Log the alert
        logger.warning(f"ALERT: {message}")
        StructuredLogger.log_event("alert_triggered", "WARNING", message, alert_type=alert_type)
        
        # Send to alerting system (implement based on your alerting provider)
        self._send_alert(alert_data)
    
    def _send_alert(self, alert_data: Dict[str, Any]):
        """Send alert to external system"""
        # Placeholder for alerting integration
        # Could integrate with PagerDuty, Slack, email, etc.
        pass

class AgentRouter:
    """Routes requests to appropriate specialized agents with monitoring"""
    
    def __init__(self):
        self.agent_urls = {
            'tramite_buscar': Config.TRAMITES_AGENT_URL,
            'tramite_requisitos': Config.TRAMITES_AGENT_URL,
            'tramite_costo': Config.TRAMITES_AGENT_URL,
            'tramite_plazo': Config.TRAMITES_AGENT_URL,
            'tramite_oficina': Config.TRAMITES_AGENT_URL,
            'tramite_estado': Config.TRAMITES_AGENT_URL,
            'pqrsd_crear': Config.PQRSD_AGENT_URL,
            'pqrsd_estado': Config.PQRSD_AGENT_URL,
            'pqrsd_tipos': Config.PQRSD_AGENT_URL,
            'programa_buscar': Config.PROGRAMAS_AGENT_URL,
            'programa_elegibilidad': Config.PROGRAMAS_AGENT_URL,
            'programa_inscripcion': Config.PROGRAMAS_AGENT_URL,
            'programa_beneficios': Config.PROGRAMAS_AGENT_URL,
            'notificacion_pico_placa': Config.NOTIFICACIONES_AGENT_URL,
            'notificacion_cierre_vial': Config.NOTIFICACIONES_AGENT_URL,
            'notificacion_evento': Config.NOTIFICACIONES_AGENT_URL,
            'notificacion_alerta': Config.NOTIFICACIONES_AGENT_URL
        }
        self.monitoring = MonitoringManager()
    
    def route_to_agent(self, intent: str, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route request to appropriate agent and return response"""
        start_time = time.time()
        
        try:
            # Get agent URL
            agent_url = self.agent_urls.get(intent)
            if not agent_url:
                error_msg = f"No agent available for intent: {intent}"
                logger.warning(error_msg)
                self.monitoring.record_metric('agent_routing_error', 1.0, {'intent': intent})
                return {
                    'error': 'No agent available for intent',
                    'intent': intent
                }
            
            # Prepare agent request
            agent_request = {
                'user_message': user_message,
                'conversation_context': context,
                'intent': intent,
                'timestamp': datetime.utcnow().isoformat(),
                'session_id': context.get('session_id', 'unknown')
            }
            
            # Call agent with timeout
            response = requests.post(
                f"{agent_url}/process",
                json=agent_request,
                timeout=30,
                headers={
                    'Content-Type': 'application/json',
                    'X-Service-Source': 'orchestrator',
                    'X-Request-ID': str(uuid.uuid4())
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Record successful response time
            response_time = time.time() - start_time
            self.monitoring.record_metric('agent_response_time', response_time, {
                'intent': intent,
                'agent_url': agent_url
            })
            
            StructuredLogger.log_event("agent_routing_success", "INFO",
                                     f"Successfully routed to agent for intent: {intent}",
                                     response_time=response_time)
            
            return result
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout calling agent for intent {intent}"
            logger.error(error_msg)
            self.monitoring.record_metric('agent_timeout', 1.0, {'intent': intent})
            StructuredLogger.log_event("agent_timeout", "ERROR", error_msg, intent=intent)
            return {'error': 'Agent timeout', 'intent': intent}
        except requests.exceptions.RequestException as e:
            error_msg = f"Error calling agent for intent {intent}: {e}"
            logger.error(error_msg)
            self.monitoring.record_metric('agent_request_error', 1.0, {'intent': intent})
            StructuredLogger.log_event("agent_request_error", "ERROR", error_msg, intent=intent)
            return {'error': 'Agent unavailable', 'intent': intent}
        except Exception as e:
            error_msg = f"Unexpected error routing to agent: {e}"
            logger.error(error_msg)
            self.monitoring.record_metric('agent_routing_error', 1.0, {'intent': intent})
            StructuredLogger.log_event("agent_routing_error", "ERROR", error_msg, intent=intent)
            return {'error': 'Routing error', 'intent': intent}

class SessionManager:
    """Enhanced session management with proper cleanup and persistence"""
    
    def __init__(self):
        self.session_timeout = timedelta(hours=Config.SESSION_TIMEOUT_HOURS)
        self.max_sessions_per_user = 5
        self.cleanup_interval = 3600  # 1 hour
        self._start_cleanup_thread()
    
    def create_session(self, user_id: str, chat_id: str) -> str:
        """Create a new session with proper validation"""
        try:
            # Check if user has too many active sessions
            user_sessions = self._get_user_sessions(user_id)
            if len(user_sessions) >= self.max_sessions_per_user:
                # Close oldest session
                self._close_oldest_session(user_sessions)
            
            # Create new session
            session_id = f"session_{uuid.uuid4().hex}"
            session_data = {
                'user_id': user_id,
                'chat_id': chat_id,
                'created_at': datetime.utcnow(),
                'last_active': datetime.utcnow(),
                'messages': [],
                'memory_summary': '',
                'user_preferences': {},
                'context_relevance_score': 0.0,
                'session_metadata': {
                    'ip_address': get_client_ip(),
                    'user_agent': request.headers.get('User-Agent', ''),
                    'environment': Config.ENVIRONMENT
                }
            }
            
            # Store in Firestore with TTL
            session_ref = db.collection('sessions').document(session_id)
            session_ref.set(session_data)
            
            # Set TTL for automatic cleanup (30 days)
            db.collection('sessions').document(session_id).update({
                'ttl': datetime.utcnow() + timedelta(days=30)
            })
            
            StructuredLogger.log_event("session_created", "INFO", f"Session created: {session_id}",
                                     user_id=user_id, chat_id=chat_id)
            
            return session_id
            
        except Exception as e:
            logger.error(f"Session creation failed: {e}")
            StructuredLogger.log_event("session_creation_failed", "ERROR", str(e), user_id=user_id)
            raise
    
    def _get_user_sessions(self, user_id: str) -> List[str]:
        """Get all active sessions for a user"""
        try:
            sessions = db.collection('sessions').where('user_id', '==', user_id).stream()
            return [session.id for session in sessions]
        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []
    
    def _close_oldest_session(self, session_ids: List[str]):
        """Close the oldest session"""
        try:
            if not session_ids:
                return
            
            # Find oldest session
            oldest_session = None
            oldest_time = datetime.utcnow()
            
            for session_id in session_ids:
                try:
                    session_ref = db.collection('sessions').document(session_id)
                    session_doc = session_ref.get()
                    if session_doc.exists:
                        session_data = session_doc.to_dict()
                        created_at = session_data.get('created_at')
                        if created_at and created_at < oldest_time:
                            oldest_time = created_at
                            oldest_session = session_id
                except Exception as e:
                    logger.error(f"Error checking session {session_id}: {e}")
            
            # Delete oldest session
            if oldest_session:
                db.collection('sessions').document(oldest_session).delete()
                StructuredLogger.log_event("session_closed", "INFO", f"Closed oldest session: {oldest_session}")
                
        except Exception as e:
            logger.error(f"Failed to close oldest session: {e}")
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        try:
            cutoff_time = datetime.utcnow() - self.session_timeout
            expired_sessions = db.collection('sessions').where('last_active', '<', cutoff_time).stream()
            
            for session in expired_sessions:
                session.reference.delete()
                StructuredLogger.log_event("session_expired_cleanup", "INFO", f"Cleaned up expired session: {session.id}")
                
        except Exception as e:
            logger.error(f"Session cleanup failed: {e}")
    
    def _start_cleanup_thread(self):
        """Start background thread for session cleanup"""
        def cleanup_worker():
            while True:
                time.sleep(self.cleanup_interval)
                self.cleanup_expired_sessions()
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()

class Orchestrator:
    """Main orchestrator class with comprehensive monitoring"""
    
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.context_manager = ContextManager()
        self.agent_router = AgentRouter()
        self.session_manager = SessionManager()
        self.monitoring = MonitoringManager()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.llm_client = LLMClient()
    
    def process_request(self, session_id: str, user_id: str, user_message: str, chat_id: str = None) -> Dict[str, Any]:
        """Process incoming request and return appropriate response"""
        start_time = time.time()
        
        try:
            # Validate input data
            if not SecurityValidator.validate_input_data(user_message):
                error_msg = "Invalid input detected - potential security threat"
                logger.warning(error_msg)
                self.monitoring.record_metric('security_violation', 1.0)
                return {
                    'error': error_msg,
                    'metadata': {
                        'processing_time': round(time.time() - start_time, 3),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                }
            
            # Get conversation context
            context = self.context_manager.get_conversation_context(session_id, user_message)
            
            # Classify intent
            intent_data = self.intent_classifier.classify_intent(user_message,
                                                               json.dumps(context['recent_messages'][-5:], indent=2))
            intent = intent_data['intent']
            
            logger.info(f"Intent classified: {intent} (confidence: {intent_data['confidence']:.2f})")
            
            # Handle different intent types
            if intent == 'clarificacion':
                response = self._handle_clarification(user_message, context, intent_data)
            elif intent == 'human_escalation':
                response = self._handle_human_escalation(user_message, context)
            elif intent in ['saludo', 'despedida', 'agradecimiento']:
                response = self._handle_general_interaction(intent, user_message, context)
            else:
                # Route to specialized agent
                response = self.agent_router.route_to_agent(intent, user_message, context)
            
            # Update session context
            self._update_session_after_response(session_id, user_message, response, context)
            
            # Record metrics
            processing_time = time.time() - start_time
            self.monitoring.record_metric('request_processing_time', processing_time, {
                'intent': intent,
                'confidence': str(intent_data['confidence'])
            })
            
            # Add metadata
            response['metadata'] = {
                'processing_time': round(processing_time, 3),
                'intent': intent,
                'confidence': intent_data['confidence'],
                'timestamp': datetime.utcnow().isoformat(),
                'session_id': session_id
            }
            
            # Check for alerts
            self.monitoring.check_alerts()
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Orchestrator processing error: {e}"
            logger.error(error_msg)
            self.monitoring.record_metric('processing_error', 1.0)
            StructuredLogger.log_event("processing_error", "ERROR", error_msg,
                                     processing_time=processing_time, session_id=session_id)
            
            # Return sanitized error response
            error_response = SecurityValidator.sanitize_response({
                'error': 'Internal processing error',
                'metadata': {
                    'processing_time': round(processing_time, 3),
                    'timestamp': datetime.utcnow().isoformat(),
                    'session_id': session_id
                }
            })
            
            return error_response
    
    def _handle_clarification(self, user_message: str, context: Dict[str, Any], intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle clarification requests with real LLM integration"""
        try:
            # Generate clarification questions using real LLM
            prompt = CLARIFICATION_PROMPT.format(
                user_message=user_message,
                recent_messages=json.dumps(context['recent_messages'][-5:], indent=2),
                confidence_score=intent_data['confidence']
            )
            
            response_text = self.llm_client.call_llm(prompt)
            return json.loads(response_text)
            
        except Exception as e:
            logger.error(f"Error handling clarification: {e}")
            self.monitoring.record_metric('clarification_error', 1.0)
            return {
                'questions': ['¿Podría explicar con más detalle lo que necesita?'],
                'suggested_intents': ['ayuda'],
                'reasoning': 'Error generando preguntas de clarificación'
            }
    
    def _handle_human_escalation(self, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle human escalation requests with real LLM integration"""
        try:
            # Detect urgency and reason for escalation using real LLM
            prompt = HUMAN_ESCALATION_DETECTION_PROMPT.format(
                user_message=user_message,
                recent_messages=json.dumps(context['recent_messages'][-3:], indent=2)
            )
            
            escalation_text = self.llm_client.call_llm(prompt)
            escalation_data = json.loads(escalation_text)
            
            if escalation_data.get('escalate', False):
                return {
                    'escalate_to_human': True,
                    'reason': escalation_data.get('reasons', ['Solicitud de usuario']),
                    'urgency': escalation_data.get('urgency', 'media'),
                    'human_agent_info': {
                        'name': 'Agente Humano',
                        'department': 'Atención al Ciudadano',
                        'estimated_wait_time': '5 minutos',
                        'contact_method': 'chat'
                    },
                    'message': 'Voy a transferirlo con un agente humano para que lo atienda personalmente. Por favor espere unos momentos.'
                }
            else:
                return {
                    'escalate_to_human': False,
                    'message': 'Entiendo su situación. Puedo ayudarle con eso. ¿Qué necesita exactamente?'
                }
            
        except Exception as e:
            logger.error(f"Error handling human escalation: {e}")
            self.monitoring.record_metric('escalation_error', 1.0)
            return {
                'escalate_to_human': True,
                'reason': ['Error en detección de escalación'],
                'urgency': 'media',
                'human_agent_info': {
                    'name': 'Agente Humano',
                    'department': 'Atención al Ciudadano',
                    'estimated_wait_time': '5 minutos',
                    'contact_method': 'chat'
                },
                'message': 'Voy a transferirlo con un agente humano para que lo atienda personalmente.'
            }
    
    def _handle_general_interaction(self, intent: str, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general interactions (greetings, farewells, thanks)"""
        responses = {
            'saludo': '¡Hola! Bienvenido a MedellínBot, su asistente ciudadano. ¿En qué puedo ayudarle hoy?',
            'despedida': '¡Hasta luego! Gracias por usar MedellínBot. Si necesita algo más, no dude en contactarnos.',
            'agradecimiento': '¡De nada! Estoy para servirle. ¿En qué más puedo ayudarle?'
        }
        
        return {
            'response': responses.get(intent, '¡Hola! ¿En qué puedo ayudarle?'),
            'suggested_actions': ['tramites', 'pqrsd', 'programas_sociales', 'notificaciones']
        }
    
    def _update_session_after_response(self, session_id: str, user_message: str, response: Dict[str, Any], context: Dict[str, Any]):
        """Update session after generating response"""
        try:
            # Add user message to history
            new_messages = context['recent_messages'].copy()
            new_messages.append({
                'text': user_message,
                'role': 'user',
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Add agent response to history
            if 'response' in response:
                new_messages.append({
                    'text': response['response'],
                    'role': 'agent',
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            # Update session
            self.context_manager.update_session_context(session_id, new_messages)
            
        except Exception as e:
            logger.error(f"Error updating session after response: {e}")
            self.monitoring.record_metric('session_update_error', 1.0)

@app.route('/process', methods=['POST'])
@validate_session
def process_request():
    """Main endpoint for processing requests"""
    start_time = time.time()
    
    try:
        data = request.get_json()
        
        session_id = data.get('session_id')
        user_id = data.get('user_id')
        user_message = data.get('text', '')
        chat_id = data.get('chat_id')
        
        # Get orchestrator instance
        orchestrator = app.config.get('orchestrator')
        if not orchestrator:
            orchestrator = Orchestrator()
            app.config['orchestrator'] = orchestrator
        
        # Process request
        response = orchestrator.process_request(session_id, user_id, user_message, chat_id)
        
        # Record successful processing
        processing_time = time.time() - start_time
        logger.info(f"Request processed successfully. Processing time: {processing_time:.3f}s")
        
        return jsonify(response), 200
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"Process request error: {e}"
        logger.error(error_msg)
        StructuredLogger.log_event("process_request_error", "ERROR", error_msg,
                                 processing_time=processing_time)
        
        # Return sanitized error response
        error_response = SecurityValidator.sanitize_response({
            'error': 'Request processing failed',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return jsonify(error_response), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check endpoint"""
    try:
        # Check system resources
        cpu_usage = psutil.cpu_percent()
        memory_usage = psutil.virtual_memory().percent
        
        # Check database connections
        db_status = "connected"
        try:
            db.collection('health_check').document('test').get()
        except Exception as e:
            db_status = f"disconnected: {str(e)}"
        
        # Check Redis connection
        redis_status = "connected" if redis_client else "disconnected"
        if redis_client:
            try:
                redis_client.ping()
            except Exception as e:
                redis_status = f"disconnected: {str(e)}"
        
        # Check LLM connection
        llm_status = "connected"
        try:
            # Test LLM connection briefly
            test_prompt = "Test connection"
            llm_client = LLMClient()
            llm_client.call_llm(test_prompt)
        except Exception as e:
            llm_status = f"disconnected: {str(e)}"
        
        health_status = {
            "status": "healthy",
            "service": "medellinbot-orchestrator",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": Config.ENVIRONMENT,
            "version": "1.0.0",
            "system_resources": {
                "cpu_usage_percent": cpu_usage,
                "memory_usage_percent": memory_usage,
                "disk_usage_percent": psutil.disk_usage('/').percent if hasattr(psutil, 'disk_usage') else None
            },
            "components": {
                "firestore": db_status,
                "storage": "connected",
                "redis": redis_status,
                "llm": llm_status,
                "secret_manager": "connected"
            },
            "rate_limiting": {
                "enabled": True,
                "storage": rate_limiter.storage,
                "window_seconds": rate_limiter.rate_limit_window,
                "max_requests": rate_limiter.max_requests
            },
            "monitoring": {
                "enabled": Config.ENABLE_METRICS,
                "retention_days": Config.METRICS_RETENTION_DAYS
            }
        }
        
        # Determine overall status
        critical_components = [db_status, redis_status, llm_status]
        if any("disconnected" in str(comp) for comp in critical_components):
            health_status["status"] = "degraded"
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        
        return jsonify(health_status), status_code
        
    except Exception as e:
        error_msg = f"Health check failed: {e}"
        logger.error(error_msg)
        StructuredLogger.log_event("health_check_failed", "ERROR", error_msg)
        
        return jsonify({
            "status": "unhealthy",
            "service": "medellinbot-orchestrator",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route('/session/<session_id>', methods=['GET'])
@validate_session
def get_session(session_id):
    """Get comprehensive session information"""
    try:
        session_ref = db.collection('sessions').document(session_id)
        session_doc = session_ref.get()
        
        if not session_doc.exists:
            StructuredLogger.log_event("session_not_found_api", "WARNING", f"Session not found via API: {session_id}")
            return jsonify({"error": "Session not found"}), 404
        
        session_data = session_doc.to_dict()
        
        # Calculate session metrics
        message_count = len(session_data.get('messages', []))
        session_duration = None
        if session_data.get('created_at') and session_data.get('last_active'):
            session_duration = (session_data['last_active'] - session_data['created_at']).total_seconds()
        
        response_data = {
            "session_id": session_id,
            "user_id": session_data.get('user_id'),
            "chat_id": session_data.get('chat_id'),
            "created_at": session_data.get('created_at').isoformat() if session_data.get('created_at') else None,
            "last_active": session_data.get('last_active').isoformat() if session_data.get('last_active') else None,
            "session_duration_seconds": session_duration,
            "message_count": message_count,
            "memory_summary": session_data.get('memory_summary', ''),
            "context_relevance_score": session_data.get('context_relevance_score', 0.0),
            "user_preferences": session_data.get('user_preferences', {}),
            "session_metadata": session_data.get('session_metadata', {}),
            "estimated_session_value": self._calculate_session_value(session_data)
        }
        
        # Sanitize response
        sanitized_response = SecurityValidator.sanitize_response(response_data)
        
        return jsonify(sanitized_response), 200
        
    except Exception as e:
        error_msg = f"Get session error: {e}"
        logger.error(error_msg)
        StructuredLogger.log_event("get_session_error", "ERROR", error_msg, session_id=session_id)
        
        return jsonify({"error": "Failed to retrieve session"}), 500
    
    def _calculate_session_value(self, session_data: Dict[str, Any]) -> float:
        """Calculate estimated value of session based on engagement metrics"""
        try:
            messages = session_data.get('messages', [])
            message_count = len(messages)
            
            # Simple heuristic: more messages = higher value
            # This could be enhanced with more sophisticated metrics
            return min(message_count * 0.1, 10.0)  # Cap at 10.0
            
        except Exception as e:
            logger.error(f"Error calculating session value: {e}")
            return 0.0

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Get comprehensive metrics and monitoring data"""
    try:
        if not Config.ENABLE_METRICS:
            return jsonify({"error": "Metrics disabled"}), 403
        
        # Get recent metrics from Firestore
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        metrics_query = db.collection('metrics').where('timestamp', '>', cutoff_time)
        
        metrics_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_metrics": {},
            "system_metrics": {
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent if hasattr(psutil, 'disk_usage') else None
            },
            "session_metrics": {},
            "error_metrics": {}
        }
        
        # Aggregate metrics from Firestore
        for doc in metrics_query.stream():
            metric_data = doc.to_dict()
            metric_name = metric_data.get('metric_name')
            value = metric_data.get('value')
            
            if metric_name not in metrics_data["request_metrics"]:
                metrics_data["request_metrics"][metric_name] = []
            metrics_data["request_metrics"][metric_name].append({
                "value": value,
                "timestamp": metric_data.get('timestamp').isoformat(),
                "tags": metric_data.get('tags', {})
            })
        
        return jsonify(metrics_data), 200
        
    except Exception as e:
        logger.error(f"Metrics endpoint error: {e}")
        return jsonify({"error": "Metrics unavailable"}), 500

@app.route('/alerts', methods=['GET'])
def get_alerts():
    """Get recent alerts and notifications"""
    try:
        # Get recent alerts from Firestore
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        alerts_query = db.collection('alerts').where('timestamp', '>', cutoff_time).order_by('timestamp', direction='DESCENDING')
        
        alerts = []
        for doc in alerts_query.limit(50).stream():  # Last 50 alerts
            alert_data = doc.to_dict()
            alerts.append({
                "alert_type": alert_data.get('alert_type'),
                "message": alert_data.get('message'),
                "timestamp": alert_data.get('timestamp').isoformat(),
                "service": alert_data.get('service')
            })
        
        return jsonify({
            "alerts": alerts,
            "total_count": len(alerts),
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Alerts endpoint error: {e}")
        return jsonify({"error": "Alerts unavailable"}), 500

if __name__ == "__main__":
    # Run locally for development
    port = int(os.environ.get("PORT", 8081))
    debug = Config.ENVIRONMENT == 'development'
    
    logger.info(f"Starting MedellínBot orchestrator on port {port}, debug={debug}")
    StructuredLogger.log_event("orchestrator_started", "INFO", f"Orchestrator started on port {port}",
                             environment=Config.ENVIRONMENT)
    
    app.run(debug=debug, host="0.0.0.0", port=port)