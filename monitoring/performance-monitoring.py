#!/usr/bin/env python3
"""
Ongoing Performance Monitoring System for MedellínBot
This script continuously monitors the performance of all services and generates reports.
"""

import requests
import time
import json
import logging
import statistics
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import deque
import psutil
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Data class for performance metrics."""
    timestamp: str
    service: str
    response_time: float
    status_code: int
    cpu_usage: float
    memory_usage: float
    error_rate: float
    throughput: float
    availability: float

@dataclass
class AlertThresholds:
    """Data class for alert thresholds."""
    max_response_time: float = 3.0  # seconds
    max_cpu_usage: float = 80.0     # percentage
    max_memory_usage: float = 85.0  # percentage
    max_error_rate: float = 5.0     # percentage
    min_availability: float = 99.0  # percentage
    max_throughput_drop: float = 50.0  # percentage

class PerformanceMonitor:
    def __init__(self, project_id: str = "medellinbot-prd-440915", check_interval: int = 60):
        self.project_id = project_id
        self.check_interval = check_interval
        self.base_urls = {
            'webhook': f'https://medellinbot-webhook-{self.project_id}.a.run.app',
            'orchestrator': f'https://medellinbot-orchestrator-{self.project_id}.a.run.app',
            'tramites': f'https://medellinbot-tramites-{self.project_id}.a.run.app',
            'pqrsd': f'https://medellinbot-pqrsd-{self.project_id}.a.run.app',
            'programas': f'https://medellinbot-programas-{self.project_id}.a.run.app',
            'notificaciones': f'https://medellinbot-notificaciones-{self.project_id}.a.run.app'
        }
        self.thresholds = AlertThresholds()
        self.metrics_history = {service: deque(maxlen=1440) for service in self.base_urls.keys()}  # 24 hours of minute-by-minute data
        self.alerts = []
        self.is_monitoring = False
        self.monitoring_thread = None
        
    def get_system_metrics(self) -> Tuple[float, float]:
        """Get current system CPU and memory usage."""
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_usage = psutil.virtual_memory().percent
            return cpu_usage, memory_usage
        except Exception as e:
            logger.warning(f"Failed to get system metrics: {e}")
            return 0.0, 0.0

    def check_service_health(self, service: str, url: str) -> Dict:
        """Check the health and performance of a service."""
        start_time = time.time()
        
        try:
            # Test health endpoint
            response = requests.get(f"{url}/health", timeout=10)
            response_time = time.time() - start_time
            
            status_code = response.status_code
            is_healthy = status_code == 200
            
            # Get system metrics
            cpu_usage, memory_usage = self.get_system_metrics()
            
            return {
                'service': service,
                'url': url,
                'response_time': response_time,
                'status_code': status_code,
                'is_healthy': is_healthy,
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'timestamp': datetime.now().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            
            # Get system metrics even when service is down
            cpu_usage, memory_usage = self.get_system_metrics()
            
            return {
                'service': service,
                'url': url,
                'response_time': response_time,
                'status_code': 0,
                'is_healthy': False,
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def calculate_derived_metrics(self, service: str, current_metrics: Dict) -> Dict:
        """Calculate derived metrics like error rate, throughput, and availability."""
        # Get recent metrics for this service
        recent_metrics = list(self.metrics_history[service])
        
        if not recent_metrics:
            return {
                'error_rate': 0.0 if current_metrics['is_healthy'] else 100.0,
                'throughput': 1.0,
                'availability': 100.0 if current_metrics['is_healthy'] else 0.0
            }
        
        # Calculate error rate (percentage of failed requests in last 5 minutes)
        recent_failures = sum(1 for m in recent_metrics[-300:] if not m['is_healthy'])  # Last 5 minutes (300 seconds)
        error_rate = (recent_failures / min(len(recent_metrics), 300)) * 100
        
        # Calculate availability (percentage of successful requests in last hour)
        hourly_failures = sum(1 for m in recent_metrics[-3600:] if not m['is_healthy'])  # Last hour (3600 seconds)
        availability = ((3600 - hourly_failures) / min(len(recent_metrics), 3600)) * 100
        
        # Calculate throughput (requests per minute)
        throughput = len(recent_metrics[-60:])  # Requests in last minute
        
        return {
            'error_rate': error_rate,
            'throughput': throughput,
            'availability': availability
        }

    def check_alerts(self, metrics: PerformanceMetrics) -> List[str]:
        """Check if any metrics exceed alert thresholds."""
        alerts = []
        
        # Response time alert
        if metrics.response_time > self.thresholds.max_response_time:
            alerts.append(f"High response time: {metrics.response_time:.2f}s (threshold: {self.thresholds.max_response_time}s)")
        
        # CPU usage alert
        if metrics.cpu_usage > self.thresholds.max_cpu_usage:
            alerts.append(f"High CPU usage: {metrics.cpu_usage:.1f}% (threshold: {self.thresholds.max_cpu_usage}%)")
        
        # Memory usage alert
        if metrics.memory_usage > self.thresholds.max_memory_usage:
            alerts.append(f"High memory usage: {metrics.memory_usage:.1f}% (threshold: {self.thresholds.max_memory_usage}%)")
        
        # Error rate alert
        if metrics.error_rate > self.thresholds.max_error_rate:
            alerts.append(f"High error rate: {metrics.error_rate:.1f}% (threshold: {self.thresholds.max_error_rate}%)")
        
        # Availability alert
        if metrics.availability < self.thresholds.min_availability:
            alerts.append(f"Low availability: {metrics.availability:.1f}% (threshold: {self.thresholds.min_availability}%)")
        
        return alerts

    def record_metrics(self, service: str, health_data: Dict, derived_metrics: Dict):
        """Record metrics for a service."""
        metrics = PerformanceMetrics(
            timestamp=health_data['timestamp'],
            service=service,
            response_time=health_data['response_time'],
            status_code=health_data['status_code'],
            cpu_usage=health_data['cpu_usage'],
            memory_usage=health_data['memory_usage'],
            error_rate=derived_metrics['error_rate'],
            throughput=derived_metrics['throughput'],
            availability=derived_metrics['availability']
        )
        
        self.metrics_history[service].append(asdict(metrics))
        
        # Check for alerts
        alerts = self.check_alerts(metrics)
        if alerts:
            for alert in alerts:
                alert_entry = {
                    'timestamp': metrics.timestamp,
                    'service': service,
                    'alert': alert,
                    'severity': self.get_alert_severity(alert)
                }
                self.alerts.append(alert_entry)
                logger.warning(f"ALERT [{service}]: {alert}")

    def get_alert_severity(self, alert: str) -> str:
        """Determine alert severity based on the alert message."""
        if 'availability' in alert.lower() or 'down' in alert.lower():
            return 'critical'
        elif 'response time' in alert.lower() or 'error rate' in alert.lower():
            return 'high'
        elif 'cpu' in alert.lower() or 'memory' in alert.lower():
            return 'medium'
        else:
            return 'low'

    def generate_performance_report(self) -> Dict:
        """Generate a comprehensive performance report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {},
            'service_details': {},
            'alerts_summary': {},
            'trends': {}
        }
        
        for service in self.base_urls.keys():
            metrics_list = list(self.metrics_history[service])
            
            if metrics_list:
                # Calculate summary statistics
                response_times = [m['response_time'] for m in metrics_list]
                cpu_usages = [m['cpu_usage'] for m in metrics_list]
                memory_usages = [m['memory_usage'] for m in metrics_list]
                
                report['service_details'][service] = {
                    'latest_metrics': metrics_list[-1],
                    'response_time_stats': {
                        'avg': statistics.mean(response_times),
                        'p95': statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0],
                        'max': max(response_times),
                        'min': min(response_times)
                    },
                    'resource_usage_stats': {
                        'avg_cpu': statistics.mean(cpu_usages),
                        'avg_memory': statistics.mean(memory_usages),
                        'max_cpu': max(cpu_usages),
                        'max_memory': max(memory_usages)
                    },
                    'availability': metrics_list[-1]['availability'],
                    'error_rate': metrics_list[-1]['error_rate']
                }
                
                # Calculate overall summary
                report['summary'][service] = {
                    'availability': metrics_list[-1]['availability'],
                    'avg_response_time': statistics.mean(response_times),
                    'status': 'healthy' if metrics_list[-1]['availability'] > 95 else 'degraded'
                }
        
        # Generate alerts summary
        recent_alerts = [a for a in self.alerts if 
                        datetime.fromisoformat(a['timestamp']) > datetime.now() - timedelta(hours=1)]
        
        alert_counts = {}
        for alert in recent_alerts:
            severity = alert['severity']
            alert_counts[severity] = alert_counts.get(severity, 0) + 1
        
        report['alerts_summary'] = {
            'total_alerts_last_hour': len(recent_alerts),
            'by_severity': alert_counts,
            'recent_alerts': recent_alerts[-10:]  # Last 10 alerts
        }
        
        # Generate trends (compare last hour vs previous hour)
        for service in self.base_urls.keys():
            metrics_list = list(self.metrics_history[service])
            
            if len(metrics_list) >= 120:  # At least 2 hours of data
                last_hour = metrics_list[-60:]
                prev_hour = metrics_list[-120:-60]
                
                if last_hour and prev_hour:
                    last_hour_avg_response = statistics.mean([m['response_time'] for m in last_hour])
                    prev_hour_avg_response = statistics.mean([m['response_time'] for m in prev_hour])
                    
                    response_trend = ((last_hour_avg_response - prev_hour_avg_response) / prev_hour_avg_response) * 100
                    
                    report['trends'][service] = {
                        'response_time_trend': response_trend,
                        'trend_direction': 'improving' if response_trend < 0 else 'degrading' if response_trend > 0 else 'stable'
                    }
        
        return report

    def save_report(self, report: Dict, filename: str = "performance_report.json"):
        """Save performance report to file."""
        if filename == "performance_report.json":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Performance report saved to {filename}")

    def print_console_report(self, report: Dict):
        """Print a formatted console report."""
        print("\n" + "="*80)
        print("MEDELLÍNBOT PERFORMANCE MONITORING REPORT")
        print("="*80)
        print(f"Generated: {report['timestamp']}")
        
        # Summary section
        print("\nSERVICE SUMMARY:")
        print("-" * 80)
        for service, summary in report['summary'].items():
            status_emoji = "✅" if summary['status'] == 'healthy' else "⚠️"
            print(f"{status_emoji} {service:15} | Availability: {summary['availability']:.1f}% | "
                  f"Avg Response: {summary['avg_response_time']:.3f}s")
        
        # Alerts section
        alerts_summary = report['alerts_summary']
        print(f"\nALERTS (Last Hour): {alerts_summary['total_alerts_last_hour']}")
        print("-" * 80)
        for severity, count in alerts_summary['by_severity'].items():
            print(f"{severity.upper()}: {count}")
        
        # Recent alerts
        if alerts_summary['recent_alerts']:
            print("\nRECENT ALERTS:")
            print("-" * 80)
            for alert in alerts_summary['recent_alerts'][-5:]:  # Last 5 alerts
                print(f"[{alert['severity']}] {alert['service']}: {alert['alert']}")
        
        # Trends
        print("\nPERFORMANCE TRENDS (Last Hour vs Previous Hour):")
        print("-" * 80)
        for service, trend in report['trends'].items():
            trend_emoji = "📈" if trend['trend_direction'] == 'degrading' else "📉" if trend['trend_direction'] == 'improving' else "➡️"
            print(f"{trend_emoji} {service:15} | Response time: {trend['response_time_trend']:+.1f}%")
        
        print("\n" + "="*80)

    def start_monitoring(self):
        """Start continuous monitoring."""
        if self.is_monitoring:
            logger.warning("Monitoring is already running")
            return
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("Performance monitoring started")

    def stop_monitoring(self):
        """Stop continuous monitoring."""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Check all services
                for service, url in self.base_urls.items():
                    health_data = self.check_service_health(service, url)
                    derived_metrics = self.calculate_derived_metrics(service, health_data)
                    self.record_metrics(service, health_data, derived_metrics)
                
                # Generate and save report every hour
                if int(time.time()) % 3600 == 0:  # Every hour
                    report = self.generate_performance_report()
                    self.save_report(report)
                    self.print_console_report(report)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.check_interval)

    def get_real_time_metrics(self) -> Dict:
        """Get real-time metrics for all services."""
        real_time_metrics = {}
        
        for service, url in self.base_urls.items():
            health_data = self.check_service_health(service, url)
            derived_metrics = self.calculate_derived_metrics(service, health_data)
            
            real_time_metrics[service] = {
                'health': health_data,
                'derived': derived_metrics,
                'timestamp': datetime.now().isoformat()
            }
        
        return real_time_metrics

