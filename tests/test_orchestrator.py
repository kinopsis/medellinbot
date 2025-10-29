#!/usr/bin/env python3
"""
Comprehensive test suite for MedellínBot Orchestrator
Tests intent classification, agent routing, session management, and error handling
"""

import pytest
import json
import time
import jwt
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from orchestrator.app import app, Config, Orchestrator, IntentClassifier, ContextManager, AgentRouter


class TestOrchestratorComponents:
    """Base test class for orchestrator components"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def valid_session_data(self):
        """Valid session data"""
        return {
            'session_id': 'test-session-123',
            'user_id': 'test-user-456',
            'chat_id': 'test-chat-789',
            'text': 'Hola, necesito información sobre trámites',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @pytest.fixture
    def mock_firestore(self):
        """Mock Google Firestore"""
        with patch('orchestrator.app.firestore.Client') as mock_client:
            mock_instance = Mock()
            mock_doc = Mock()
            mock_doc.to_dict.return_value = {
                'user_id': 'test-user-456',
                'created_at': datetime.utcnow(),
                'last_active': datetime.utcnow(),
                'messages': [],
                'memory_summary': ''
            }
            mock_doc.exists = True
            mock_instance.collection.return_value.document.return_value = mock_doc
            mock_client.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def mock_storage(self):
        """Mock Google Cloud Storage"""
        with patch('orchestrator.app.storage.Client') as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            yield mock_instance


class TestSessionManagement(TestOrchestratorComponents):
    """Test session management functionality"""
    
    def test_session_validation_decorator(self, client, valid_session_data, mock_firestore):
        """Test session validation decorator"""
        # Test missing session_id
        response = client.post('/process', 
                             json={'user_id': 'test-user'})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Missing session_id or user_id" in data['error']
        
        # Test missing user_id
        response = client.post('/process', 
                             json={'session_id': 'test-session'})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Missing session_id or user_id" in data['error']
    
    def test_session_not_found(self, client, valid_session_data, mock_firestore):
        """Test handling of non-existent session"""
        # Configure session to not exist
        mock_firestore.collection.return_value.document.return_value.exists = False
        
        response = client.post('/process', json=valid_session_data)
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "Session not found" in data['error']
    
    def test_session_timeout(self, client, valid_session_data, mock_firestore):
        """Test session timeout handling"""
        # Configure session with expired last_active
        expired_time = datetime.utcnow() - timedelta(hours=Config.SESSION_TIMEOUT_HOURS + 1)
        mock_firestore.collection.return_value.document.return_value.to_dict.return_value = {
            'user_id': 'test-user-456',
            'created_at': datetime.utcnow(),
            'last_active': expired_time,
            'messages': [],
            'memory_summary': ''
        }
        
        response = client.post('/process', json=valid_session_data)
        assert response.status_code == 440
        data = json.loads(response.data)
        assert "Session expired" in data['error']
    
    def test_unauthorized_session_access(self, client, valid_session_data, mock_firestore):
        """Test unauthorized session access"""
        # Configure session with different user_id
        mock_firestore.collection.return_value.document.return_value.to_dict.return_value = {
            'user_id': 'different-user',
            'created_at': datetime.utcnow(),
            'last_active': datetime.utcnow(),
            'messages': [],
            'memory_summary': ''
        }
        
        response = client.post('/process', json=valid_session_data)
        assert response.status_code == 403
        data = json.loads(response.data)
        assert "Unauthorized session access" in data['error']


class TestIntentClassifier(TestOrchestratorComponents):
    """Test intent classification functionality"""
    
    @pytest.fixture
    def intent_classifier(self):
        """Create intent classifier instance"""
        return IntentClassifier()
    
    def test_intent_classification_success(self, intent_classifier):
        """Test successful intent classification"""
        with patch.object(intent_classifier, '_call_llm') as mock_llm:
            mock_llm.return_value = json.dumps({
                'intent': 'tramite_buscar',
                'confidence': 0.85,
                'reasoning': 'User is asking about procedures',
                'detected_keywords': ['trámite', 'información']
            })
            
            result = intent_classifier.classify_intent("Necesito información sobre trámites")
            
            assert result['intent'] == 'tramite_buscar'
            assert result['confidence'] == 0.85
            assert 'reasoning' in result
            assert 'detected_keywords' in result
    
    def test_intent_classification_low_confidence(self, intent_classifier):
        """Test intent classification with low confidence"""
        with patch.object(intent_classifier, '_call_llm') as mock_llm:
            mock_llm.return_value = json.dumps({
                'intent': 'tramite_buscar',
                'confidence': 0.3,
                'reasoning': 'Low confidence classification',
                'detected_keywords': ['trámite']
            })
            
            result = intent_classifier.classify_intent("No estoy seguro de lo que necesito")
            
            assert result['intent'] == 'clarificacion'
            assert result['confidence'] == 0.3
    
    def test_intent_classification_error_handling(self, intent_classifier):
        """Test intent classification error handling"""
        with patch.object(intent_classifier, '_call_llm') as mock_llm:
            mock_llm.side_effect = Exception("LLM service unavailable")
            
            result = intent_classifier.classify_intent("Hola")
            
            assert result['intent'] == 'clarificacion'
            assert result['confidence'] == 0.0
            assert 'Error en clasificación' in result['reasoning']
    
    def test_llm_response_parsing(self, intent_classifier):
        """Test LLM response parsing"""
        # Test valid JSON response
        valid_response = json.dumps({
            'intent': 'pqrsd_crear',
            'confidence': 0.9,
            'reasoning': 'User wants to create a complaint',
            'detected_keywords': ['queja', 'reclamo']
        })
        
        result = intent_classifier._parse_intent_response(valid_response)
        assert result['intent'] == 'pqrsd_crear'
        
        # Test invalid JSON response
        with pytest.raises(ValueError):
            intent_classifier._parse_intent_response("invalid json")
        
        # Test missing required fields
        with pytest.raises(ValueError):
            intent_classifier._parse_intent_response(json.dumps({'intent': 'test'}))


class TestContextManager(TestOrchestratorComponents):
    """Test context management functionality"""
    
    @pytest.fixture
    def context_manager(self):
        """Create context manager instance"""
        return ContextManager()
    
    def test_get_conversation_context(self, context_manager, mock_firestore):
        """Test getting conversation context"""
        # Configure mock session data
        mock_firestore.collection.return_value.document.return_value.to_dict.return_value = {
            'messages': [
                {'text': 'Hola', 'role': 'user', 'timestamp': '2024-01-01T10:00:00'},
                {'text': 'Bienvenido', 'role': 'agent', 'timestamp': '2024-01-01T10:01:00'}
            ],
            'memory_summary': 'User is asking about municipal services',
            'user_preferences': {'language': 'es'},
            'context_relevance_score': 0.8
        }
        
        context = context_manager.get_conversation_context('test-session', 'Hola')
        
        assert 'recent_messages' in context
        assert 'memory_summary' in context
        assert 'user_preferences' in context
        assert 'context_relevance_score' in context
        assert len(context['recent_messages']) == 3  # Includes current message
    
    def test_context_truncation(self, context_manager, mock_firestore):
        """Test context truncation when exceeding max history"""
        # Create session with more messages than max_history
        many_messages = [{'text': f'Message {i}', 'role': 'user', 'timestamp': f'2024-01-01T10:{i:02d}:00'} 
                        for i in range(60)]  # More than default max_history of 50
        
        mock_firestore.collection.return_value.document.return_value.to_dict.return_value = {
            'messages': many_messages,
            'memory_summary': '',
            'user_preferences': {},
            'context_relevance_score': 0.0
        }
        
        context = context_manager.get_conversation_context('test-session', 'New message')
        
        # Should be truncated to max_history + 1 (current message)
        assert len(context['recent_messages']) <= context_manager.max_history + 1
    
    def test_update_session_context(self, context_manager, mock_firestore):
        """Test updating session context"""
        new_messages = [
            {'text': 'Hola', 'role': 'user', 'timestamp': datetime.utcnow().isoformat()}
        ]
        
        context_manager.update_session_context('test-session', new_messages, 'Test summary')
        
        # Verify update was called
        mock_firestore.collection.return_value.document.return_value.update.assert_called_once()
        args = mock_firestore.collection.return_value.document.return_value.update.call_args[0][0]
        assert 'messages' in args
        assert 'memory_summary' in args
        assert 'last_active' in args


class TestAgentRouter(TestOrchestratorComponents):
    """Test agent routing functionality"""
    
    @pytest.fixture
    def agent_router(self):
        """Create agent router instance"""
        return AgentRouter()
    
    def test_route_to_agent_success(self, agent_router):
        """Test successful agent routing"""
        with patch('orchestrator.app.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'response': 'Agent response',
                'metadata': {'agent': 'tramites'}
            }
            mock_post.return_value = mock_response
            
            result = agent_router.route_to_agent(
                'tramite_buscar',
                'Necesito información sobre trámites',
                {'recent_messages': []}
            )
            
            assert 'response' in result
            assert result['response'] == 'Agent response'
            mock_post.assert_called_once()
    
    def test_route_to_unknown_agent(self, agent_router):
        """Test routing to unknown agent"""
        result = agent_router.route_to_agent(
            'unknown_intent',
            'Test message',
            {'recent_messages': []}
        )
        
        assert 'error' in result
        assert result['error'] == 'No agent available for intent'
        assert result['intent'] == 'unknown_intent'
    
    def test_agent_timeout_handling(self, agent_router):
        """Test agent timeout handling"""
        with patch('orchestrator.app.requests.post') as mock_post:
            mock_post.side_effect = TimeoutError("Agent timeout")
            
            result = agent_router.route_to_agent(
                'tramite_buscar',
                'Test message',
                {'recent_messages': []}
            )
            
            assert 'error' in result
            assert result['error'] == 'Agent timeout'
    
    def test_agent_connection_error_handling(self, agent_router):
        """Test agent connection error handling"""
        with patch('orchestrator.app.requests.post') as mock_post:
            mock_post.side_effect = ConnectionError("Connection failed")
            
            result = agent_router.route_to_agent(
                'tramite_buscar',
                'Test message',
                {'recent_messages': []}
            )
            
            assert 'error' in result
            assert result['error'] == 'Agent unavailable'


class TestOrchestratorMainFlow(TestOrchestratorComponents):
    """Test main orchestrator flow"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance"""
        return Orchestrator()
    
    def test_process_request_success(self, orchestrator, mock_firestore):
        """Test successful request processing"""
        with patch.object(orchestrator.intent_classifier, 'classify_intent') as mock_classify, \
             patch.object(orchestrator.agent_router, 'route_to_agent') as mock_route:
            
            # Mock intent classification
            mock_classify.return_value = {
                'intent': 'tramite_buscar',
                'confidence': 0.85,
                'reasoning': 'User is asking about procedures',
                'detected_keywords': ['trámite']
            }
            
            # Mock agent routing
            mock_route.return_value = {
                'response': 'Here is the information about trámites...',
                'metadata': {'agent_response_time': 1.5}
            }
            
            result = orchestrator.process_request(
                'test-session',
                'test-user',
                'Necesito información sobre trámites'
            )
            
            assert 'response' in result
            assert 'metadata' in result
            assert result['metadata']['intent'] == 'tramite_buscar'
            assert result['metadata']['confidence'] == 0.85
            assert 'processing_time' in result['metadata']
    
    def test_process_request_clarification(self, orchestrator, mock_firestore):
        """Test request requiring clarification"""
        with patch.object(orchestrator.intent_classifier, 'classify_intent') as mock_classify, \
             patch.object(orchestrator, '_handle_clarification') as mock_handle:
            
            # Mock low confidence classification
            mock_classify.return_value = {
                'intent': 'clarificacion',
                'confidence': 0.3,
                'reasoning': 'Low confidence',
                'detected_keywords': []
            }
            
            mock_handle.return_value = {
                'questions': ['¿Podría ser más específico?'],
                'suggested_intents': ['tramite_buscar']
            }
            
            result = orchestrator.process_request(
                'test-session',
                'test-user',
                'No estoy seguro de lo que necesito'
            )
            
            assert 'questions' in result
            assert result['questions'][0] == '¿Podría ser más específico?'
    
    def test_process_request_error_handling(self, orchestrator):
        """Test error handling in request processing"""
        with patch.object(orchestrator, '_update_session_after_response') as mock_update:
            mock_update.side_effect = Exception("Session update failed")
            
            result = orchestrator.process_request(
                'test-session',
                'test-user',
                'Test message'
            )
            
            assert 'error' in result
            assert result['error'] == 'Internal processing error'
            assert 'metadata' in result


