#!/usr/bin/env python3
"""
MedellínBot - Telegram Webhook Handler
Cloud Run deployment for receiving and processing Telegram webhook events
"""

import os
import json
import logging
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify, Response
import requests
from google.cloud import secretmanager, firestore
from google.cloud.firestore_v1.base_client import Client
import jwt
from functools import wraps
import secrets
from werkzeug.security import check_password_hash, generate_password_hash
import redis
import json as json_lib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Security headers configuration
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

# Initialize Google Cloud clients
try:
    secret_client = secretmanager.SecretManagerServiceClient()
    db = firestore.Client()
    logger.info("Google Cloud clients initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Google Cloud clients: {e}")
    raise

# Configuration
class Config:
    """Application configuration loaded from environment and secrets"""
    
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
    
    # Load configuration from environment and secrets
    ORCHESTRATOR_URL = os.environ.get('ORCHESTRATOR_URL', 'http://localhost:8081')
    TELEGRAM_TOKEN = get_secret.__func__('telegram-bot-token')
    JWT_SECRET = get_secret.__func__('jwt-secret-key')
    RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS', '100'))
    RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW', '3600'))  # 1 hour
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
    
    # Security settings
    ALLOWED_CHAT_IDS = os.environ.get('ALLOWED_CHAT_IDS', '').split(',') if os.environ.get('ALLOWED_CHAT_IDS') else None
    REQUIRE_AUTH = os.environ.get('REQUIRE_AUTH', 'false').lower() == 'true'

# Rate limiting storage (Redis-based for production)
try:
    redis_client = redis.Redis(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=int(os.environ.get('REDIS_PORT', 6379)),
        db=int(os.environ.get('REDIS_DB', 0)),
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5
    )
    # Test Redis connection
    redis_client.ping()
    RATE_LIMIT_STORAGE = 'redis'
    logger.info("Redis client initialized successfully")
except (redis.ConnectionError, redis.TimeoutError) as e:
    logger.warning(f"Redis connection failed: {e}. Falling back to in-memory storage.")
    redis_client = None
    RATE_LIMIT_STORAGE = 'memory'

# Rate limiting storage (in-memory fallback)
rate_limit_store = {}

class JWTManager:
    """JWT token management and validation"""
    
    @staticmethod
    def generate_token(user_id: str, chat_id: str) -> str:
        """Generate JWT token for user session"""
        payload = {
            'user_id': user_id,
            'chat_id': chat_id,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow(),
            'jti': secrets.token_urlsafe(32)  # Unique token identifier
        }
        return jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')
    
    @staticmethod
    def validate_token(token: str) -> Dict[str, Any]:
        """Validate JWT token and return payload"""
        try:
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
    
    @staticmethod
    def extract_user_info_from_request() -> Optional[Dict[str, str]]:
        """Extract user info from Authorization header"""
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        try:
            payload = JWTManager.validate_token(token)
            user_id = payload.get('user_id')
            chat_id = payload.get('chat_id')
            
            if user_id and chat_id:
                return {
                    'user_id': str(user_id),
                    'chat_id': str(chat_id)
                }
            return None
        except ValueError:
            return None

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
        sensitive_fields = ['password', 'token', 'secret', 'key', 'authorization']
        
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

