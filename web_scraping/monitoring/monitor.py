"""
Monitoring and Alerting System
==============================

Comprehensive monitoring for web scraping operations with Prometheus metrics
and alerting capabilities.
"""

import logging
import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

from prometheus_client import Counter, Histogram, Gauge, start_http_server, CollectorRegistry
from google.cloud import monitoring_v3
from google.cloud.monitoring_v3 import types
import structlog

# Prometheus metrics
REQUEST_COUNT = Counter('web_scraping_requests_total', 'Total number of scraping requests', ['source', 'status'])
REQUEST_DURATION = Histogram('web_scraping_request_duration_seconds', 'Duration of scraping requests', ['source'])
DATA_QUALITY_GAUGE = Gauge('web_scraping_data_quality', 'Data quality score', ['source', 'data_type'])
ERROR_COUNT = Counter('web_scraping_errors_total', 'Total number of errors', ['source', 'error_type'])
ACTIVE_SCRAPERS = Gauge('web_scraping_active_scrapers', 'Number of active scrapers')

# Firestore metrics
FIRESTORE_WRITE_COUNT = Counter('firestore_writes_total', 'Total number of Firestore write operations', ['collection', 'operation_type'])
FIRESTORE_READ_COUNT = Counter('firestore_reads_total', 'Total number of Firestore read operations', ['collection', 'operation_type'])
FIRESTORE_WRITE_DURATION = Histogram('firestore_write_duration_seconds', 'Duration of Firestore write operations', ['collection'])
FIRESTORE_READ_DURATION = Histogram('firestore_read_duration_seconds', 'Duration of Firestore read operations', ['collection'])
FIRESTORE_ERROR_COUNT = Counter('firestore_errors_total', 'Total number of Firestore errors', ['collection', 'error_type'])
FIRESTORE_DOCUMENT_COUNT = Gauge('firestore_document_count', 'Number of documents in collection', ['collection'])
FIRESTORE_STORAGE_BYTES = Gauge('firestore_storage_bytes', 'Storage usage in bytes', ['collection'])

# Vector Search metrics
VECTOR_SEARCH_EMBEDDING_COUNT = Counter('vector_search_embeddings_total', 'Total number of embeddings generated', ['model'])
VECTOR_SEARCH_UPSERT_COUNT = Counter('vector_search_upserts_total', 'Total number of vector upserts', ['index'])
VECTOR_SEARCH_SEARCH_COUNT = Counter('vector_search_queries_total', 'Total number of vector search queries', ['index'])
VECTOR_SEARCH_EMBEDDING_DURATION = Histogram('vector_search_embedding_duration_seconds', 'Duration of embedding generation', ['model'])
VECTOR_SEARCH_UPSERT_DURATION = Histogram('vector_search_upsert_duration_seconds', 'Duration of vector upsert operations', ['index'])
VECTOR_SEARCH_SEARCH_DURATION = Histogram('vector_search_search_duration_seconds', 'Duration of vector search operations', ['index'])
VECTOR_SEARCH_ERROR_COUNT = Counter('vector_search_errors_total', 'Total number of Vector Search errors', ['operation', 'error_type'])
VECTOR_SEARCH_INDEX_SIZE = Gauge('vector_search_index_size', 'Number of vectors in index', ['index'])
VECTOR_SEARCH_INDEX_DIMENSIONS = Gauge('vector_search_index_dimensions', 'Dimensionality of vectors in index', ['index'])

@dataclass
class AlertRule:
    """Definition of an alert rule."""
    name: str
    metric_name: str
    condition: str  # '>', '<', '==', '!='
    threshold: float
    duration: timedelta  # Time window for the condition
    severity: str  # 'critical', 'warning', 'info'
    description: str

@dataclass
class Alert:
    """Alert instance."""
    rule: AlertRule
    value: float
    timestamp: datetime
    message: str
    resolved: bool = False

