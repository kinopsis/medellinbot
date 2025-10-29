#!/usr/bin/env python3
"""
Comprehensive test suite for MedellínBot Webhook Handler
Tests webhook functionality, security, error handling, and performance
"""

import pytest
import json
import time
import jwt
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from webhook.app import app, Config, rate_limit_store


class TestWebhookHandler:
    """Test suite for webhook handler functionality"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def valid_webhook_payload(self):
        """Valid Telegram webhook payload"""
        return {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {
                    "id": 123456789,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "testuser",
                    "language_code": "es"
                },
                "chat": {
                    "id": 123456789,
                    "first_name": "Test",
                    "username": "testuser",
                    "type": "private"
                },
                "date": 1234567890,
                "text": "Hola, ¿cómo estás?"
            }
        }
    
    @pytest.fixture
    def invalid_webhook_payloads(self):
        """Invalid webhook payloads for testing"""
        return [
            {},  # Empty payload
            {"message": {}},  # Missing required fields
            {"update_id": 123456789},  # Missing message
            {
                "message": {
                    "chat": {}  # Missing chat ID
                }
            }
        ]
    
    @pytest.fixture
    def mock_secret_manager(self):
        """Mock Google Secret Manager"""
        with patch('webhook.app.secretmanager.SecretManagerServiceClient') as mock_client:
            mock_instance = Mock()
            mock_instance.access_secret_version.return_value.payload.data.decode.return_value = "test-secret"
            mock_client.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def mock_firestore(self):
        """Mock Google Firestore"""
        with patch('webhook.app.firestore.Client') as mock_client:
            mock_instance = Mock()
            mock_doc = Mock()
            mock_doc.get.return_value = Mock(exists=False)
            mock_instance.collection.return_value.document.return_value = mock_doc
            mock_client.return_value = mock_instance
            yield mock_instance


class TestWebhookValidation(TestWebhookHandler):
    """Test webhook validation logic"""
    
    def test_valid_webhook_request(self, client, valid_webhook_payload, mock_secret_manager, mock_firestore):
        """Test valid webhook request processing"""
        response = client.post('/', 
                             json=valid_webhook_payload,
                             headers={'Content-Type': 'application/json'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert 'session_id' in data
        assert 'processing_time' in data
    
    def test_invalid_content_type(self, client):
        """Test rejection of non-JSON content type"""
        response = client.post('/', 
                             data='{"message": "test"}',
                             content_type='text/plain')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Invalid content type" in data['error']
    
    def test_missing_message_field(self, client):
        """Test rejection of payload without message field"""
        response = client.post('/', 
                             json={},
                             headers={'Content-Type': 'application/json'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Missing message field" in data['error']
    
    def test_missing_chat_id(self, client):
        """Test rejection of payload without chat ID"""
        response = client.post('/', 
                             json={"message": {"text": "test"}},
                             headers={'Content-Type': 'application/json'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Missing chat ID" in data['error']


class TestRateLimiting(TestWebhookHandler):
    """Test rate limiting functionality"""
    
    def test_rate_limiting(self, client, valid_webhook_payload, mock_secret_manager, mock_firestore):
        """Test rate limiting mechanism"""
        # Configure rate limiting for testing
        original_requests = Config.RATE_LIMIT_REQUESTS
        original_window = Config.RATE_LIMIT_WINDOW
        
        try:
            Config.RATE_LIMIT_REQUESTS = 2
            Config.RATE_LIMIT_WINDOW = 3600
            
            # Make requests within limit
            for i in range(2):
                response = client.post('/', 
                                     json=valid_webhook_payload,
                                     headers={'Content-Type': 'application/json'})
                assert response.status_code == 200
            
            # Make request that exceeds limit
            response = client.post('/', 
                                 json=valid_webhook_payload,
                                 headers={'Content-Type': 'application/json'})
            assert response.status_code == 429
            data = json.loads(response.data)
            assert "Rate limit exceeded" in data['error']
            
        finally:
            # Restore original values
            Config.RATE_LIMIT_REQUESTS = original_requests
            Config.RATE_LIMIT_WINDOW = original_window
            rate_limit_store.clear()
    
    def test_rate_limit_window_reset(self, client, valid_webhook_payload, mock_secret_manager, mock_firestore):
        """Test rate limit window reset"""
        # Configure for testing
        original_requests = Config.RATE_LIMIT_REQUESTS
        original_window = Config.RATE_LIMIT_WINDOW
        
        try:
            Config.RATE_LIMIT_REQUESTS = 1
            Config.RATE_LIMIT_WINDOW = 1  # 1 second window
            
            # Make request that hits limit
            response = client.post('/', 
                                 json=valid_webhook_payload,
                                 headers={'Content-Type': 'application/json'})
            assert response.status_code == 200
            
            # Should be rate limited immediately
            response = client.post('/', 
                                 json=valid_webhook_payload,
                                 headers={'Content-Type': 'application/json'})
            assert response.status_code == 429
            
            # Wait for window to reset
            time.sleep(1.1)
            
            # Should work again after window reset
            response = client.post('/', 
                                 json=valid_webhook_payload,
                                 headers={'Content-Type': 'application/json'})
            assert response.status_code == 200
            
        finally:
            # Restore original values
            Config.RATE_LIMIT_REQUESTS = original_requests
            Config.RATE_LIMIT_WINDOW = original_window
            rate_limit_store.clear()


class TestAuthentication(TestWebhookHandler):
    """Test authentication and authorization"""
    
    def test_jwt_authentication_required(self, client, valid_webhook_payload, mock_secret_manager, mock_firestore):
        """Test JWT authentication when required"""
        # Configure to require auth
        original_require_auth = Config.REQUIRE_AUTH
        Config.REQUIRE_AUTH = True
        
        try:
            # Test without authorization header
            response = client.post('/', 
                                 json=valid_webhook_payload,
                                 headers={'Content-Type': 'application/json'})
            assert response.status_code == 401
            data = json.loads(response.data)
            assert "Authorization required" in data['error']
            
            # Test with invalid JWT token
            response = client.post('/', 
                                 json=valid_webhook_payload,
                                 headers={
                                     'Content-Type': 'application/json',
                                     'Authorization': 'Bearer invalid-token'
                                 })
            assert response.status_code == 401
            data = json.loads(response.data)
            assert "Invalid authorization" in data['error']
            
            # Test with valid JWT token
            valid_token = jwt.encode(
                {'user_id': 'test-user'}, 
                'test-secret', 
                algorithm='HS256'
            )
            response = client.post('/', 
                                 json=valid_webhook_payload,
                                 headers={
                                     'Content-Type': 'application/json',
                                     'Authorization': f'Bearer {valid_token}'
                                 })
            assert response.status_code == 200
            
        finally:
            # Restore original value
            Config.REQUIRE_AUTH = original_require_auth
    
    def test_chat_id_whitelist(self, client, valid_webhook_payload, mock_secret_manager, mock_firestore):
        """Test chat ID whitelist validation"""
        # Configure whitelist
        original_allowed = Config.ALLOWED_CHAT_IDS
        Config.ALLOWED_CHAT_IDS = ['987654321']  # Different from payload chat ID
        
        try:
            response = client.post('/', 
                                 json=valid_webhook_payload,
                                 headers={'Content-Type': 'application/json'})
            assert response.status_code == 400
            data = json.loads(response.data)
            assert "not in allowed list" in data['error']
            
        finally:
            # Restore original value
            Config.ALLOWED_CHAT_IDS = original_allowed


class TestErrorHandling(TestWebhookHandler):
    """Test error handling and resilience"""
    
    def test_orchestrator_timeout(self, client, valid_webhook_payload, mock_secret_manager, mock_firestore):
        """Test handling of orchestrator timeout"""
        with patch('webhook.app.requests.post') as mock_post:
            mock_post.side_effect = TimeoutError("Request timeout")
            
            response = client.post('/', 
                                 json=valid_webhook_payload,
                                 headers={'Content-Type': 'application/json'})
            assert response.status_code == 504
            data = json.loads(response.data)
            assert "Service timeout" in data['error']
    
    def test_orchestrator_connection_error(self, client, valid_webhook_payload, mock_secret_manager, mock_firestore):
        """Test handling of orchestrator connection error"""
        with patch('webhook.app.requests.post') as mock_post:
            mock_post.side_effect = ConnectionError("Connection failed")
            
            response = client.post('/', 
                                 json=valid_webhook_payload,
                                 headers={'Content-Type': 'application/json'})
            assert response.status_code == 503
            data = json.loads(response.data)
            assert "Service unavailable" in data['error']
    
    def test_firestore_connection_error(self, client, valid_webhook_payload, mock_secret_manager):
        """Test handling of Firestore connection error"""
        with patch('webhook.app.firestore.Client') as mock_firestore:
            mock_firestore.side_effect = Exception("Firestore connection failed")
            
            response = client.post('/', 
                                 json=valid_webhook_payload,
                                 headers={'Content-Type': 'application/json'})
            assert response.status_code == 500
            data = json.loads(response.data)
            assert "Internal server error" in data['error']


class TestHealthAndMetrics(TestWebhookHandler):
    """Test health check and metrics endpoints"""
    
    def test_health_check(self, client, mock_firestore):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'medellinbot-webhook'
    
    def test_health_check_firestore_error(self, client):
        """Test health check with Firestore error"""
        with patch('webhook.app.firestore.Client') as mock_firestore:
            mock_instance = Mock()
            mock_instance.collection.return_value.document.return_value.get.side_effect = Exception("DB Error")
            mock_firestore.return_value = mock_instance
            
            response = client.get('/health')
            assert response.status_code == 200  # Still returns 200 but with disconnected status
            data = json.loads(response.data)
            assert data['database'] == 'disconnected'
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint"""
        response = client.get('/metrics')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'rate_limit_stats' in data
        assert 'configuration' in data
        assert 'total_clients' in data['rate_limit_stats']


