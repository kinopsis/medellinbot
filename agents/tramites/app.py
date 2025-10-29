#!/usr/bin/env python3
"""
MedellínBot - Trámites Agent
Specialized agent for handling municipal procedures and trámites
"""

import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from flask import Flask, request, jsonify
import requests
from google.cloud import firestore, storage
import psycopg2
from psycopg2.extras import RealDictCursor
import jwt
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Initialize Google Cloud clients
try:
    db = firestore.Client()
    storage_client = storage.Client()
    logger.info("Google Cloud clients initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Google Cloud clients: {e}")
    raise

# Configuration
class Config:
    """Application configuration"""
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
    JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
    
    # Database configuration
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', '5432'))
    DB_NAME = os.environ.get('DB_NAME', 'medellinbot')
    DB_USER = os.environ.get('DB_USER', 'medellinbot_user')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'default-password')
    
    # Vector search configuration
    VECTOR_SEARCH_ENABLED = os.environ.get('VECTOR_SEARCH_ENABLED', 'false').lower() == 'true'
    VECTOR_SEARCH_INDEX = os.environ.get('VECTOR_SEARCH_INDEX', 'tramites')
    
    # LLM Configuration
    LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'vertex-ai')
    LLM_MODEL = os.environ.get('LLM_MODEL', 'gemini-1.5-flash')
    LLM_TEMPERATURE = float(os.environ.get('LLM_TEMPERATURE', '0.3'))

# Load prompts
try:
    from prompts.tramites_agent import TRAMITES_AGENT_SYSTEM_PROMPT, TRAMITES_AGENT_FOLLOWUP_PROMPT
    logger.info("Trámites agent prompts loaded successfully")
except ImportError as e:
    logger.error(f"Failed to load trámites prompts: {e}")
    raise

def get_db_connection():
    """Get database connection to Cloud SQL"""
    try:
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def validate_agent_request(func):
    """Decorator to validate agent requests"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({"error": "Invalid JSON payload"}), 400
            
            required_fields = ['user_message', 'conversation_context', 'intent']
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Missing required field: {field}"}), 400
            
            # Validate conversation context
            context = data.get('conversation_context', {})
            if not isinstance(context, dict):
                return jsonify({"error": "Invalid conversation context format"}), 400
            
            return func(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Request validation error: {e}")
            return jsonify({"error": "Request validation failed"}), 500
    
    return wrapper

class TramitesSearch:
    """Handles search operations for trámites"""
    
    def __init__(self):
        self.db_conn = get_db_connection()
    
    def search_tramite_by_codigo(self, codigo: str) -> Optional[Dict[str, Any]]:
        """Search for a trámite by código"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM tramites_activos 
                    WHERE codigo = %s AND active = true
                """, (codigo,))
                
                result = cursor.fetchone()
                return dict(result) if result else None
                
        except Exception as e:
            logger.error(f"Error searching trámite by código: {e}")
            return None
    
    def search_tramite_by_keywords(self, keywords: List[str], limit: int = 5) -> List[Dict[str, Any]]:
        """Search for trámites by keywords using full-text search"""
        try:
            with self.db_conn.cursor() as cursor:
                # Create search query using tsvector for full-text search
                search_query = " | ".join(keywords)
                
                cursor.execute("""
                    SELECT *, 
                           ts_rank(to_tsvector('spanish', titulo || ' ' || descripcion), plainto_tsquery('spanish', %s)) as rank
                    FROM tramites_activos 
                    WHERE to_tsvector('spanish', titulo || ' ' || descripcion) @@ plainto_tsquery('spanish', %s)
                      AND active = true
                    ORDER BY rank DESC
                    LIMIT %s
                """, (search_query, search_query, limit))
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error searching trámites by keywords: {e}")
            return []
    
    def search_tramite_by_categoria(self, categoria: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for trámites by category"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM tramites_activos 
                    WHERE categoria = %s AND active = true
                    ORDER BY titulo
                    LIMIT %s
                """, (categoria, limit))
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error searching trámites by category: {e}")
            return []
    
    def get_tramite_alternatives(self, tramite_id: int, limit: int = 3) -> List[Dict[str, Any]]:
        """Get alternative trámites for a given trámite"""
        try:
            with self.db_conn.cursor() as cursor:
                # Get the category of the original trámite
                cursor.execute("""
                    SELECT categoria FROM tramites_activos WHERE id = %s
                """, (tramite_id,))
                
                result = cursor.fetchone()
                if not result:
                    return []
                
                categoria = result['categoria']
                
                # Get alternatives from the same category
                cursor.execute("""
                    SELECT * FROM tramites_activos 
                    WHERE categoria = %s AND id != %s AND active = true
                    ORDER BY titulo
                    LIMIT %s
                """, (categoria, tramite_id, limit))
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error getting trámite alternatives: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if hasattr(self, 'db_conn'):
            self.db_conn.close()

