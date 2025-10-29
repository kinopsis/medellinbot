"""
Firestore Configuration and Connection Management
===============================================

Configuration and connection management for Google Cloud Firestore integration.
"""

import os
import logging
from typing import Optional, Dict, Any
from google.cloud import firestore
from google.cloud.firestore_v1.client import Client
from google.api_core.exceptions import GoogleAPIError
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class FirestoreConfig:
    """Firestore configuration settings."""
    project_id: Optional[str] = os.getenv("FIRESTORE_PROJECT_ID")
    database_id: str = os.getenv("FIRESTORE_DATABASE_ID", "(default)")
    collection_prefix: str = os.getenv("FIRESTORE_COLLECTION_PREFIX", "medellinbot")
    credentials_path: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    emulator_host: Optional[str] = os.getenv("FIRESTORE_EMULATOR_HOST")
    use_emulator: bool = os.getenv("USE_FIRESTORE_EMULATOR", "false").lower() == "true"
    
    # Collection configurations
    collections: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "temporary_data": {
            "name": "temporary_data",
            "ttl_field": "expires_at",
            "default_ttl_days": 7
        },
        "cache": {
            "name": "cache",
            "ttl_field": "expires_at", 
            "default_ttl_days": 1
        },
        "user_sessions": {
            "name": "user_sessions",
            "ttl_field": "expires_at",
            "default_ttl_days": 30
        },
        "vector_embeddings": {
            "name": "vector_embeddings",
            "ttl_field": None,
            "default_ttl_days": None
        }
    })

