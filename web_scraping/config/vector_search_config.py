"""
Vertex AI Vector Search Configuration and Integration
====================================================

Configuration and integration for Google Cloud Vertex AI Vector Search.
"""

import os
import logging
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from google.cloud import aiplatform
from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint
from google.cloud.aiplatform.matching_engine import MatchingEngineIndex, MatchingEngineIndexEndpoint
from google.api_core.exceptions import GoogleAPIError
from google.oauth2 import service_account
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class VectorSearchConfig:
    """Vertex AI Vector Search configuration."""
    project_id: Optional[str] = os.getenv("VECTOR_SEARCH_PROJECT_ID")
    region: str = os.getenv("VECTOR_SEARCH_REGION", "us-central1")
    index_id: Optional[str] = os.getenv("VECTOR_SEARCH_INDEX_ID")
    endpoint_id: Optional[str] = os.getenv("VECTOR_SEARCH_ENDPOINT_ID")
    dimensions: int = int(os.getenv("VECTOR_SEARCH_DIMENSIONS", "768"))
    metric: str = os.getenv("VECTOR_SEARCH_METRIC", "cosine")
    credentials_path: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    display_name: str = os.getenv("VECTOR_SEARCH_DISPLAY_NAME", "medellinbot-vector-index")
    description: str = os.getenv("VECTOR_SEARCH_DESCRIPTION", "Vector index for MedellínBot semantic search")
    
    # Index configuration
    index_config: Dict[str, Any] = field(default_factory=lambda: {
        "approximate_neighbors_count": 150,
        "distance_measure_type": "DOT_PRODUCT_DISTANCE",
        "algorithm_config": {
            "tree_ah_config": {
                "leaf_node_embedding_count": 500,
                "leaf_nodes_to_search_percent": 7
            }
        },
        "feature_normalize": True
    })