def main():
    """Main function for performance monitoring."""
    import argparse
    import signal
    import sys
    
    parser = argparse.ArgumentParser(description='MedellínBot Performance Monitor')
    parser.add_argument('--project-id', default='medellinbot-prd-440915', help='Google Cloud Project ID')
    parser.add_argument('--interval', type=int, default=60, help='Check interval in seconds')
    parser.add_argument('--report-only', action='store_true', help='Generate report only, then exit')
    parser.add_argument('--continuous', action='store_true', help='Run continuous monitoring')
    
    args = parser.parse_args()
    
    monitor = PerformanceMonitor(args.project_id, args.interval)
    
    def signal_handler(sig, frame):
        logger.info("Received interrupt signal, stopping monitoring...")
        monitor.stop_monitoring()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    if args.report_only:
        # Generate one-time report
        logger.info("Generating one-time performance report...")
        for service, url in monitor.base_urls.items():
            health_data = monitor.check_service_health(service, url)
            derived_metrics = monitor.calculate_derived_metrics(service, health_data)
            monitor.record_metrics(service, health_data, derived_metrics)
        
        report = monitor.generate_performance_report()
        monitor.save_report(report)
        monitor.print_console_report(report)
        
    elif args.continuous:
        # Start continuous monitoring
        monitor.start_monitoring()
        
        try:
            # Print real-time status every 5 minutes
            while True:
                time.sleep(300)  # 5 minutes
                real_time = monitor.get_real_time_metrics()
                
                print("\n" + "="*50)
                print("REAL-TIME STATUS")
                print("="*50)
                for service, data in real_time.items():
                    health = data['health']
                    status = "✅" if health['is_healthy'] else "❌"
                    print(f"{status} {service}: {health['response_time']:.3f}s | {health['status_code']}")
                
        except KeyboardInterrupt:
            monitor.stop_monitoring()
    
    else:
        # Default: generate report and exit
        logger.info("Generating performance report...")
        for service, url in monitor.base_urls.items():
            health_data = monitor.check_service_health(service, url)
            derived_metrics = monitor.calculate_derived_metrics(service, health_data)
            monitor.record_metrics(service, health_data, derived_metrics)
        
        report = monitor.generate_performance_report()
        monitor.save_report(report)
        monitor.print_console_report(report)

if __name__ == "__main__":
    main()