class MonitoringService:
    """Main monitoring service for web scraping operations."""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        self.alert_rules: List[AlertRule] = []
        self.active_alerts: List[Alert] = []
        self.metrics_registry = CollectorRegistry()
        self.start_time = datetime.now()
        
        # Initialize default alert rules
        self._initialize_default_rules()
        
    def start_monitoring(self, port: int = 8000):
        """Start the Prometheus metrics server."""
        try:
            start_http_server(port, registry=self.metrics_registry)
            self.logger.info(f"Prometheus metrics server started on port {port}")
        except Exception as e:
            self.logger.error(f"Failed to start metrics server: {e}")
            
    def _initialize_default_rules(self):
        """Initialize default alert rules."""
        default_rules = [
            AlertRule(
                name="high_error_rate",
                metric_name="web_scraping_errors_total",
                condition=">",
                threshold=10.0,
                duration=timedelta(minutes=5),
                severity="critical",
                description="High error rate detected in scraping operations"
            ),
            AlertRule(
                name="low_data_quality",
                metric_name="web_scraping_data_quality",
                condition="<",
                threshold=0.5,
                duration=timedelta(minutes=10),
                severity="warning",
                description="Data quality below acceptable threshold"
            ),
            AlertRule(
                name="scraper_timeout",
                metric_name="web_scraping_request_duration_seconds",
                condition=">",
                threshold=300.0,  # 5 minutes
                duration=timedelta(minutes=1),
                severity="critical",
                description="Scraper request taking too long"
            )
        ]
        
        self.alert_rules.extend(default_rules)
        
    def record_request(self, source: str, status: str, duration: float):
        """Record a scraping request metric."""
        REQUEST_COUNT.labels(source=source, status=status).inc()
        REQUEST_DURATION.labels(source=source).observe(duration)
        
    def record_error(self, source: str, error_type: str):
        """Record an error metric."""
        ERROR_COUNT.labels(source=source, error_type=error_type).inc()
        
    def update_data_quality(self, source: str, data_type: str, quality_score: float):
        """Update data quality metric."""
        DATA_QUALITY_GAUGE.labels(source=source, data_type=data_type).set(quality_score)
        
    def set_active_scrapers(self, count: int):
        """Set the number of active scrapers."""
        ACTIVE_SCRAPERS.set(count)
        
    # Firestore monitoring methods
    def record_firestore_write(self, collection: str, operation_type: str, duration: float):
        """Record a Firestore write operation."""
        FIRESTORE_WRITE_COUNT.labels(collection=collection, operation_type=operation_type).inc()
        FIRESTORE_WRITE_DURATION.labels(collection=collection).observe(duration)
        
    def record_firestore_read(self, collection: str, operation_type: str, duration: float):
        """Record a Firestore read operation."""
        FIRESTORE_READ_COUNT.labels(collection=collection, operation_type=operation_type).inc()
        FIRESTORE_READ_DURATION.labels(collection=collection).observe(duration)
        
    def record_firestore_error(self, collection: str, error_type: str):
        """Record a Firestore error."""
        FIRESTORE_ERROR_COUNT.labels(collection=collection, error_type=error_type).inc()
        
    def update_firestore_document_count(self, collection: str, count: int):
        """Update Firestore document count metric."""
        FIRESTORE_DOCUMENT_COUNT.labels(collection=collection).set(count)
        
    def update_firestore_storage_usage(self, collection: str, bytes_used: int):
        """Update Firestore storage usage metric."""
        FIRESTORE_STORAGE_BYTES.labels(collection=collection).set(bytes_used)
        
    # Vector Search monitoring methods
    def record_vector_embedding(self, model: str, duration: float):
        """Record a vector embedding generation."""
        VECTOR_SEARCH_EMBEDDING_COUNT.labels(model=model).inc()
        VECTOR_SEARCH_EMBEDDING_DURATION.labels(model=model).observe(duration)
        
    def record_vector_upsert(self, index: str, duration: float):
        """Record a vector upsert operation."""
        VECTOR_SEARCH_UPSERT_COUNT.labels(index=index).inc()
        VECTOR_SEARCH_UPSERT_DURATION.labels(index=index).observe(duration)
        
    def record_vector_search(self, index: str, duration: float):
        """Record a vector search operation."""
        VECTOR_SEARCH_SEARCH_COUNT.labels(index=index).inc()
        VECTOR_SEARCH_SEARCH_DURATION.labels(index=index).observe(duration)
        
    def record_vector_search_error(self, operation: str, error_type: str):
        """Record a Vector Search error."""
        VECTOR_SEARCH_ERROR_COUNT.labels(operation=operation, error_type=error_type).inc()
        
    def update_vector_index_size(self, index: str, size: int):
        """Update vector index size metric."""
        VECTOR_SEARCH_INDEX_SIZE.labels(index=index).set(size)
        
    def update_vector_index_dimensions(self, index: str, dimensions: int):
        """Update vector index dimensions metric."""
        VECTOR_SEARCH_INDEX_DIMENSIONS.labels(index=index).set(dimensions)
        
    async def check_alerts(self):
        """Check all alert rules and generate alerts if conditions are met."""
        current_time = datetime.now()
        
        for rule in self.alert_rules:
            try:
                # This would need to be implemented based on your metrics collection
                # For now, we'll simulate checking
                metric_value = self._get_metric_value(rule.metric_name, rule.condition)
                
                if self._evaluate_condition(metric_value, rule.condition, rule.threshold):
                    # Check if we already have an active alert for this rule
                    existing_alert = next(
                        (alert for alert in self.active_alerts 
                         if alert.rule.name == rule.name and not alert.resolved),
                        None
                    )
                    
                    if not existing_alert:
                        alert = Alert(
                            rule=rule,
                            value=metric_value,
                            timestamp=current_time,
                            message=f"Alert: {rule.description} (value: {metric_value}, threshold: {rule.threshold})"
                        )
                        self.active_alerts.append(alert)
                        await self._send_alert(alert)
                        
            except Exception as e:
                self.logger.error(f"Error checking alert rule {rule.name}: {e}")
                
    def _get_metric_value(self, metric_name: str, condition: str) -> float:
        """Get the current value of a metric."""
        # This would need to be implemented based on your metrics collection system
        # For now, return a dummy value
        return 0.0
        
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Evaluate a condition against a threshold."""
        if condition == ">":
            return value > threshold
        elif condition == "<":
            return value < threshold
        elif condition == "==":
            return value == threshold
        elif condition == "!=":
            return value != threshold
        else:
            return False
            
    async def _send_alert(self, alert: Alert):
        """Send an alert notification."""
        try:
            # Log the alert
            self.logger.warning(
                "Alert triggered",
                alert_name=alert.rule.name,
                severity=alert.rule.severity,
                message=alert.message,
                value=alert.value,
                threshold=alert.rule.threshold
            )
            
            # Send to external alerting systems (implement as needed)
            await self._send_to_slack(alert)
            await self._send_to_email(alert)
            await self._send_to_cloud_monitoring(alert)
            
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
            
    async def _send_to_slack(self, alert: Alert):
        """Send alert to Slack (implement if needed)."""
        pass
        
    async def _send_to_email(self, alert: Alert):
        """Send alert via email (implement if needed)."""
        pass
        
    async def _send_to_cloud_monitoring(self, alert: Alert):
        """Send alert to Google Cloud Monitoring (implement if needed)."""
        pass
        
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        current_time = datetime.now()
        uptime = current_time - self.start_time
        
        return {
            "status": "healthy",
            "uptime_seconds": int(uptime.total_seconds()),
            "active_alerts": len([alert for alert in self.active_alerts if not alert.resolved]),
            "total_alerts": len(self.active_alerts),
            "timestamp": current_time.isoformat()
        }
        
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of key metrics."""
        return {
            "total_requests": self._get_total_requests(),
            "error_rate": self._get_error_rate(),
            "average_response_time": self._get_average_response_time(),
            "data_quality_scores": self._get_data_quality_scores(),
            "active_scrapers": self._get_active_scrapers_count()
        }
        
    def _get_total_requests(self) -> int:
        """Get total number of requests."""
        # Implement based on your metrics collection
        return 0
        
    def _get_error_rate(self) -> float:
        """Get error rate percentage."""
        # Implement based on your metrics collection
        return 0.0
        
    def _get_average_response_time(self) -> float:
        """Get average response time."""
        # Implement based on your metrics collection
        return 0.0
        
    def _get_data_quality_scores(self) -> Dict[str, float]:
        """Get data quality scores by source."""
        # Implement based on your metrics collection
        return {}
        
    def _get_active_scrapers_count(self) -> int:
        """Get number of active scrapers."""
        # Implement based on your metrics collection
        return 0