class VectorSearchManager:
    """Manages Vertex AI Vector Search operations."""
    
    def __init__(self, config: Optional[VectorSearchConfig] = None):
        """Initialize Vector Search manager."""
        self.config = config or VectorSearchConfig()
        self._index: Optional[MatchingEngineIndex] = None
        self._endpoint: Optional[MatchingEngineIndexEndpoint] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Vertex AI client."""
        try:
            # Initialize Vertex AI
            if self.config.credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    self.config.credentials_path
                )
                aiplatform.init(
                    project=self.config.project_id,
                    location=self.config.region,
                    credentials=credentials
                )
            else:
                aiplatform.init(
                    project=self.config.project_id,
                    location=self.config.region
                )
            
            logger.info(f"Vertex AI initialized for project: {self.config.project_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            raise
    
    async def create_index(self) -> Optional[MatchingEngineIndex]:
        """Create a new vector search index."""
        try:
            if not self.config.project_id:
                raise ValueError("Project ID is required to create index")
            
            # Create index
            index = MatchingEngineIndex.create(
                display_name=self.config.display_name,
                description=self.config.description,
                dimensions=self.config.dimensions,
                approximate_neighbors_count=self.config.index_config["approximate_neighbors_count"],
                distance_measure_type=self.config.index_config["distance_measure_type"],
                algorithm_config=self.config.index_config["algorithm_config"],
                feature_normalize=self.config.index_config["feature_normalize"]
            )
            
            self._index = index
            logger.info(f"Created vector search index: {index.name}")
            return index
            
        except Exception as e:
            logger.error(f"Failed to create vector search index: {e}")
            return None
    
    async def get_or_create_endpoint(self) -> Optional[MatchingEngineIndexEndpoint]:
        """Get existing endpoint or create new one."""
        try:
            if self.config.endpoint_id:
                # Try to get existing endpoint
                try:
                    endpoint = MatchingEngineIndexEndpoint(self.config.endpoint_id)
                    self._endpoint = endpoint
                    logger.info(f"Using existing endpoint: {endpoint.name}")
                    return endpoint
                except Exception:
                    logger.info("Existing endpoint not found, creating new one")
            
            # Create new endpoint
            if not self._index:
                self._index = await self.create_index()
            
            if self._index:
                endpoint = MatchingEngineIndexEndpoint.create(
                    display_name=f"{self.config.display_name}-endpoint"
                )
                
                # Deploy index to endpoint
                endpoint.deploy_index(
                    index=self._index,
                    deployed_index_id=f"{self.config.display_name}-deployed-index"
                )
                
                self._endpoint = endpoint
                logger.info(f"Created and deployed endpoint: {endpoint.name}")
                return endpoint
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get or create endpoint: {e}")
            return None
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for text using Vertex AI."""
        try:
            from vertexai.language_models import TextEmbeddingModel
            
            # Initialize embedding model
            model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
            
            # Generate embeddings
            embeddings = []
            for text in texts:
                response = model.get_embeddings([text])
                if response and len(response) > 0:
                    embeddings.append(response[0].values)
                else:
                    embeddings.append([0.0] * self.config.dimensions)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            # Return zero vectors as fallback
            return [[0.0] * self.config.dimensions for _ in texts]
    
    async def upsert_embeddings(self, ids: List[str], embeddings: List[List[float]], 
                              metadata: List[Dict[str, Any]]) -> bool:
        """Upsert embeddings to the vector index."""
        try:
            if not self._endpoint:
                self._endpoint = await self.get_or_create_endpoint()
            
            if not self._endpoint:
                raise RuntimeError("Failed to get or create endpoint")
            
            # Prepare data for upsert
            upsert_data = []
            for i, (id_val, embedding, meta) in enumerate(zip(ids, embeddings, metadata)):
                # Convert metadata to string format for Vertex AI
                metadata_str = {k: str(v) for k, v in meta.items()}
                
                upsert_data.append({
                    "id": id_val,
                    "embedding": embedding,
                    "restricts": [],  # Optional metadata for filtering
                    "numeric_properties": {},  # Optional numeric metadata
                    "crowding_tag": {}  # Optional crowding configuration
                })
            
            # Upsert to index
            self._endpoint.upsert_datapoints(
                deployed_index_id=f"{self.config.display_name}-deployed-index",
                datapoints=upsert_data
            )
            
            logger.info(f"Upserted {len(upsert_data)} embeddings to vector index")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert embeddings: {e}")
            return False
    
    async def search_similar_vectors(self, query_embedding: List[float], 
                                   num_neighbors: int = 10) -> List[Dict[str, Any]]:
        """Search for similar vectors in the index."""
        try:
            if not self._endpoint:
                self._endpoint = await self.get_or_create_endpoint()
            
            if not self._endpoint:
                raise RuntimeError("Failed to get or create endpoint")
            
            # Perform vector search
            response = self._endpoint.find_neighbors(
                deployed_index_id=f"{self.config.display_name}-deployed-index",
                queries=[query_embedding],
                num_neighbors=num_neighbors
            )
            
            results = []
            for neighbor_list in response:
                for neighbor in neighbor_list:
                    results.append({
                        "id": neighbor.id,
                        "distance": neighbor.distance,
                        "metadata": neighbor.datapoint.restricts  # Extract metadata if available
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search similar vectors: {e}")
            return []
    
    async def delete_index(self) -> bool:
        """Delete the vector search index."""
        try:
            if self._index:
                self._index.delete(force=True)
                logger.info(f"Deleted vector search index: {self._index.name}")
                self._index = None
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            return False
    
    async def delete_endpoint(self) -> bool:
        """Delete the vector search endpoint."""
        try:
            if self._endpoint:
                self._endpoint.delete(force=True)
                logger.info(f"Deleted vector search endpoint: {self._endpoint.name}")
                self._endpoint = None
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete endpoint: {e}")
            return False

# Global Vector Search manager instance
vector_search_manager: Optional[VectorSearchManager] = None

def initialize_vector_search(config: Optional[VectorSearchConfig] = None) -> VectorSearchManager:
    """Initialize global Vector Search manager."""
    global vector_search_manager
    vector_search_manager = VectorSearchManager(config)
    return vector_search_manager

def get_vector_search_manager() -> VectorSearchManager:
    """Get global Vector Search manager instance."""
    if vector_search_manager is None:
        raise RuntimeError("Vector Search manager not initialized. Call initialize_vector_search() first.")
    return vector_search_manager