class FirestoreManager:
    """Manages Firestore connections and operations."""
    
    def __init__(self, config: Optional[FirestoreConfig] = None):
        """Initialize Firestore manager."""
        self.config = config or FirestoreConfig()
        self._client: Optional[Client] = None
        self._initialize_client()
        
    def _initialize_client(self) -> None:
        """Initialize Firestore client with proper configuration."""
        try:
            # Use emulator if configured
            if self.config.use_emulator and self.config.emulator_host:
                os.environ["FIRESTORE_EMULATOR_HOST"] = self.config.emulator_host
                logger.info(f"Using Firestore emulator at {self.config.emulator_host}")
            
            # Initialize client
            self._client = firestore.Client(
                project=self.config.project_id,
                database=self.config.database_id
            )
            
            logger.info(f"Firestore client initialized for project: {self.config.project_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            raise
    
    @property
    def client(self) -> Client:
        """Get Firestore client instance."""
        if self._client is None:
            raise RuntimeError("Firestore client not initialized")
        return self._client
    
    def get_collection_ref(self, collection_name: str) -> firestore.CollectionReference:
        """Get collection reference with prefix."""
        full_collection_name = f"{self.config.collection_prefix}_{collection_name}"
        return self.client.collection(full_collection_name)
    
    async def save_temporary_data(self, data_type: str, data: Dict[str, Any], 
                                 ttl_days: Optional[int] = None) -> Optional[str]:
        """Save temporary data with TTL."""
        try:
            collection = self.get_collection_ref("temporary_data")
            
            # Set expiration time
            from datetime import datetime, timedelta
            expires_at = datetime.utcnow() + timedelta(
                days=ttl_days or self.config.collections["temporary_data"]["default_ttl_days"]
            )
            
            doc_data = {
                **data,
                "data_type": data_type,
                "created_at": datetime.utcnow(),
                "expires_at": expires_at
            }
            
            doc_ref = collection.document()
            doc_ref.set(doc_data)
            
            return doc_ref.id
            
        except Exception as e:
            logger.error(f"Failed to save temporary data: {e}")
            return None
    
    async def get_temporary_data(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get temporary data by document ID."""
        try:
            collection = self.get_collection_ref("temporary_data")
            doc_ref = collection.document(doc_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                # Check if data has expired
                if "expires_at" in data:
                    from datetime import datetime
                    if data["expires_at"] < datetime.utcnow():
                        # Delete expired data
                        doc_ref.delete()
                        return None
                return data
            return None
            
        except Exception as e:
            logger.error(f"Failed to get temporary data: {e}")
            return None
    
    async def save_cache_entry(self, cache_key: str, data: Dict[str, Any], 
                              ttl_days: Optional[int] = None) -> bool:
        """Save cache entry with TTL."""
        try:
            collection = self.get_collection_ref("cache")
            
            # Set expiration time
            from datetime import datetime, timedelta
            expires_at = datetime.utcnow() + timedelta(
                days=ttl_days or self.config.collections["cache"]["default_ttl_days"]
            )
            
            doc_data = {
                **data,
                "cache_key": cache_key,
                "created_at": datetime.utcnow(),
                "expires_at": expires_at
            }
            
            doc_ref = collection.document(cache_key)
            doc_ref.set(doc_data, merge=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save cache entry: {e}")
            return False
    
    async def get_cache_entry(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cache entry by key."""
        try:
            collection = self.get_collection_ref("cache")
            doc_ref = collection.document(cache_key)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                # Check if cache has expired
                if "expires_at" in data:
                    from datetime import datetime
                    if data["expires_at"] < datetime.utcnow():
                        # Delete expired cache
                        doc_ref.delete()
                        return None
                return data
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cache entry: {e}")
            return None
    
    async def save_user_session(self, session_id: str, session_data: Dict[str, Any], 
                               ttl_days: Optional[int] = None) -> bool:
        """Save user session data."""
        try:
            collection = self.get_collection_ref("user_sessions")
            
            # Set expiration time
            from datetime import datetime, timedelta
            expires_at = datetime.utcnow() + timedelta(
                days=ttl_days or self.config.collections["user_sessions"]["default_ttl_days"]
            )
            
            doc_data = {
                **session_data,
                "session_id": session_id,
                "updated_at": datetime.utcnow(),
                "expires_at": expires_at
            }
            
            doc_ref = collection.document(session_id)
            doc_ref.set(doc_data, merge=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save user session: {e}")
            return False
    
    async def get_user_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get user session data."""
        try:
            collection = self.get_collection_ref("user_sessions")
            doc_ref = collection.document(session_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                # Check if session has expired
                if "expires_at" in data:
                    from datetime import datetime
                    if data["expires_at"] < datetime.utcnow():
                        # Delete expired session
                        doc_ref.delete()
                        return None
                return data
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user session: {e}")
            return None
    
    async def cleanup_expired_documents(self, collection_name: str) -> int:
        """Clean up expired documents from a collection."""
        try:
            collection = self.get_collection_ref(collection_name)
            from datetime import datetime
            
            # Query for expired documents
            expired_docs = collection.where("expires_at", "<", datetime.utcnow()).stream()
            
            deleted_count = 0
            for doc in expired_docs:
                doc.reference.delete()
                deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired documents from {collection_name}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired documents: {e}")
            return 0
    
    async def cleanup_all_expired(self) -> Dict[str, int]:
        """Clean up expired documents from all collections with TTL."""
        results = {}
        
        # Clean up collections with TTL
        ttl_collections = ["temporary_data", "cache", "user_sessions"]
        
        for collection_name in ttl_collections:
            results[collection_name] = await self.cleanup_expired_documents(collection_name)
        
        return results

# Global Firestore manager instance
firestore_manager: Optional[FirestoreManager] = None

def initialize_firestore(config: Optional[FirestoreConfig] = None) -> FirestoreManager:
    """Initialize global Firestore manager."""
    global firestore_manager
    firestore_manager = FirestoreManager(config)
    return firestore_manager

def get_firestore_manager() -> FirestoreManager:
    """Get global Firestore manager instance."""
    if firestore_manager is None:
        raise RuntimeError("Firestore manager not initialized. Call initialize_firestore() first.")
    return firestore_manager