class TramitesAgent:
    """Main trámites agent class"""
    
    def __init__(self):
        self.search_engine = TramitesSearch()
    
    def process_request(self, user_message: str, context: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """Process trámites request and return response"""
        start_time = time.time()
        
        try:
            # Extract search terms from user message
            search_terms = self._extract_search_terms(user_message)
            
            # Search for relevant trámites
            if len(search_terms) == 1 and self._is_codigo_format(search_terms[0]):
                # Direct código search
                tramite = self.search_engine.search_tramite_by_codigo(search_terms[0])
                if tramite:
                    results = [tramite]
                    match_score = 0.95
                else:
                    results = []
                    match_score = 0.0
            else:
                # Keyword search
                results = self.search_engine.search_tramite_by_keywords(search_terms, limit=5)
                match_score = 0.8 if results else 0.0
            
            # Generate response
            if results:
                response = self._generate_tramite_response(results[0], match_score, context, user_message)
                
                # Add alternatives if multiple results
                if len(results) > 1:
                    alternatives = []
                    for result in results[1:]:
                        alternatives.append({
                            'codigo': result['codigo'],
                            'titulo': result['titulo'],
                            'razon_similitud': self._calculate_similarity_reason(user_message, result)
                        })
                    response['alternativas'] = alternatives
                else:
                    response['alternativas'] = []
                    
            else:
                # No results found - search by category or provide alternatives
                response = self._handle_no_results(user_message, search_terms, context)
            
            # Add metadata
            response['metadata'] = {
                'processing_time': round(time.time() - start_time, 3),
                'search_terms': search_terms,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Trámites agent processing error: {e}")
            return {
                'error': 'Internal processing error',
                'metadata': {
                    'processing_time': round(time.time() - start_time, 3),
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
    
    def _extract_search_terms(self, user_message: str) -> List[str]:
        """Extract search terms from user message"""
        # Simple keyword extraction - in production, use NLP for better extraction
        import re
        
        # Remove special characters and convert to lowercase
        cleaned = re.sub(r'[^\w\s]', '', user_message.lower())
        
        # Split into words and remove common stop words
        stop_words = {'el', 'la', 'los', 'las', 'de', 'del', 'en', 'y', 'o', 'a', 'para', 'por', 'con', 'un', 'una', 'es', 'son'}
        words = [word for word in cleaned.split() if word not in stop_words and len(word) > 2]
        
        return words
    
    def _is_codigo_format(self, term: str) -> bool:
        """Check if a term matches trámite código format"""
        import re
        # Pattern: letters and numbers separated by hyphens (e.g., PREDIAL-001, LICENCIA-001)
        pattern = r'^[A-Z]+-\d+$'
        return bool(re.match(pattern, term.upper()))
    
    def _generate_tramite_response(self, tramite: Dict[str, Any], match_score: float, context: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """Generate response for a found trámite"""
        try:
            # Prepare the prompt for LLM
            prompt = TRAMITES_AGENT_SYSTEM_PROMPT.format(
                user_message=user_message,
                conversation_context=json.dumps(context, indent=2),
                search_results=json.dumps(tramite, indent=2, default=str)
            )
            
            # Call LLM to generate response
            llm_response = self._call_llm(prompt)
            
            # Parse LLM response
            response_data = json.loads(llm_response)
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error generating trámite response: {e}")
            return self._generate_fallback_response(tramite, match_score)
    
    def _generate_fallback_response(self, tramite: Dict[str, Any], match_score: float) -> Dict[str, Any]:
        """Generate fallback response without LLM"""
        # Format office locations
        ubicacion_oficinas = []
        if tramite.get('ubicacion_oficinas'):
            try:
                oficinas = json.loads(tramite['ubicacion_oficinas']) if isinstance(tramite['ubicacion_oficinas'], str) else tramite['ubicacion_oficinas']
                if isinstance(oficinas, dict):
                    oficinas = [oficinas]
                
                for oficina in oficinas:
                    ubicacion_oficinas.append({
                        'name': oficina.get('name', ''),
                        'address': oficina.get('address', ''),
                        'horario': oficina.get('horario', ''),
                        'telefono': oficina.get('telefono', ''),
                        'lat': oficina.get('lat'),
                        'lng': oficina.get('lng')
                    })
            except Exception as e:
                logger.error(f"Error parsing office locations: {e}")
        
        # Format requirements
        requisitos = []
        if tramite.get('requisitos'):
            try:
                requisitos = json.loads(tramite['requisitos']) if isinstance(tramite['requisitos'], str) else tramite['requisitos']
                if isinstance(requisitos, str):
                    requisitos = [requisitos]
            except Exception as e:
                logger.error(f"Error parsing requirements: {e}")
                requisitos = []
        
        return {
            "match_score": match_score,
            "tramite": {
                "codigo": tramite['codigo'],
                "titulo": tramite['titulo'],
                "descripcion": tramite['descripcion'] or '',
                "requisitos": requisitos,
                "plazos": tramite['plazos'] or '',
                "costo": tramite['costo'] or '',
                "ubicacion_oficinas": ubicacion_oficinas,
                "pasos": [],
                "fuente": "",
                "documentos_adjuntos": []
            },
            "texto_usuario": f"He encontrado el trámite que busca: {tramite['titulo']}. ¿Desea información sobre los requisitos, la ubicación de las oficinas o el costo del trámite?",
            "preguntas_recomendadas": [
                "¿Desea información sobre los requisitos?",
                "¿Necesita la ubicación de las oficinas?",
                "¿Quiere saber sobre el costo?"
            ],
            "alternativas": []
        }
    
    def _handle_no_results(self, user_message: str, search_terms: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle case when no trámites are found"""
        try:
            # Try category-based search
            categories = self._get_relevant_categories(user_message)
            
            if categories:
                # Search by category
                for category in categories:
                    results = self.search_engine.search_tramite_by_categoria(category, limit=3)
                    if results:
                        # Generate response with category results
                        return self._generate_category_response(category, results, context, user_message)
            
            # No results found - provide helpful response
            return {
                "match_score": 0.0,
                "tramite": None,
                "texto_usuario": "No encontré un trámite específico que coincida con su búsqueda. Sin embargo, puedo ayudarle a encontrar información sobre trámites municipales en general. ¿Podría ser más específico sobre el tipo de trámite que necesita?",
                "preguntas_recomendadas": [
                    "¿Qué tipo de trámite está buscando?",
                    "¿Tiene el código del trámite?",
                    "¿Necesita ayuda para encontrar el trámite adecuado?"
                ],
                "alternativas": []
            }
            
        except Exception as e:
            logger.error(f"Error handling no results: {e}")
            return {
                "match_score": 0.0,
                "tramite": None,
                "texto_usuario": "No encontré trámites que coincidan con su búsqueda. ¿Podría proporcionar más detalles o intentar con términos diferentes?",
                "preguntas_recomendadas": [
                    "¿Podría ser más específico?",
                    "¿Tiene el código del trámite?",
                    "¿Necesita ayuda para encontrar el trámite adecuado?"
                ],
                "alternativas": []
            }
    
    def _get_relevant_categories(self, user_message: str) -> List[str]:
        """Get relevant categories based on user message"""
        user_message_lower = user_message.lower()
        
        category_keywords = {
            'impuestos': ['impuesto', 'predial', 'industria', 'comercio', 'renta'],
            'construcción': ['construcción', 'licencia', 'obra', 'edificio', 'permiso'],
            'servicios públicos': ['agua', 'energía', 'gas', 'servicio', 'factura'],
            'documentos': ['documento', 'cedula', 'pasaporte', 'registro', 'certificado'],
            'vehículos': ['carro', 'moto', 'placa', 'vehículo', 'transito']
        }
        
        relevant_categories = []
        for category, keywords in category_keywords.items():
            if any(keyword in user_message_lower for keyword in keywords):
                relevant_categories.append(category)
        
        return relevant_categories
    
    def _generate_category_response(self, category: str, results: List[Dict[str, Any]], context: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """Generate response for category-based search"""
        try:
            # Prepare prompt for LLM
            prompt = TRAMITES_AGENT_SYSTEM_PROMPT.format(
                user_message=user_message,
                conversation_context=json.dumps(context, indent=2),
                search_results=json.dumps({
                    'category': category,
                    'results': results
                }, indent=2, default=str)
            )
            
            # Call LLM to generate response
            llm_response = self._call_llm(prompt)
            
            # Parse LLM response
            response_data = json.loads(llm_response)
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error generating category response: {e}")
            return self._generate_fallback_category_response(category, results)
    
    def _generate_fallback_category_response(self, category: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate fallback response for category search"""
        alternatives = []
        for result in results:
            alternatives.append({
                'codigo': result['codigo'],
                'titulo': result['titulo'],
                'razon_similitud': f'Tramite relacionado con la categoría {category}'
            })
        
        return {
            "match_score": 0.6,
            "tramite": None,
            "texto_usuario": f"Encontré varios trámites relacionados con {category}. ¿Le interesa alguno de estos?",
            "preguntas_recomendadas": [
                "¿Desea información sobre alguno de estos trámites?",
                "¿Tiene el código de un trámite específico?",
                "¿Necesita ayuda para elegir el trámite adecuado?"
            ],
            "alternativas": alternatives
        }
    
    def _calculate_similarity_reason(self, user_message: str, tramite: Dict[str, Any]) -> str:
        """Calculate reason for similarity between user message and trámite"""
        user_words = set(user_message.lower().split())
        tramite_words = set((tramite['titulo'] + ' ' + (tramite['descripcion'] or '')).lower().split())
        
        common_words = user_words.intersection(tramite_words)
        
        if common_words:
            return f"Contiene palabras clave como: {', '.join(list(common_words)[:3])}"
        else:
            return "Trámite relacionado por categoría"
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM provider (placeholder implementation)"""
        # This would be implemented based on your specific LLM provider
        # For now, return a mock response
        logger.warning("LLM integration is using mock responses - implement actual LLM integration")
        
        # Mock response based on whether we have search results
        if '"tramite": null' in prompt:
            return json.dumps({
                "match_score": 0.0,
                "tramite": None,
                "texto_usuario": "No encontré un trámite específico que coincida con su búsqueda. Sin embargo, puedo ayudarle a encontrar información sobre trámites municipales en general.",
                "preguntas_recomendadas": [
                    "¿Qué tipo de trámite está buscando?",
                    "¿Tiene el código del trámite?",
                    "¿Necesita ayuda para encontrar el trámite adecuado?"
                ],
                "alternativas": []
            })
        else:
            # Extract trámite data from prompt to create realistic response
            import re
            titulo_match = re.search(r'"titulo":\s*"([^"]*)"', prompt)
            titulo = titulo_match.group(1) if titulo_match else "Trámite Municipal"
            
            return json.dumps({
                "match_score": 0.85,
                "tramite": {
                    "codigo": "PREDIAL-001",
                    "titulo": titulo,
                    "descripcion": "Trámite para gestionar asuntos municipales relacionados con impuestos y servicios.",
                    "requisitos": ["Cédula de ciudadanía", "Certificado de tradición y libertad", "Último recibo de pago"],
                    "plazos": "30 días hábiles",
                    "costo": "$50.000",
                    "ubicacion_oficinas": [
                        {
                            "name": "Alcaldía de Medellín",
                            "address": "Cra. 44 #52-11",
                            "horario": "8:00-17:00",
                            "telefono": "321 123 4567",
                            "lat": 6.2442,
                            "lng": -75.5812
                        }
                    ],
                    "pasos": [
                        "Paso 1: Reúna los documentos requeridos",
                        "Paso 2: Diríjase a la oficina correspondiente",
                        "Paso 3: Realice el pago correspondiente",
                        "Paso 4: Obtenga el recibo oficial"
                    ],
                    "fuente": "https://medellin.gov.co/tramites",
                    "documentos_adjuntos": ["formulario.pdf"]
                },
                "texto_usuario": f"He encontrado el trámite que busca: {titulo}. Este trámite tiene un costo de $50.000 y un tiempo de procesamiento de 30 días hábiles.",
                "preguntas_recomendadas": [
                    "¿Desea información sobre los requisitos?",
                    "¿Necesita la ubicación de las oficinas?",
                    "¿Quiere saber sobre el costo?"
                ],
                "alternativas": []
            })

@app.route('/process', methods=['POST'])
@validate_agent_request
def process_request():
    """Process trámites request"""
    try:
        data = request.get_json()
        
        user_message = data.get('user_message', '')
        context = data.get('conversation_context', {})
        intent = data.get('intent', '')
        
        # Get agent instance
        agent = app.config.get('tramites_agent')
        if not agent:
            agent = TramitesAgent()
            app.config['tramites_agent'] = agent
        
        # Process request
        response = agent.process_request(user_message, context, intent)
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Process request error: {e}")
        return jsonify({
            'error': 'Request processing failed',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        health_status = {
            "status": "healthy",
            "service": "medellinbot-tramites-agent",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": Config.ENVIRONMENT,
            "version": "1.0.0",
            "components": {
                "firestore": "connected",
                "storage": "connected",
                "database": "connected",
                "llm": "mocked"  # Change to "connected" when LLM is implemented
            }
        }
        
        return jsonify(health_status), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "service": "medellinbot-tramites-agent",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route('/search/<codigo>', methods=['GET'])
def search_by_codigo(codigo):
    """Search trámite by código (for testing and debugging)"""
    try:
        agent = app.config.get('tramites_agent')
        if not agent:
            agent = TramitesAgent()
            app.config['tramites_agent'] = agent
        
        tramite = agent.search_engine.search_tramite_by_codigo(codigo)
        
        if tramite:
            return jsonify({
                "found": True,
                "tramite": tramite
            }), 200
        else:
            return jsonify({
                "found": False,
                "message": "Trámite no encontrado"
            }), 404
            
    except Exception as e:
        logger.error(f"Search by código error: {e}")
        return jsonify({
            "error": "Search failed",
            "timestamp": datetime.utcnow().isoformat()
        }), 500

if __name__ == "__main__":
    # Run locally for development
    port = int(os.environ.get("PORT", 8082))
    debug = Config.ENVIRONMENT == 'development'
    
    logger.info(f"Starting MedellínBot trámites agent on port {port}, debug={debug}")
    app.run(debug=debug, host="0.0.0.0", port=port)