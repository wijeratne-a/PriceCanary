"""API request/response models"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class TelemetryRecordRequest(BaseModel):
    """Request model for telemetry ingestion"""
    timestamp: datetime
    sku: str
    price: float
    stock: int
    views: int
    add_to_cart: int
    purchases: int
    referrer: Optional[str] = None


class IngestResponse(BaseModel):
    """Response model for ingest endpoint"""
    success: bool
    message: str
    violations: List[Dict[str, Any]] = []
    alerts_created: int = 0


class AlertResponse(BaseModel):
    """Response model for alert"""
    alert_id: str
    alert_type: str
    severity: str
    message: str
    sku: Optional[str]
    timestamp: str
    last_good_state: Dict[str, Any]
    suggested_fix: Optional[str]
    metadata: Dict[str, Any]
    acknowledged: bool
    resolved: bool
    age_seconds: float


class AlertsResponse(BaseModel):
    """Response model for alerts endpoint"""
    alerts: List[AlertResponse]
    total: int
    stats: Dict[str, Any]

