"""Alert consolidation and enrichment system"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from collections import defaultdict


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert:
    """Represents a single alert"""
    
    def __init__(
        self,
        alert_id: str,
        alert_type: str,
        severity: AlertSeverity,
        message: str,
        sku: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        last_good_state: Optional[Dict[str, Any]] = None,
        suggested_fix: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.alert_id = alert_id
        self.alert_type = alert_type
        self.severity = severity
        self.message = message
        self.sku = sku
        self.timestamp = timestamp or datetime.now()
        self.last_good_state = last_good_state or {}
        self.suggested_fix = suggested_fix
        self.metadata = metadata or {}
        self.acknowledged = False
        self.resolved = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type,
            "severity": self.severity.value,
            "message": self.message,
            "sku": self.sku,
            "timestamp": self.timestamp.isoformat(),
            "last_good_state": self.last_good_state,
            "suggested_fix": self.suggested_fix,
            "metadata": self.metadata,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "age_seconds": (datetime.now() - self.timestamp).total_seconds()
        }


class AlertManager:
    """Manages and consolidates alerts from various sources"""
    
    def __init__(self, alert_ttl_seconds: int = 3600):
        """
        Initialize alert manager
        
        Args:
            alert_ttl_seconds: Time-to-live for alerts in seconds
        """
        self.alerts: Dict[str, Alert] = {}
        self.alert_ttl = timedelta(seconds=alert_ttl_seconds)
        self.alert_counter = 0
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID"""
        self.alert_counter += 1
        return f"ALERT-{datetime.now().strftime('%Y%m%d')}-{self.alert_counter:06d}"
    
    def create_alert(
        self,
        alert_type: str,
        severity: AlertSeverity,
        message: str,
        sku: Optional[str] = None,
        last_good_state: Optional[Dict[str, Any]] = None,
        suggested_fix: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """
        Create a new alert
        
        Args:
            alert_type: Type of alert (e.g., "contract_violation", "drift", "anomaly")
            severity: Severity level
            message: Human-readable message
            sku: SKU identifier (optional)
            last_good_state: Last known good state
            suggested_fix: Suggested remediation action
            metadata: Additional metadata
            
        Returns:
            Created Alert object
        """
        alert_id = self._generate_alert_id()
        alert = Alert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            sku=sku,
            last_good_state=last_good_state,
            suggested_fix=suggested_fix,
            metadata=metadata
        )
        
        self.alerts[alert_id] = alert
        return alert
    
    def create_contract_violation_alert(
        self,
        violation: Dict[str, Any],
        record: Dict[str, Any]
    ) -> Optional[Alert]:
        """
        Create alert from contract violation
        
        Args:
            violation: Violation dictionary
            record: Original telemetry record
            
        Returns:
            Alert object or None
        """
        violation_type = violation.get("violation_type", "unknown")
        severity_str = violation.get("severity", "medium")
        
        # Map severity string to enum
        severity_map = {
            "low": AlertSeverity.LOW,
            "medium": AlertSeverity.MEDIUM,
            "high": AlertSeverity.HIGH,
            "critical": AlertSeverity.CRITICAL
        }
        severity = severity_map.get(severity_str.lower(), AlertSeverity.MEDIUM)
        
        # Determine suggested fix based on violation type
        suggested_fix = self._suggest_fix_for_violation(violation_type, record)
        
        # Get last good state (previous record if available)
        last_good_state = {
            "price": record.get("price"),
            "stock": record.get("stock"),
            "timestamp": record.get("timestamp")
        }
        
        return self.create_alert(
            alert_type="contract_violation",
            severity=severity,
            message=violation.get("reason", "Data contract violation"),
            sku=violation.get("sku"),
            last_good_state=last_good_state,
            suggested_fix=suggested_fix,
            metadata={"violation_type": violation_type}
        )
    
    def create_drift_alert(
        self,
        drift_result: Dict[str, Any],
        metric_type: str
    ) -> Optional[Alert]:
        """
        Create alert from drift detection
        
        Args:
            drift_result: Drift detection result
            metric_type: Type of metric (price, stock, conversion)
            
        Returns:
            Alert object or None
        """
        if not drift_result.get("drift_detected", False):
            return None
        
        # Determine severity based on PSI and KS values
        psi = drift_result.get("psi", 0.0)
        ks_pvalue = drift_result.get("ks_pvalue", 1.0)
        
        if psi > 0.5 or ks_pvalue < 0.01:
            severity = AlertSeverity.CRITICAL
        elif psi > 0.3 or ks_pvalue < 0.05:
            severity = AlertSeverity.HIGH
        else:
            severity = AlertSeverity.MEDIUM
        
        baseline_mean = drift_result.get("baseline_mean", 0)
        recent_mean = drift_result.get("recent_mean", 0)
        
        message = (
            f"{metric_type.capitalize()} drift detected: "
            f"PSI={psi:.3f}, KS p-value={ks_pvalue:.4f}. "
            f"Baseline: {baseline_mean:.2f}, Recent: {recent_mean:.2f}"
        )
        
        suggested_fix = f"Review {metric_type} trends and investigate root cause. Check for data quality issues or system changes."
        
        last_good_state = {
            f"baseline_{metric_type}": baseline_mean,
            f"baseline_std": drift_result.get("baseline_std", 0)
        }
        
        return self.create_alert(
            alert_type="drift",
            severity=severity,
            message=message,
            last_good_state=last_good_state,
            suggested_fix=suggested_fix,
            metadata={
                "metric_type": metric_type,
                "psi": psi,
                "ks_pvalue": ks_pvalue,
                "baseline_mean": baseline_mean,
                "recent_mean": recent_mean
            }
        )
    
    def create_anomaly_alert(
        self,
        anomaly_result: Dict[str, Any],
        record: Dict[str, Any]
    ) -> Optional[Alert]:
        """
        Create alert from anomaly detection
        
        Args:
            anomaly_result: Anomaly detection result
            record: Original telemetry record
            
        Returns:
            Alert object or None
        """
        if not anomaly_result.get("is_anomaly", False):
            return None
        
        score = anomaly_result.get("anomaly_score", 0.0)
        
        # Determine severity based on anomaly score
        # Lower score = more anomalous
        if score < -0.5:
            severity = AlertSeverity.CRITICAL
        elif score < -0.3:
            severity = AlertSeverity.HIGH
        else:
            severity = AlertSeverity.MEDIUM
        
        message = f"Anomaly detected: {anomaly_result.get('explanation', 'Unusual pattern detected')}"
        
        suggested_fix = "Investigate data quality and system behavior. Check for bot activity, data pipeline issues, or pricing errors."
        
        last_good_state = {
            "price": record.get("price"),
            "stock": record.get("stock"),
            "views": record.get("views"),
            "purchases": record.get("purchases")
        }
        
        return self.create_alert(
            alert_type="anomaly",
            severity=severity,
            message=message,
            sku=record.get("sku"),
            last_good_state=last_good_state,
            suggested_fix=suggested_fix,
            metadata={
                "anomaly_score": score,
                "features": anomaly_result.get("features", {}),
                "explanation": anomaly_result.get("explanation", "")
            }
        )
    
    def create_conversion_deviation_alert(
        self,
        deviation_result: Dict[str, Any],
        sku: str
    ) -> Optional[Alert]:
        """
        Create alert from conversion rate deviation (Kalman filter)
        
        Args:
            deviation_result: Deviation detection result
            sku: SKU identifier
            
        Returns:
            Alert object or None
        """
        if not deviation_result.get("deviation_detected", False):
            return None
        
        z_score = deviation_result.get("z_score", 0.0)
        expected = deviation_result.get("expected_conversion", 0.0)
        observed = deviation_result.get("observed_conversion", 0.0)
        
        if z_score > 3.0:
            severity = AlertSeverity.CRITICAL
        elif z_score > 2.5:
            severity = AlertSeverity.HIGH
        else:
            severity = AlertSeverity.MEDIUM
        
        message = (
            f"Conversion rate deviation for {sku}: "
            f"Expected {expected:.2%}, Observed {observed:.2%} "
            f"(z-score: {z_score:.2f})"
        )
        
        suggested_fix = "Review conversion funnel and user behavior. Check for checkout issues, pricing problems, or inventory availability."
        
        return self.create_alert(
            alert_type="conversion_deviation",
            severity=severity,
            message=message,
            sku=sku,
            last_good_state={
                "expected_conversion": expected,
                "uncertainty": deviation_result.get("uncertainty", 0.0)
            },
            suggested_fix=suggested_fix,
            metadata={
                "z_score": z_score,
                "expected_conversion": expected,
                "observed_conversion": observed,
                "deviation_pct": deviation_result.get("deviation_pct", 0.0)
            }
        )
    
    def _suggest_fix_for_violation(self, violation_type: str, record: Dict[str, Any]) -> str:
        """Generate suggested fix based on violation type"""
        fixes = {
            "negative_stock": "Fix data pipeline to ensure stock values are non-negative. Check for integer overflow or data corruption.",
            "price_jump": "Verify price updates are correct. Check for unit conversion errors or data entry mistakes.",
            "unit_error": "Normalize price units (ensure consistent dollars/cents). Review data source configuration.",
            "invalid_timestamp": "Check data feed freshness and timezone settings. Verify system clock synchronization.",
            "schema_error": "Validate data schema matches expected format. Check for missing or malformed fields."
        }
        
        return fixes.get(violation_type, "Review data quality and system configuration.")
    
    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[str] = None,
        sku: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get alerts with optional filtering
        
        Args:
            severity: Filter by severity
            alert_type: Filter by alert type
            sku: Filter by SKU
            resolved: Filter by resolved status
            limit: Maximum number of alerts to return
            
        Returns:
            List of alert dictionaries
        """
        # Clean up expired alerts
        self._cleanup_expired()
        
        alerts = []
        for alert in self.alerts.values():
            if severity and alert.severity != severity:
                continue
            if alert_type and alert.alert_type != alert_type:
                continue
            if sku and alert.sku != sku:
                continue
            if resolved is not None and alert.resolved != resolved:
                continue
            
            alerts.append(alert.to_dict())
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return alerts[:limit]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged"""
        if alert_id in self.alerts:
            self.alerts[alert_id].acknowledged = True
            return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved"""
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved = True
            return True
        return False
    
    def _cleanup_expired(self):
        """Remove expired alerts"""
        now = datetime.now()
        expired_ids = [
            alert_id
            for alert_id, alert in self.alerts.items()
            if now - alert.timestamp > self.alert_ttl
        ]
        for alert_id in expired_ids:
            del self.alerts[alert_id]
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get statistics about alerts"""
        self._cleanup_expired()
        
        stats = {
            "total": len(self.alerts),
            "by_severity": defaultdict(int),
            "by_type": defaultdict(int),
            "unresolved": 0,
            "unacknowledged": 0
        }
        
        for alert in self.alerts.values():
            stats["by_severity"][alert.severity.value] += 1
            stats["by_type"][alert.alert_type] += 1
            if not alert.resolved:
                stats["unresolved"] += 1
            if not alert.acknowledged:
                stats["unacknowledged"] += 1
        
        return dict(stats)

