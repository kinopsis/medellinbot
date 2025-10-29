#!/usr/bin/env python3
"""
Integration test suite for MedellínBot System
Tests end-to-end functionality, component integration, and system behavior
"""

import pytest
import json
import time
import jwt
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
import requests


class TestSystemIntegration:
    """Base test class for system integration tests"""
    
    @pytest.fixture
    def mock_webhook_config(self):
        """Mock webhook configuration"""
        with patch('webhook.app.Config') as mock_config:
            mock_config.ORCHESTRATOR_URL = 'http://localhost:8081'
            mock_config.TELEGRAM_TOKEN = 'test-token'
            mock_config.JWT_SECRET = 'test-secret'
            mock_config.RATE_LIMIT_REQUESTS = 100
            mock_config.RATE_LIMIT_WINDOW = 3600
            mock_config.ENVIRONMENT = 'test'
            mock_config.ALLOWED_CHAT_IDS = None
            mock_config.REQUIRE_AUTH = False
            yield mock_config
    
    @pytest.fixture
    def mock_orchestrator_config(self):
        """Mock orchestrator configuration"""
        with patch('orchestrator.app.Config') as mock_config:
            mock_config.ENVIRONMENT = 'test'
            mock_config.JWT_SECRET = 'test-secret'
            mock_config.SESSION_TIMEOUT_HOURS = 24
            mock_config.MAX_MESSAGE_HISTORY = 50
            mock_config.CONFIDENCE_THRESHOLD = 0.7
            mock_config.TRAMITES_AGENT_URL = 'http://localhost:8082'
            mock_config.PQRSD_AGENT_URL = 'http://localhost:8083'
            mock_config.PROGRAMAS_AGENT_URL = 'http://localhost:8084'
            mock_config.NOTIFICACIONES_AGENT_URL = 'http://localhost:8085'
            mock_config.LLM_PROVIDER = 'mock'
            mock_config.LLM_MODEL = 'mock-model'
            mock_config.LLM_TEMPERATURE = 0.3
            yield mock_config
    
    @pytest.fixture
    def mock_firestore_webhook(self):
        """Mock Firestore for webhook tests"""
        with patch('webhook.app.firestore.Client') as mock_client:
            mock_instance = Mock()
            mock_doc = Mock()
            mock_doc.get.return_value = Mock(exists=False)
            mock_instance.collection.return_value.document.return_value = mock_doc
            mock_client.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def mock_firestore_orchestrator(self):
        """Mock Firestore for orchestrator tests"""
        with patch('orchestrator.app.firestore.Client') as mock_client:
            mock_instance = Mock()
            mock_doc = Mock()
            mock_doc.to_dict.return_value = {
                'user_id': 'test-user',
                'created_at': datetime.utcnow(),
                'last_active': datetime.utcnow(),
                'messages': [],
                'memory_summary': ''
            }
            mock_doc.exists = True
            mock_instance.collection.return_value.document.return_value = mock_doc
            mock_client.return_value = mock_instance
            yield mock_instance


