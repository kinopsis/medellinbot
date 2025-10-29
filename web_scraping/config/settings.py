"""
Configuration Settings
======================

Centralized configuration management for the web scraping framework.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str = os.getenv("DATABASE_URL", "sqlite:///./web_scraping.db")
    pool_size: int = int(os.getenv("DB_POOL_SIZE", "10"))
    max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    echo: bool = os.getenv("DB_ECHO", "false").lower() == "true"

@dataclass
class ScrapingConfig:
    """Web scraping configuration."""
    default_user_agent: str = "MedellínBot/1.0"
    default_timeout: int = int(os.getenv("SCRAPING_TIMEOUT", "30"))
    default_max_retries: int = int(os.getenv("SCRAPING_MAX_RETRIES", "3"))
    rate_limit_delay: float = float(os.getenv("RATE_LIMIT_DELAY", "1.0"))
    concurrent_requests: int = int(os.getenv("CONCURRENT_REQUESTS", "5"))

@dataclass
class MonitoringConfig:
    """Monitoring and alerting configuration."""
    enable_prometheus: bool = os.getenv("ENABLE_PROMETHEUS", "true").lower() == "true"
    prometheus_port: int = int(os.getenv("PROMETHEUS_PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    enable_cloud_logging: bool = os.getenv("ENABLE_CLOUD_LOGGING", "false").lower() == "true"

@dataclass
class CloudConfig:
    """Google Cloud configuration."""
    project_id: Optional[str] = os.getenv("GCP_PROJECT_ID")
    region: str = os.getenv("GCP_REGION", "us-central1")
    bucket_name: Optional[str] = os.getenv("GCS_BUCKET_NAME")
    service_account_path: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

@dataclass
class FirestoreConfig:
    """Firestore configuration."""
    project_id: Optional[str] = os.getenv("FIRESTORE_PROJECT_ID")
    database_id: str = os.getenv("FIRESTORE_DATABASE_ID", "(default)")
    collection_prefix: str = os.getenv("FIRESTORE_COLLECTION_PREFIX", "medellinbot")
    credentials_path: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    emulator_host: Optional[str] = os.getenv("FIRESTORE_EMULATOR_HOST")
    use_emulator: bool = os.getenv("USE_FIRESTORE_EMULATOR", "false").lower() == "true"

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

@dataclass
class AppConfig:
    """Main application configuration."""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    scraping: ScrapingConfig = field(default_factory=ScrapingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    cloud: CloudConfig = field(default_factory=CloudConfig)
    firestore: FirestoreConfig = field(default_factory=FirestoreConfig)
    vector_search: VectorSearchConfig = field(default_factory=VectorSearchConfig)
    
    # Source-specific configurations
    source_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        # Default source configurations
        self.source_configs = {
            "alcaldia_medellin": {
                "base_url": "https://medellin.gov.co",
                "rate_limit_delay": 2.0,
                "timeout": 30
            },
            "secretaria_movilidad": {
                "base_url": "https://movilidadmedellin.gov.co",
                "rate_limit_delay": 1.5,
                "timeout": 25
            },
            "metro_medellin": {
                "base_url": "https://metroenvilla.com.co",
                "rate_limit_delay": 1.0,
                "timeout": 20
            },
            "sdp": {
                "base_url": "https://sdp.gov.co",
                "rate_limit_delay": 2.0,
                "timeout": 35
            },
            "medellin_cultura": {
                "base_url": "https://medellin.gov.co/cultura",
                "rate_limit_delay": 1.5,
                "timeout": 25
            }
        }

# Global configuration instance
config = AppConfig()

def get_source_config(source_name: str) -> Dict[str, Any]:
    """Get configuration for a specific data source."""
    return config.source_configs.get(source_name, {})

def update_source_config(source_name: str, config_data: Dict[str, Any]):
    """Update configuration for a specific data source."""
    config.source_configs[source_name] = config_data