"""Prometheus metrics collection"""

from prometheus_client import Counter, Histogram, Gauge, start_http_server
from typing import Optional, Dict
import time


class MetricsCollector:
    """Collects and exposes Prometheus metrics"""
    
    def __init__(self):
        """Initialize metrics"""
        # Request metrics
        self.ingest_requests = Counter(
            'pricecanary_ingest_requests_total',
            'Total number of ingest requests',
            ['status']  # status: success, validation_error, etc.
        )
        
        self.ingest_latency = Histogram(
            'pricecanary_ingest_latency_seconds',
            'Ingest request latency in seconds',
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
        )
        
        # Validation metrics
        self.validation_pass_rate = Gauge(
            'pricecanary_validation_pass_rate',
            'Validation pass rate (0-1)'
        )
        
        self.validation_failures = Counter(
            'pricecanary_validation_failures_total',
            'Total validation failures',
            ['violation_type']
        )
        
        # Drift metrics
        self.drift_score_price = Gauge(
            'pricecanary_drift_score_price',
            'Price drift PSI score'
        )
        
        self.drift_score_stock = Gauge(
            'pricecanary_drift_score_stock',
            'Stock drift PSI score'
        )
        
        self.drift_detections = Counter(
            'pricecanary_drift_detections_total',
            'Total drift detections',
            ['metric_type', 'severity']
        )
        
        # Anomaly metrics
        self.anomaly_score = Histogram(
            'pricecanary_anomaly_score',
            'Anomaly detection scores',
            buckets=[-1.0, -0.5, -0.3, -0.1, 0.0, 0.1, 0.3, 0.5, 1.0]
        )
        
        self.anomaly_detections = Counter(
            'pricecanary_anomaly_detections_total',
            'Total anomaly detections',
            ['severity']
        )
        
        # Alert metrics
        self.active_alerts = Gauge(
            'pricecanary_active_alerts',
            'Number of active (unresolved) alerts',
            ['severity', 'alert_type']
        )
        
        self.alert_count = Counter(
            'pricecanary_alerts_total',
            'Total alerts created',
            ['severity', 'alert_type']
        )
        
        self.alert_latency = Histogram(
            'pricecanary_alert_latency_seconds',
            'Time from event to alert creation in seconds',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
        )
        
        # Throughput metrics
        self.records_processed = Counter(
            'pricecanary_records_processed_total',
            'Total records processed'
        )
        
        self.records_per_second = Gauge(
            'pricecanary_records_per_second',
            'Current processing rate (records/second)'
        )
        
        # System metrics
        self.processing_errors = Counter(
            'pricecanary_processing_errors_total',
            'Total processing errors',
            ['error_type']
        )
        
        # Track for rate calculation
        self._last_record_count = 0
        self._last_rate_time = time.time()
    
    def record_ingest(self, status: str, latency: float):
        """
        Record ingest request
        
        Args:
            status: Request status (success, validation_error, etc.)
            latency: Request latency in seconds
        """
        self.ingest_requests.labels(status=status).inc()
        self.ingest_latency.observe(latency)
    
    def record_validation(self, passed: bool, violation_type: Optional[str] = None):
        """
        Record validation result
        
        Args:
            passed: Whether validation passed
            violation_type: Type of violation if failed
        """
        if not passed and violation_type:
            self.validation_failures.labels(violation_type=violation_type).inc()
    
    def update_validation_pass_rate(self, rate: float):
        """
        Update validation pass rate
        
        Args:
            rate: Pass rate (0-1)
        """
        self.validation_pass_rate.set(rate)
    
    def record_drift(self, metric_type: str, psi: float, detected: bool, severity: str = "medium"):
        """
        Record drift detection
        
        Args:
            metric_type: Type of metric (price, stock, conversion)
            psi: PSI score
            detected: Whether drift was detected
            severity: Severity level
        """
        if metric_type == "price":
            self.drift_score_price.set(psi)
        elif metric_type == "stock":
            self.drift_score_stock.set(psi)
        
        if detected:
            self.drift_detections.labels(metric_type=metric_type, severity=severity).inc()
    
    def record_anomaly(self, score: float, detected: bool, severity: str = "medium"):
        """
        Record anomaly detection
        
        Args:
            score: Anomaly score
            detected: Whether anomaly was detected
            severity: Severity level
        """
        self.anomaly_score.observe(score)
        if detected:
            self.anomaly_detections.labels(severity=severity).inc()
    
    def update_active_alerts(self, alerts_by_severity_type: Dict[str, Dict[str, int]]):
        """
        Update active alerts gauge
        
        Args:
            alerts_by_severity_type: Dict mapping severity to dict of alert_type to count
        """
        # Reset all to zero first
        for severity in ['low', 'medium', 'high', 'critical']:
            for alert_type in ['contract_violation', 'drift', 'anomaly', 'conversion_deviation']:
                self.active_alerts.labels(severity=severity, alert_type=alert_type).set(0)
        
        # Set actual values
        for severity, alert_types in alerts_by_severity_type.items():
            for alert_type, count in alert_types.items():
                self.active_alerts.labels(severity=severity, alert_type=alert_type).set(count)
    
    def record_alert_created(self, severity: str, alert_type: str, latency: float):
        """
        Record alert creation
        
        Args:
            severity: Alert severity
            alert_type: Alert type
            latency: Time from event to alert in seconds
        """
        self.alert_count.labels(severity=severity, alert_type=alert_type).inc()
        self.alert_latency.observe(latency)
    
    def record_record_processed(self):
        """Record that a record was processed"""
        self.records_processed.inc()
        
        # Update rate (simple moving average over last 10 seconds)
        current_time = time.time()
        time_diff = current_time - self._last_rate_time
        
        if time_diff >= 10.0:  # Update every 10 seconds
            current_count = self.records_processed._value.get()
            count_diff = current_count - self._last_record_count
            rate = count_diff / time_diff if time_diff > 0 else 0.0
            
            self.records_per_second.set(rate)
            
            self._last_record_count = current_count
            self._last_rate_time = current_time
    
    def record_processing_error(self, error_type: str):
        """
        Record processing error
        
        Args:
            error_type: Type of error
        """
        self.processing_errors.labels(error_type=error_type).inc()


# Global metrics instance
metrics = MetricsCollector()


def start_metrics_server(port: int = 8000):
    """
    Start Prometheus metrics HTTP server
    
    Args:
        port: Port to serve metrics on
    """
    start_http_server(port)
    print(f"Prometheus metrics server started on port {port}")