class TestHealthAndMonitoring(TestOrchestratorComponents):
    """Test health check and monitoring"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'medellinbot-orchestrator'
        assert 'components' in data
    
    def test_get_session_endpoint(self, client, mock_firestore):
        """Test get session endpoint"""
        # Configure mock session
        mock_firestore.collection.return_value.document.return_value.to_dict.return_value = {
            'user_id': 'test-user',
            'created_at': datetime.utcnow(),
            'last_active': datetime.utcnow(),
            'messages': [{'text': 'test', 'role': 'user', 'timestamp': datetime.utcnow()}],
            'memory_summary': 'Test summary'
        }
        
        response = client.get('/session/test-session')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['session_id'] == 'test-session'
        assert data['user_id'] == 'test-user'
        assert data['message_count'] == 1


class TestPerformanceRequirements(TestOrchestratorComponents):
    """Test performance requirements"""
    
    def test_intent_classification_performance(self, orchestrator):
        """Test intent classification meets performance requirements"""
        start_time = time.time()
        
        # Mock the LLM call to avoid network delay in test
        with patch.object(orchestrator.intent_classifier, '_call_llm') as mock_llm:
            mock_llm.return_value = json.dumps({
                'intent': 'tramite_buscar',
                'confidence': 0.8,
                'reasoning': 'Test',
                'detected_keywords': ['test']
            })
            
            result = orchestrator.intent_classifier.classify_intent("Test message")
        
        processing_time = time.time() - start_time
        
        assert processing_time < 3.0  # Should be well under 3 seconds
        assert result['intent'] == 'tramite_buscar'
    
    def test_overall_processing_performance(self, orchestrator, mock_firestore):
        """Test overall processing meets performance requirements"""
        start_time = time.time()
        
        with patch.object(orchestrator.intent_classifier, 'classify_intent') as mock_classify, \
             patch.object(orchestrator.agent_router, 'route_to_agent') as mock_route:
            
            mock_classify.return_value = {
                'intent': 'tramite_buscar',
                'confidence': 0.8,
                'reasoning': 'Test',
                'detected_keywords': ['test']
            }
            
            mock_route.return_value = {
                'response': 'Test response',
                'metadata': {'test': True}
            }
            
            result = orchestrator.process_request(
                'test-session',
                'test-user',
                'Test message'
            )
        
        processing_time = time.time() - start_time
        
        assert processing_time < 3.0  # Should be well under 3 seconds
        assert 'metadata' in result
        assert 'processing_time' in result['metadata']
        assert result['metadata']['processing_time'] < 3.0


class TestSecurityAndValidation(TestOrchestratorComponents):
    """Test security and input validation"""
    
    def test_session_id_validation(self, client, mock_firestore):
        """Test session ID format validation"""
        # Test with invalid session ID format
        response = client.post('/process', 
                             json={
                                 'session_id': 'invalid-session-id',
                                 'user_id': 'test-user',
                                 'text': 'Test message'
                             })
        
        # Should fail session validation
        assert response.status_code != 200
    
    def test_user_id_validation(self, client, mock_firestore):
        """Test user ID validation"""
        # Configure session with different user_id
        mock_firestore.collection.return_value.document.return_value.to_dict.return_value = {
            'user_id': 'different-user',
            'created_at': datetime.utcnow(),
            'last_active': datetime.utcnow(),
            'messages': [],
            'memory_summary': ''
        }
        
        response = client.post('/process', 
                             json={
                                 'session_id': 'test-session',
                                 'user_id': 'wrong-user',
                                 'text': 'Test message'
                             })
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert "Unauthorized session access" in data['error']
    
    def test_input_sanitization(self, orchestrator):
        """Test input sanitization"""
        # Test with potentially malicious input
        malicious_input = "<script>alert('xss')</script> or 1=1--"
        
        with patch.object(orchestrator.intent_classifier, 'classify_intent') as mock_classify:
            mock_classify.return_value = {
                'intent': 'clarificacion',
                'confidence': 0.5,
                'reasoning': 'Input needs clarification',
                'detected_keywords': []
            }
            
            result = orchestrator.process_request(
                'test-session',
                'test-user',
                malicious_input
            )
            
            # Should handle malicious input gracefully
            assert 'error' not in result or result['error'] != 'Internal server error'


class TestErrorResilience(TestOrchestratorComponents):
    """Test error resilience and recovery"""
    
    def test_firestore_unavailable(self, client, valid_session_data):
        """Test behavior when Firestore is unavailable"""
        with patch('orchestrator.app.firestore.Client') as mock_firestore:
            mock_firestore.side_effect = Exception("Firestore unavailable")
            
            response = client.post('/process', json=valid_session_data)
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert "Failed to retrieve session" in data['error']
    
    def test_llm_service_unavailable(self, orchestrator):
        """Test behavior when LLM service is unavailable"""
        with patch.object(orchestrator.intent_classifier, '_call_llm') as mock_llm:
            mock_llm.side_effect = Exception("LLM service down")
            
            result = orchestrator.process_request(
                'test-session',
                'test-user',
                'Test message'
            )
            
            # Should handle LLM failure gracefully
            assert 'error' in result
            assert result['error'] == 'Internal processing error'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])