class TestSessionManagement(TestWebhookHandler):
    """Test session management functionality"""
    
    def test_session_id_generation(self, client, valid_webhook_payload, mock_secret_manager, mock_firestore):
        """Test session ID generation"""
        response = client.post('/', 
                             json=valid_webhook_payload,
                             headers={'Content-Type': 'application/json'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'session_id' in data
        assert data['session_id'].startswith('tg:')
        assert len(data['session_id']) == 19  # tg: + 16 hex chars
    
    def test_consistent_session_id(self, client, valid_webhook_payload, mock_secret_manager, mock_firestore):
        """Test that same user gets same session ID"""
        # Make multiple requests with same chat/user ID
        session_ids = set()
        for i in range(3):
            response = client.post('/', 
                                 json=valid_webhook_payload,
                                 headers={'Content-Type': 'application/json'})
            assert response.status_code == 200
            data = json.loads(response.data)
            session_ids.add(data['session_id'])
        
        # Should have only one unique session ID
        assert len(session_ids) == 1


class TestLoggingAndMonitoring(TestWebhookHandler):
    """Test logging and monitoring functionality"""
    
    def test_webhook_logging(self, client, valid_webhook_payload, mock_firestore):
        """Test webhook event logging"""
        with patch.object(mock_firestore, 'collection') as mock_collection:
            mock_add = mock_collection.return_value.add
            
            response = client.post('/', 
                                 json=valid_webhook_payload,
                                 headers={'Content-Type': 'application/json'})
            
            assert response.status_code == 200
            # Verify that logging was called
            assert mock_add.called
    
    def test_error_logging(self, client, valid_webhook_payload, mock_secret_manager, mock_firestore, caplog):
        """Test error logging"""
        # Test with invalid payload to trigger error logging
        with caplog.at_level('WARNING'):
            response = client.post('/', 
                                 json={"message": {}},
                                 headers={'Content-Type': 'application/json'})
            
            assert response.status_code == 400
            # Verify warning was logged
            assert "Invalid webhook payload" in caplog.text


class TestPerformance(TestWebhookHandler):
    """Test performance requirements"""
    
    def test_response_time_requirement(self, client, valid_webhook_payload, mock_secret_manager, mock_firestore):
        """Test that responses meet performance requirements"""
        start_time = time.time()
        
        response = client.post('/', 
                             json=valid_webhook_payload,
                             headers={'Content-Type': 'application/json'})
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        assert response.status_code == 200
        # Response should be well under 3 second requirement
        assert processing_time < 3.0
        
        # Check that processing time is included in response
        data = json.loads(response.data)
        assert 'processing_time' in data
        assert data['processing_time'] < 3.0


class TestSecurityHeaders(TestWebhookHandler):
    """Test security-related headers and responses"""
    
    def test_cors_headers(self, client):
        """Test CORS headers are not exposed by default"""
        response = client.get('/health')
        # Should not include dangerous CORS headers
        assert 'Access-Control-Allow-Origin' not in response.headers
    
    def test_content_type_validation(self, client, valid_webhook_payload):
        """Test strict content type validation"""
        # Test with XML content type
        response = client.post('/', 
                             data=json.dumps(valid_webhook_payload),
                             content_type='application/xml')
        assert response.status_code == 400
        
        # Test with form content type
        response = client.post('/', 
                             data={'message': 'test'},
                             content_type='application/x-www-form-urlencoded')
        assert response.status_code == 400


if __name__ == '__main__':
    pytest.main([__file__, '-v'])