class TestWebhookToOrchestratorIntegration(TestSystemIntegration):
    """Test integration between webhook and orchestrator"""
    
    def test_end_to_end_webhook_forwarding(self, mock_webhook_config, mock_firestore_webhook):
        """Test complete webhook to orchestrator flow"""
        # Import and configure webhook app
        from webhook.app import app
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            # Mock orchestrator response
            with patch('webhook.app.requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    'status': 'ok',
                    'session_id': 'test-session'
                }
                mock_post.return_value = mock_response
                
                # Send valid webhook
                payload = {
                    "update_id": 123456789,
                    "message": {
                        "message_id": 1,
                        "from": {
                            "id": 123456789,
                            "is_bot": False,
                            "first_name": "Test",
                            "username": "testuser"
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
                
                response = client.post('/', 
                                     json=payload,
                                     headers={'Content-Type': 'application/json'})
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['status'] == 'ok'
                assert 'session_id' in data
                assert 'processing_time' in data
                
                # Verify orchestrator was called
                assert mock_post.called
                call_args = mock_post.call_args[1]  # keyword arguments
                assert call_args['json']['session_id'] == data['session_id']
                assert call_args['json']['user_id'] == '123456789'
                assert call_args['json']['text'] == 'Hola, ¿cómo estás?'
    
    def test_webhook_orchestrator_timeout_handling(self, mock_webhook_config, mock_firestore_webhook):
        """Test webhook handling of orchestrator timeout"""
        from webhook.app import app
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            with patch('webhook.app.requests.post') as mock_post:
                mock_post.side_effect = TimeoutError("Orchestrator timeout")
                
                payload = {
                    "update_id": 123456789,
                    "message": {
                        "message_id": 1,
                        "from": {"id": 123456789, "is_bot": False},
                        "chat": {"id": 123456789, "type": "private"},
                        "date": 1234567890,
                        "text": "Test message"
                    }
                }
                
                response = client.post('/', 
                                     json=payload,
                                     headers={'Content-Type': 'application/json'})
                
                assert response.status_code == 504
                data = json.loads(response.data)
                assert "Service timeout" in data['error']
    
    def test_webhook_orchestrator_connection_error(self, mock_webhook_config, mock_firestore_webhook):
        """Test webhook handling of orchestrator connection error"""
        from webhook.app import app
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            with patch('webhook.app.requests.post') as mock_post:
                mock_post.side_effect = ConnectionError("Connection failed")
                
                payload = {
                    "update_id": 123456789,
                    "message": {
                        "message_id": 1,
                        "from": {"id": 123456789, "is_bot": False},
                        "chat": {"id": 123456789, "type": "private"},
                        "date": 1234567890,
                        "text": "Test message"
                    }
                }
                
                response = client.post('/', 
                                     json=payload,
                                     headers={'Content-Type': 'application/json'})
                
                assert response.status_code == 503
                data = json.loads(response.data)
                assert "Service unavailable" in data['error']


class TestOrchestratorToAgentIntegration(TestSystemIntegration):
    """Test integration between orchestrator and specialized agents"""
    
    def test_orchestrator_agent_routing(self, mock_orchestrator_config, mock_firestore_orchestrator):
        """Test orchestrator routing to specialized agents"""
        from orchestrator.app import app, Orchestrator
        app.config['TESTING'] = True
        
        orchestrator = Orchestrator()
        
        # Mock agent response
        with patch('orchestrator.app.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'response': 'Trámite information',
                'metadata': {'agent': 'tramites'}
            }
            mock_post.return_value = mock_response
            
            result = orchestrator.agent_router.route_to_agent(
                'tramite_buscar',
                'Necesito información sobre trámites',
                {'recent_messages': []}
            )
            
            assert 'response' in result
            assert result['response'] == 'Trámite information'
            
            # Verify correct agent was called
            assert mock_post.called
            call_args = mock_post.call_args
            assert 'http://localhost:8082/process' in call_args[0][0]  # URL
            assert call_args[1]['json']['intent'] == 'tramite_buscar'
    
    def test_orchestrator_agent_timeout_handling(self, mock_orchestrator_config, mock_firestore_orchestrator):
        """Test orchestrator handling of agent timeout"""
        from orchestrator.app import Orchestrator
        
        orchestrator = Orchestrator()
        
        with patch('orchestrator.app.requests.post') as mock_post:
            mock_post.side_effect = TimeoutError("Agent timeout")
            
            result = orchestrator.agent_router.route_to_agent(
                'tramite_buscar',
                'Test message',
                {'recent_messages': []}
            )
            
            assert 'error' in result
            assert result['error'] == 'Agent timeout'
            assert result['intent'] == 'tramite_buscar'
    
    def test_orchestrator_fallback_on_agent_failure(self, mock_orchestrator_config, mock_firestore_orchestrator):
        """Test orchestrator fallback behavior when agent fails"""
        from orchestrator.app import Orchestrator
        
        orchestrator = Orchestrator()
        
        # Mock intent classification
        with patch.object(orchestrator.intent_classifier, 'classify_intent') as mock_classify, \
             patch.object(orchestrator.agent_router, 'route_to_agent') as mock_route:
            
            mock_classify.return_value = {
                'intent': 'tramite_buscar',
                'confidence': 0.8,
                'reasoning': 'User is asking about procedures',
                'detected_keywords': ['trámite']
            }
            
            mock_route.return_value = {
                'error': 'Agent timeout',
                'intent': 'tramite_buscar'
            }
            
            result = orchestrator.process_request(
                'test-session',
                'test-user',
                'Necesito información sobre trámites'
            )
            
            # Should include error information but still return a response
            assert 'metadata' in result
            assert result['metadata']['intent'] == 'tramite_buscar'
            assert 'processing_time' in result['metadata']


class TestSessionManagementIntegration(TestSystemIntegration):
    """Test session management across components"""
    
    def test_session_creation_and_retrieval(self, mock_orchestrator_config, mock_firestore_orchestrator):
        """Test session creation and retrieval across requests"""
        from orchestrator.app import app
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            # First request - should create session
            with patch.object(mock_firestore_orchestrator.collection.return_value.document.return_value, 'get') as mock_get:
                mock_doc = Mock()
                mock_doc.exists = False
                mock_get.return_value = mock_doc
                
                response1 = client.post('/process', 
                                      json={
                                          'session_id': 'test-session',
                                          'user_id': 'test-user',
                                          'text': 'Hola'
                                      })
                
                # Should fail because session doesn't exist
                assert response1.status_code == 404
            
            # Create session manually
            session_data = {
                'user_id': 'test-user',
                'created_at': datetime.utcnow(),
                'last_active': datetime.utcnow(),
                'messages': [],
                'memory_summary': ''
            }
            mock_firestore_orchestrator.collection.return_value.document.return_value.to_dict.return_value = session_data
            mock_firestore_orchestrator.collection.return_value.document.return_value.exists = True
            
            # Second request - should work with existing session
            response2 = client.post('/process', 
                                  json={
                                      'session_id': 'test-session',
                                      'user_id': 'test-user',
                                      'text': 'Hola'
                                  })
            
            assert response2.status_code == 200
    
    def test_session_timeout_integration(self, mock_orchestrator_config, mock_firestore_orchestrator):
        """Test session timeout behavior"""
        from orchestrator.app import app
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            # Create expired session
            expired_time = datetime.utcnow() - timedelta(hours=25)  # Exceeds 24-hour timeout
            session_data = {
                'user_id': 'test-user',
                'created_at': datetime.utcnow(),
                'last_active': expired_time,
                'messages': [],
                'memory_summary': ''
            }
            mock_firestore_orchestrator.collection.return_value.document.return_value.to_dict.return_value = session_data
            mock_firestore_orchestrator.collection.return_value.document.return_value.exists = True
            
            response = client.post('/process', 
                                  json={
                                      'session_id': 'test-session',
                                      'user_id': 'test-user',
                                      'text': 'Hola'
                                  })
            
            assert response.status_code == 440
            data = json.loads(response.data)
            assert "Session expired" in data['error']


class TestEndToEndConversationFlow(TestSystemIntegration):
    """Test complete conversation flow"""
    
    def test_multi_turn_conversation(self, mock_webhook_config, mock_orchestrator_config, 
                                   mock_firestore_webhook, mock_firestore_orchestrator):
        """Test multi-turn conversation flow"""
        # Test complete flow: Webhook -> Orchestrator -> Agent -> Response
        from webhook.app import app as webhook_app
        from orchestrator.app import app as orchestrator_app, Orchestrator
        
        # Configure webhook app
        webhook_app.config['TESTING'] = True
        
        # Configure orchestrator app and mock its behavior
        orchestrator_app.config['TESTING'] = True
        orchestrator = Orchestrator()
        
        with webhook_app.test_client() as webhook_client, \
             orchestrator_app.test_client() as orchestrator_client:
            
            # Mock orchestrator response
            with patch('webhook.app.requests.post') as mock_webhook_to_orchestrator:
                mock_orchestrator_response = Mock()
                mock_orchestrator_response.status_code = 200
                mock_orchestrator_response.json.return_value = {
                    'response': 'Aquí está la información que solicitó',
                    'metadata': {
                        'intent': 'tramite_buscar',
                        'confidence': 0.85,
                        'processing_time': 1.2
                    }
                }
                mock_webhook_to_orchestrator.return_value = mock_orchestrator_response
                
                # Mock agent response in orchestrator
                with patch.object(orchestrator.agent_router, 'route_to_agent') as mock_agent_route:
                    mock_agent_response = Mock()
                    mock_agent_response.status_code = 200
                    mock_agent_response.json.return_value = {
                        'response': 'Aquí está la información que solicitó',
                        'metadata': {'agent': 'tramites'}
                    }
                    mock_agent_route.return_value = mock_agent_response
                    
                    # Send first message through webhook
                    payload1 = {
                        "update_id": 1,
                        "message": {
                            "message_id": 1,
                            "from": {"id": 123456789, "is_bot": False},
                            "chat": {"id": 123456789, "type": "private"},
                            "date": 1234567890,
                            "text": "Hola, necesito información sobre trámites"
                        }
                    }
                    
                    response1 = webhook_client.post('/', 
                                                  json=payload1,
                                                  headers={'Content-Type': 'application/json'})
                    
                    assert response1.status_code == 200
                    data1 = json.loads(response1.data)
                    assert 'session_id' in data1
                    
                    # Verify orchestrator was called with correct data
                    assert mock_webhook_to_orchestrator.called
                    webhook_call_args = mock_webhook_to_orchestrator.call_args[1]['json']
                    assert webhook_call_args['session_id'] == data1['session_id']
                    assert webhook_call_args['text'] == "Hola, necesito información sobre trámites"
                    
                    # Verify agent was called
                    assert mock_agent_route.called
                    agent_call_args = mock_agent_route.call_args
                    assert agent_call_args[0][0] == 'tramite_buscar'  # intent
                    assert agent_call_args[0][1] == "Hola, necesito información sobre trámites"  # user_message


class TestErrorPropagationIntegration(TestSystemIntegration):
    """Test error propagation across components"""
    
    def test_database_error_propagation(self, mock_webhook_config, mock_orchestrator_config):
        """Test that database errors are properly handled and propagated"""
        from webhook.app import app as webhook_app
        from orchestrator.app import app as orchestrator_app
        
        webhook_app.config['TESTING'] = True
        orchestrator_app.config['TESTING'] = True
        
        with webhook_app.test_client() as webhook_client, \
             orchestrator_app.test_client() as orchestrator_client:
            
            # Mock webhook Firestore error
            with patch('webhook.app.firestore.Client') as mock_webhook_firestore:
                mock_webhook_firestore.side_effect = Exception("Webhook DB Error")
                
                payload = {
                    "update_id": 1,
                    "message": {
                        "message_id": 1,
                        "from": {"id": 123456789, "is_bot": False},
                        "chat": {"id": 123456789, "type": "private"},
                        "date": 1234567890,
                        "text": "Test message"
                    }
                }
                
                response = webhook_client.post('/', 
                                             json=payload,
                                             headers={'Content-Type': 'application/json'})
                
                # Webhook should handle DB error gracefully
                assert response.status_code == 500
                data = json.loads(response.data)
                assert "Internal server error" in data['error']
    
    def test_llm_service_error_integration(self, mock_orchestrator_config, mock_firestore_orchestrator):
        """Test LLM service error handling in orchestrator"""
        from orchestrator.app import app, Orchestrator
        
        app.config['TESTING'] = True
        orchestrator = Orchestrator()
        
        with app.test_client() as client:
            # Mock LLM service failure
            with patch.object(orchestrator.intent_classifier, '_call_llm') as mock_llm:
                mock_llm.side_effect = Exception("LLM service unavailable")
                
                response = client.post('/process', 
                                     json={
                                         'session_id': 'test-session',
                                         'user_id': 'test-user',
                                         'text': 'Hola'
                                     })
                
                # Should handle LLM error gracefully
                assert response.status_code == 200  # Orchestrator should handle this internally
                data = json.loads(response.data)
                # The response should indicate an error or fallback behavior
                assert 'error' in data or 'clarificacion' in str(data).lower()


class TestPerformanceIntegration(TestSystemIntegration):
    """Test performance requirements in integrated system"""
    
    def test_end_to_end_response_time(self, mock_webhook_config, mock_orchestrator_config, 
                                    mock_firestore_webhook, mock_firestore_orchestrator):
        """Test end-to-end response time meets requirements"""
        from webhook.app import app as webhook_app
        from orchestrator.app import app as orchestrator_app, Orchestrator
        
        webhook_app.config['TESTING'] = True
        orchestrator_app.config['TESTING'] = True
        orchestrator = Orchestrator()
        
        with webhook_app.test_client() as webhook_client:
            # Mock fast responses from all services
            with patch('webhook.app.requests.post') as mock_webhook_request, \
                 patch.object(orchestrator.intent_classifier, 'classify_intent') as mock_classify, \
                 patch.object(orchestrator.agent_router, 'route_to_agent') as mock_route:
                
                # Mock fast orchestrator response
                mock_orchestrator_response = Mock()
                mock_orchestrator_response.status_code = 200
                mock_orchestrator_response.json.return_value = {
                    'response': 'Test response',
                    'metadata': {'processing_time': 0.5}
                }
                mock_webhook_request.return_value = mock_orchestrator_response
                
                # Mock fast intent classification
                mock_classify.return_value = {
                    'intent': 'tramite_buscar',
                    'confidence': 0.8,
                    'reasoning': 'Test',
                    'detected_keywords': ['test']
                }
                
                # Mock fast agent response
                mock_route.return_value = {
                    'response': 'Agent response',
                    'metadata': {'agent_time': 0.2}
                }
                
                payload = {
                    "update_id": 1,
                    "message": {
                        "message_id": 1,
                        "from": {"id": 123456789, "is_bot": False},
                        "chat": {"id": 123456789, "type": "private"},
                        "date": 1234567890,
                        "text": "Hola"
                    }
                }
                
                start_time = time.time()
                response = webhook_client.post('/', 
                                             json=payload,
                                             headers={'Content-Type': 'application/json'})
                end_time = time.time()
                
                total_time = end_time - start_time
                
                assert response.status_code == 200
                assert total_time < 3.0  # Total time should be under 3 seconds
                
                data = json.loads(response.data)
                assert 'processing_time' in data
                assert data['processing_time'] < 3.0


class TestSecurityIntegration(TestSystemIntegration):
    """Test security measures in integrated system"""
    
    def test_jwt_token_propagation(self, mock_webhook_config, mock_orchestrator_config, 
                                 mock_firestore_webhook, mock_firestore_orchestrator):
        """Test JWT token handling across components"""
        from webhook.app import app as webhook_app
        
        webhook_app.config['TESTING'] = True
        
        with app.test_client() as client:
            # Configure webhook to require auth
            mock_webhook_config.REQUIRE_AUTH = True
            
            # Create valid JWT token
            valid_token = jwt.encode(
                {'user_id': 'test-user'}, 
                'test-secret', 
                algorithm='HS256'
            )
            
            payload = {
                "update_id": 1,
                "message": {
                    "message_id": 1,
                    "from": {"id": 123456789, "is_bot": False},
                    "chat": {"id": 123456789, "type": "private"},
                    "date": 1234567890,
                    "text": "Hola"
                }
            }
            
            # Test with valid token
            response = client.post('/', 
                                 json=payload,
                                 headers={
                                     'Content-Type': 'application/json',
                                     'Authorization': f'Bearer {valid_token}'
                                 })
            
            assert response.status_code == 200
            
            # Test with invalid token
            response = client.post('/', 
                                 json=payload,
                                 headers={
                                     'Content-Type': 'application/json',
                                     'Authorization': 'Bearer invalid-token'
                                 })
            
            assert response.status_code == 401
    
    def test_session_isolation(self, mock_orchestrator_config, mock_firestore_orchestrator):
        """Test that sessions are properly isolated"""
        from orchestrator.app import app
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            # Mock different session data for different users
            def mock_session_data(session_id, user_id):
                mock_doc = Mock()
                mock_doc.to_dict.return_value = {
                    'user_id': user_id,
                    'created_at': datetime.utcnow(),
                    'last_active': datetime.utcnow(),
                    'messages': [],
                    'memory_summary': f'Session for {user_id}'
                }
                mock_doc.exists = True
                return mock_doc
            
            # Mock Firestore to return different data based on session ID
            def mock_document(session_id):
                if session_id == 'session-user1':
                    return mock_session_data('session-user1', 'user1')
                elif session_id == 'session-user2':
                    return mock_session_data('session-user2', 'user2')
                else:
                    mock_doc = Mock()
                    mock_doc.exists = False
                    return mock_doc
            
            mock_firestore_orchestrator.collection.return_value.document.side_effect = mock_document
            
            # Test user1 access
            response1 = client.post('/process', 
                                  json={
                                      'session_id': 'session-user1',
                                      'user_id': 'user1',
                                      'text': 'Hola'
                                  })
            
            assert response1.status_code == 200
            
            # Test user2 trying to access user1 session
            response2 = client.post('/process', 
                                  json={
                                      'session_id': 'session-user1',
                                      'user_id': 'user2',
                                      'text': 'Hola'
                                  })
            
            assert response2.status_code == 403
            data = json.loads(response2.data)
            assert "Unauthorized session access" in data['error']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])