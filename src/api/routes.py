"""FastAPI routes"""

import time
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from src.api.models import TelemetryRecordRequest, IngestResponse, AlertsResponse, AlertResponse
from src.data.contracts import DataContractValidator
from src.data.violations import ViolationLogger
from src.models.drift import DriftDetector
from src.models.kalman import ConversionKalmanFilter
from src.models.anomaly import AnomalyDetector
from src.api.alerts import AlertManager, AlertSeverity
from src.monitoring.metrics import metrics


# Global instances (would typically use dependency injection)
contract_validator = DataContractValidator()
violation_logger = ViolationLogger()
drift_detector = DriftDetector()
kalman_filter = ConversionKalmanFilter()
anomaly_detector: Optional[AnomalyDetector] = None
alert_manager = AlertManager()


# Initialize anomaly detector with baseline data
def initialize_anomaly_detector():
    """Initialize anomaly detector with synthetic baseline data"""
    global anomaly_detector
    
    from src.data.generator import SyntheticStoreGenerator
    
    generator = SyntheticStoreGenerator(fault_probability=0.0)  # No faults for baseline
    baseline_records = generator.generate_batch(n_records=500)
    
    anomaly_detector = AnomalyDetector(contamination=0.1)
    anomaly_detector.train(baseline_records)
    
    # Populate drift detector baseline
    for record in baseline_records:
        drift_detector.add_to_baseline(record)
    
    print("Anomaly detector and drift baseline initialized")


router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_telemetry(record: TelemetryRecordRequest):
    """
    Ingest telemetry record and perform validation, drift detection, and anomaly detection
    """
    start_time = time.time()
    
    try:
        # Convert to dict
        record_dict = record.model_dump()
        
        # Validate with data contracts
        validation_result = contract_validator.validate_record(record_dict)
        
        # Log violations
        if not validation_result.is_valid:
            violation_logger.log_violations(validation_result.violations)
            metrics.record_validation(False, validation_result.violations[0].get("violation_type") if validation_result.violations else None)
            
            # Create alerts for violations
            alerts_created = 0
            for violation in validation_result.violations:
                alert = alert_manager.create_contract_violation_alert(violation, record_dict)
                if alert:
                    metrics.record_alert_created(
                        alert.severity.value,
                        alert.alert_type,
                        time.time() - start_time
                    )
                    alerts_created += 1
        else:
            metrics.record_validation(True)
            alerts_created = 0
        
        # Update drift detector
        drift_detector.add_to_baseline(record_dict) if not drift_detector.baseline_ready else drift_detector.add_to_recent(record_dict)
        
        # Detect drift
        drift_results = drift_detector.detect_all_drift()
        
        # Create drift alerts
        if drift_results.get("price_drift", {}).get("drift_detected"):
            drift_result = drift_results["price_drift"]
            psi = drift_result.get("psi", 0.0)
            severity = "critical" if psi > 0.5 else "high" if psi > 0.3 else "medium"
            alert = alert_manager.create_drift_alert(drift_result, "price")
            if alert:
                metrics.record_drift("price", psi, True, severity)
                metrics.record_alert_created(severity, "drift", time.time() - start_time)
                alerts_created += 1
        
        if drift_results.get("stock_drift", {}).get("drift_detected"):
            drift_result = drift_results["stock_drift"]
            psi = drift_result.get("psi", 0.0)
            severity = "critical" if psi > 0.5 else "high" if psi > 0.3 else "medium"
            alert = alert_manager.create_drift_alert(drift_result, "stock")
            if alert:
                metrics.record_drift("stock", psi, True, severity)
                metrics.record_alert_created(severity, "drift", time.time() - start_time)
                alerts_created += 1
        
        # Detect anomalies
        if anomaly_detector and anomaly_detector.is_trained:
            anomaly_result = anomaly_detector.predict(record_dict)
            
            if anomaly_result.get("is_anomaly"):
                score = anomaly_result.get("anomaly_score", 0.0)
                severity = "critical" if score < -0.5 else "high" if score < -0.3 else "medium"
                alert = alert_manager.create_anomaly_alert(anomaly_result, record_dict)
                if alert:
                    metrics.record_anomaly(score, True, severity)
                    metrics.record_alert_created(severity, "anomaly", time.time() - start_time)
                    alerts_created += 1
        
        # Check conversion deviation with Kalman filter
        views = record_dict.get("views", 0)
        purchases = record_dict.get("purchases", 0)
        sku = record_dict.get("sku")
        
        if views > 0 and sku:
            deviation_result = kalman_filter.detect_deviation(sku, views, purchases)
            if deviation_result.get("deviation_detected"):
                z_score = deviation_result.get("z_score", 0.0)
                severity = "critical" if z_score > 3.0 else "high" if z_score > 2.5 else "medium"
                alert = alert_manager.create_conversion_deviation_alert(deviation_result, sku)
                if alert:
                    metrics.record_alert_created(severity, "conversion_deviation", time.time() - start_time)
                    alerts_created += 1
        
        # Record metrics
        latency = time.time() - start_time
        status = "success" if validation_result.is_valid else "validation_error"
        metrics.record_ingest(status, latency)
        metrics.record_record_processed()
        
        # Update validation pass rate (simplified - would track over time)
        # This is a placeholder; in production, track over a window
        pass_rate = 1.0 if validation_result.is_valid else 0.0
        metrics.update_validation_pass_rate(pass_rate)
        
        return IngestResponse(
            success=validation_result.is_valid,
            message="Record processed successfully" if validation_result.is_valid else "Record processed with violations",
            violations=validation_result.violations,
            alerts_created=alerts_created
        )
    
    except Exception as e:
        metrics.record_processing_error("exception")
        metrics.record_ingest("error", time.time() - start_time)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@router.get("/alerts", response_model=AlertsResponse)
async def get_alerts(
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    sku: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 100
):
    """
    Get active alerts with optional filtering
    """
    try:
        severity_enum = None
        if severity:
            try:
                severity_enum = AlertSeverity(severity.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        alerts = alert_manager.get_alerts(
            severity=severity_enum,
            alert_type=alert_type,
            sku=sku,
            resolved=resolved,
            limit=limit
        )
        
        # Update active alerts metrics
        alerts_by_severity_type = {}
        for alert in alerts:
            if not alert.get("resolved", False):
                sev = alert.get("severity", "medium")
                atype = alert.get("alert_type", "unknown")
                if sev not in alerts_by_severity_type:
                    alerts_by_severity_type[sev] = {}
                alerts_by_severity_type[sev][atype] = alerts_by_severity_type[sev].get(atype, 0) + 1
        
        metrics.update_active_alerts(alerts_by_severity_type)
        
        return AlertsResponse(
            alerts=[AlertResponse(**alert) for alert in alerts],
            total=len(alerts),
            stats=alert_manager.get_alert_stats()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts: {str(e)}")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert"""
    success = alert_manager.acknowledge_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": True, "message": f"Alert {alert_id} acknowledged"}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Resolve an alert"""
    success = alert_manager.resolve_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": True, "message": f"Alert {alert_id} resolved"}


@router.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics endpoint
    """
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "baseline_ready": drift_detector.baseline_ready,
        "anomaly_detector_trained": anomaly_detector.is_trained if anomaly_detector else False
    }