def get_client_ip():
    """Get client IP address from request headers"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def is_rate_limited(client_id: str) -> bool:
    """Check if client has exceeded rate limit"""
    current_time = time.time()
    window_start = current_time - Config.RATE_LIMIT_WINDOW
    
    if RATE_LIMIT_STORAGE == 'redis' and redis_client:
        return _is_rate_limited_redis(client_id, current_time, window_start)
    else:
        return _is_rate_limited_memory(client_id, current_time, window_start)

def _is_rate_limited_redis(client_id: str, current_time: float, window_start: float) -> bool:
    """Check rate limit using Redis"""
    if redis_client is None:
        return _is_rate_limited_memory(client_id, current_time, window_start)
        
    try:
        # Use Redis sorted set for rate limiting
        key = f"rate_limit:{client_id}"
        
        # Remove old entries outside the window
        redis_client.zremrangebyscore(key, 0, window_start)
        
        # Count current requests in window
        current_count = redis_client.zcard(key)
        
        if current_count >= Config.RATE_LIMIT_REQUESTS:
            return True
        
        # Add current request
        redis_client.zadd(key, {str(current_time): current_time})
        
        # Set expiration on the key
        redis_client.expire(key, Config.RATE_LIMIT_WINDOW + 60)  # Extra 60 seconds buffer
        
        return False
        
    except (redis.ConnectionError, redis.TimeoutError, Exception) as e:
        logger.warning(f"Redis rate limit check failed: {e}. Falling back to in-memory.")
        return _is_rate_limited_memory(client_id, current_time, window_start)

def _is_rate_limited_memory(client_id: str, current_time: float, window_start: float) -> bool:
    """Check rate limit using in-memory storage"""
    if client_id not in rate_limit_store:
        rate_limit_store[client_id] = []
    
    # Remove requests outside the current window
    rate_limit_store[client_id] = [
        req_time for req_time in rate_limit_store[client_id]
        if req_time > window_start
    ]
    
    # Check if limit exceeded
    if len(rate_limit_store[client_id]) >= Config.RATE_LIMIT_REQUESTS:
        return True
    
    # Add current request
    rate_limit_store[client_id].append(current_time)
    return False

def validate_telegram_webhook(func):
    """Decorator to validate Telegram webhook requests"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Basic validation
        if not request.is_json:
            logger.warning(f"Invalid content type: {request.content_type}")
            return jsonify({"error": "Invalid content type, expected application/json"}), 400
        
        # Check rate limiting
        client_ip = get_client_ip()
        if is_rate_limited(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return jsonify({"error": "Rate limit exceeded"}), 429
        
        # Validate required headers
        if Config.REQUIRE_AUTH:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logger.warning(f"Missing or invalid authorization header from IP: {client_ip}")
                return jsonify({"error": "Authorization required"}), 401
            
            try:
                token = auth_header.split(' ')[1]
                # Validate JWT token using our JWTManager
                payload = JWTManager.validate_token(token)
                request.user_id = payload.get('user_id')
                request.chat_id = payload.get('chat_id')
            except ValueError as e:
                logger.warning(f"JWT validation failed from IP: {client_ip} - {e}")
                return jsonify({"error": "Invalid or expired authorization"}), 401
        
        return func(*args, **kwargs)
    return wrapper

def validate_telegram_update(payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate Telegram update payload"""
    if not payload:
        return False, "Empty payload"
    
    if 'message' not in payload:
        return False, "Missing message field"
    
    message = payload.get('message', {})
    chat = message.get('chat', {})
    
    if not chat.get('id'):
        return False, "Missing chat ID"
    
    # Validate chat ID if whitelist is configured
    if Config.ALLOWED_CHAT_IDS and str(chat.get('id')) not in Config.ALLOWED_CHAT_IDS:
        return False, f"Chat ID {chat.get('id')} not in allowed list"
    
    # Validate input for security threats
    text = message.get('text', '')
    if text and not SecurityValidator.validate_input_data(text):
        return False, "Invalid input detected - potential security threat"
    
    return True, None

def create_session_id(chat_id: int, user_id: int) -> str:
    """Create a session ID for the conversation"""
    # Use a hash to create a consistent but non-reversible session ID
    combined = f"{chat_id}_{user_id}_{Config.JWT_SECRET}"
    return f"tg:{hashlib.sha256(combined.encode()).hexdigest()[:16]}"

def log_webhook_event(event_type: str, data: Dict[str, Any]):
    """Log webhook events to Firestore for monitoring"""
    try:
        log_entry = {
            'event_type': event_type,
            'timestamp': datetime.utcnow(),
            'data': data,
            'environment': Config.ENVIRONMENT
        }
        
        # Store in Firestore with TTL (Time To Live) of 30 days
        db.collection('webhook_logs').add(log_entry)
    except Exception as e:
        logger.error(f"Failed to log webhook event: {e}")

@app.route('/', methods=['POST'])
@validate_telegram_webhook
def webhook():
    """Handle incoming Telegram webhook"""
    start_time = time.time()
    
    try:
        # Parse request data
        payload = request.get_json()
        logger.info(f"Received webhook from IP: {get_client_ip()}")
        
        # Validate payload
        is_valid, error_msg = validate_telegram_update(payload)
        if not is_valid:
            logger.warning(f"Invalid webhook payload: {error_msg}")
            return jsonify({"error": error_msg}), 400
        
        message = payload.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        text = message.get("text", "")
        message_id = message.get("message_id")
        
        # Create session ID
        session_id = create_session_id(chat_id, user_id)
        
        # Log the incoming webhook
        log_webhook_event("incoming_webhook", {
            'session_id': session_id,
            'chat_id': chat_id,
            'user_id': user_id,
            'text': text[:100] + "..." if len(text) > 100 else text,  # Truncate long messages
            'message_id': message_id
        })
        
        # Build request to orchestrator
        orchestrator_payload = {
            "session_id": session_id,
            "user_id": str(user_id),
            "chat_id": str(chat_id),
            "message_id": message_id,
            "text": text,
            "raw": payload,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "environment": Config.ENVIRONMENT,
                "client_ip": get_client_ip(),
                "user_agent": request.headers.get('User-Agent', '')
            }
        }
        
        # Forward to orchestrator with timeout
        try:
            response = requests.post(
                f"{Config.ORCHESTRATOR_URL}/process",
                json=orchestrator_payload,
                timeout=15,  # 15 second timeout
                headers={
                    "Content-Type": "application/json",
                    "X-Session-ID": session_id,
                    "X-Chat-ID": str(chat_id)
                }
            )
            
            response.raise_for_status()
            
            # Log successful forwarding
            processing_time = time.time() - start_time
            log_webhook_event("forwarded_to_orchestrator", {
                'session_id': session_id,
                'chat_id': chat_id,
                'processing_time': processing_time,
                'status_code': response.status_code
            })
            
            logger.info(f"Webhook forwarded successfully for session {session_id}. Processing time: {processing_time:.3f}s")
            
            return jsonify({
                "status": "ok",
                "session_id": session_id,
                "processing_time": processing_time
            }), 200
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout forwarding to orchestrator for session {session_id}")
            return jsonify({"error": "Service timeout"}), 504
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to orchestrator for session {session_id}")
            return jsonify({"error": "Service unavailable"}), 503
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error forwarding to orchestrator: {e}")
            return jsonify({"error": "Service error"}), 502
            
    except Exception as e:
        logger.error(f"Unexpected error in webhook handler: {e}", exc_info=True)
        # Return sanitized error response
        error_response = SecurityValidator.sanitize_response({
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        })
        return jsonify(error_response), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run"""
    try:
        # Check if we can connect to Firestore
        health_status = {
            "status": "healthy",
            "service": "medellinbot-webhook",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": Config.ENVIRONMENT,
            "version": "1.0.0"
        }
        
        # Test Firestore connection
        try:
            db.collection('health_check').document('test').get()
            health_status["database"] = "connected"
        except Exception as e:
            logger.warning(f"Firestore health check failed: {e}")
            health_status["database"] = "disconnected"
        
        return jsonify(health_status), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "service": "medellinbot-webhook",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route('/metrics', methods=['GET'])
def metrics():
    """Metrics endpoint for monitoring"""
    try:
        # Return basic metrics
        metrics_data = {
            "rate_limit_stats": {
                "total_clients": len(rate_limit_store),
                "rate_limit_window": Config.RATE_LIMIT_WINDOW,
                "max_requests": Config.RATE_LIMIT_REQUESTS
            },
            "configuration": {
                "environment": Config.ENVIRONMENT,
                "require_auth": Config.REQUIRE_AUTH,
                "allowed_chat_ids_count": len(Config.ALLOWED_CHAT_IDS) if Config.ALLOWED_CHAT_IDS else 0
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return jsonify(metrics_data), 200
        
    except Exception as e:
        logger.error(f"Metrics endpoint error: {e}")
        return jsonify({"error": "Metrics unavailable"}), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 error for path: {request.path}")
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"500 error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    # Run locally for development
    port = int(os.environ.get("PORT", 8080))
    debug = Config.ENVIRONMENT == 'development'
    
    logger.info(f"Starting MedellínBot webhook on port {port}, debug={debug}")
    app.run(debug=debug, host="0.0.0.0", port=port)