class ScrapingMonitor:
    """Context manager for monitoring individual scraping operations."""
    
    def __init__(self, source: str, monitoring_service: MonitoringService):
        self.source = source
        self.monitoring_service = monitoring_service
        self.start_time = None
        self.status = "running"
        
    async def __aenter__(self):
        """Enter the monitoring context."""
        self.start_time = time.time()
        self.monitoring_service.set_active_scrapers(
            self.monitoring_service._get_active_scrapers_count() + 1
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the monitoring context."""
        if self.start_time is not None:
            duration = time.time() - self.start_time
        else:
            duration = 0
            
        if exc_type is None:
            self.status = "success"
            self.monitoring_service.record_request(self.source, "success", duration)
        else:
            self.status = "error"
            self.monitoring_service.record_request(self.source, "error", duration)
            self.monitoring_service.record_error(self.source, str(exc_type.__name__))
            
        self.monitoring_service.set_active_scrapers(
            self.monitoring_service._get_active_scrapers_count() - 1
        )
        
    def update_data_quality(self, data_type: str, quality_score: float):
        """Update data quality during scraping."""
        self.monitoring_service.update_data_quality(self.source, data_type, quality_score)

# Global monitoring service instance
monitoring_service = MonitoringService()

def get_monitoring_service() -> MonitoringService:
    """Get the global monitoring service instance."""
    return monitoring_service