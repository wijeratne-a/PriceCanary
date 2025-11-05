"""Data contracts and validation using Pydantic and Pandera"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, validator
import pandas as pd
import pandera as pa
from pandera import Column, DataFrameSchema, Check


class ViolationType(str, Enum):
    """Types of data contract violations"""
    SCHEMA_ERROR = "schema_error"
    NEGATIVE_STOCK = "negative_stock"
    PRICE_JUMP = "price_jump"
    UNIT_ERROR = "unit_error"
    INVALID_TIMESTAMP = "invalid_timestamp"
    MISSING_REQUIRED = "missing_required"
    OUT_OF_BOUNDS = "out_of_bounds"


class TelemetryRecord(BaseModel):
    """Pydantic model for e-commerce telemetry records"""
    timestamp: datetime = Field(..., description="Event timestamp")
    sku: str = Field(..., min_length=1, description="Stock keeping unit identifier")
    price: float = Field(..., gt=0, description="Price in dollars (normalized)")
    stock: int = Field(..., ge=0, description="Stock quantity (non-negative)")
    views: int = Field(..., ge=0, description="Page views count")
    add_to_cart: int = Field(..., ge=0, description="Add to cart events")
    purchases: int = Field(..., ge=0, description="Purchase count")
    referrer: Optional[str] = Field(None, description="Traffic referrer source")

    @validator('price', pre=True)
    def normalize_price(cls, v):
        """Normalize price: if > 1000, assume cents, divide by 100"""
        if isinstance(v, (int, float)):
            if v > 1000:
                return v / 100.0
            return float(v)
        return v

    @validator('add_to_cart')
    def validate_add_to_cart(cls, v, values):
        """Add to cart should not exceed views"""
        if 'views' in values and v > values['views']:
            raise ValueError('add_to_cart cannot exceed views')
        return v

    @validator('purchases')
    def validate_purchases(cls, v, values):
        """Purchases should not exceed add_to_cart"""
        if 'add_to_cart' in values and v > values['add_to_cart']:
            raise ValueError('purchases cannot exceed add_to_cart')
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ValidationResult:
    """Result of data contract validation"""
    def __init__(
        self,
        is_valid: bool,
        violations: List[Dict[str, Any]] = None,
        normalized_data: Optional[pd.DataFrame] = None
    ):
        self.is_valid = is_valid
        self.violations = violations or []
        self.normalized_data = normalized_data

    def add_violation(
        self,
        violation_type: ViolationType,
        reason: str,
        sku: Optional[str] = None,
        severity: str = "medium"
    ):
        """Add a violation to the result"""
        self.violations.append({
            "timestamp": datetime.now().isoformat(),
            "sku": sku,
            "violation_type": violation_type.value,
            "reason": reason,
            "severity": severity
        })
        self.is_valid = False


# Pandera schema for DataFrame validation
TELEMETRY_SCHEMA = DataFrameSchema({
    "timestamp": Column(pd.DatetimeTZDtype, nullable=False),
    "sku": Column(str, nullable=False, checks=Check.str_length(min_value=1)),
    "price": Column(
        float,
        nullable=False,
        checks=[
            Check.greater_than(0),
            Check.less_than_or_equal_to(100000)  # Reasonable upper bound
        ]
    ),
    "stock": Column(
        int,
        nullable=False,
        checks=Check.greater_than_or_equal_to(0)
    ),
    "views": Column(
        int,
        nullable=False,
        checks=Check.greater_than_or_equal_to(0)
    ),
    "add_to_cart": Column(
        int,
        nullable=False,
        checks=[
            Check.greater_than_or_equal_to(0),
            Check(lambda s: s <= s["views"], element_wise=False, error="add_to_cart cannot exceed views")
        ]
    ),
    "purchases": Column(
        int,
        nullable=False,
        checks=[
            Check.greater_than_or_equal_to(0),
            Check(lambda s: s <= s["add_to_cart"], element_wise=False, error="purchases cannot exceed add_to_cart")
        ]
    ),
    "referrer": Column(str, nullable=True)
})


class DataContractValidator:
    """Validates telemetry data against contracts"""
    
    def __init__(self, price_jump_threshold: float = 10.0, max_price: float = 100000.0):
        """
        Initialize validator
        
        Args:
            price_jump_threshold: Multiplicative factor for price jump detection (e.g., 10.0 = 10x)
            max_price: Maximum acceptable price in dollars
        """
        self.price_jump_threshold = price_jump_threshold
        self.max_price = max_price
        self.price_history: Dict[str, List[float]] = {}  # Track price history per SKU
        
    def validate_record(self, record: Dict[str, Any]) -> ValidationResult:
        """
        Validate a single telemetry record
        
        Args:
            record: Dictionary with telemetry data
            
        Returns:
            ValidationResult with validation status and violations
        """
        result = ValidationResult(is_valid=True)
        
        # Validate with Pydantic
        try:
            telemetry = TelemetryRecord(**record)
            normalized_record = telemetry.dict()
        except Exception as e:
            result.add_violation(
                ViolationType.SCHEMA_ERROR,
                f"Pydantic validation failed: {str(e)}",
                record.get("sku"),
                "high"
            )
            return result
        
        sku = normalized_record["sku"]
        price = normalized_record["price"]
        
        # Check for negative stock (should be caught by Pydantic, but double-check)
        if normalized_record["stock"] < 0:
            result.add_violation(
                ViolationType.NEGATIVE_STOCK,
                f"Stock value is negative: {normalized_record['stock']}",
                sku,
                "high"
            )
        
        # Check for unit errors (price seems too high or too low)
        if price > self.max_price:
            result.add_violation(
                ViolationType.UNIT_ERROR,
                f"Price {price} exceeds maximum threshold {self.max_price} - possible unit error",
                sku,
                "critical"
            )
        
        # Check for large price jumps
        if sku in self.price_history and len(self.price_history[sku]) > 0:
            last_price = self.price_history[sku][-1]
            if last_price > 0:
                price_change_ratio = price / last_price
                if price_change_ratio > self.price_jump_threshold:
                    result.add_violation(
                        ViolationType.PRICE_JUMP,
                        f"Price jumped from {last_price} to {price} ({price_change_ratio:.2f}x) - exceeds threshold {self.price_jump_threshold}x",
                        sku,
                        "critical"
                    )
                elif price_change_ratio < (1.0 / self.price_jump_threshold):
                    result.add_violation(
                        ViolationType.PRICE_JUMP,
                        f"Price dropped from {last_price} to {price} ({1/price_change_ratio:.2f}x decrease) - exceeds threshold",
                        sku,
                        "high"
                    )
        
        # Update price history
        if sku not in self.price_history:
            self.price_history[sku] = []
        self.price_history[sku].append(price)
        # Keep only last 100 prices per SKU
        if len(self.price_history[sku]) > 100:
            self.price_history[sku] = self.price_history[sku][-100:]
        
        # Check timestamp freshness (within last 24 hours)
        timestamp = normalized_record["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
        time_diff = (now - timestamp).total_seconds()
        
        if time_diff > 86400:  # 24 hours
            result.add_violation(
                ViolationType.INVALID_TIMESTAMP,
                f"Timestamp is {time_diff/3600:.1f} hours old - possible stale feed",
                sku,
                "medium"
            )
        elif time_diff < -3600:  # More than 1 hour in future
            result.add_violation(
                ViolationType.INVALID_TIMESTAMP,
                f"Timestamp is {abs(time_diff)/3600:.1f} hours in future - possible timezone error",
                sku,
                "medium"
            )
        
        if result.is_valid:
            result.normalized_data = pd.DataFrame([normalized_record])
        
        return result
    
    def validate_dataframe(self, df: pd.DataFrame) -> ValidationResult:
        """
        Validate a DataFrame of telemetry records
        
        Args:
            df: DataFrame with telemetry data
            
        Returns:
            ValidationResult with validation status and violations
        """
        result = ValidationResult(is_valid=True)
        
        # Validate with Pandera schema
        try:
            validated_df = TELEMETRY_SCHEMA.validate(df)
            result.normalized_data = validated_df
        except pa.errors.SchemaError as e:
            result.add_violation(
                ViolationType.SCHEMA_ERROR,
                f"Pandera validation failed: {str(e)}",
                severity="high"
            )
            return result
        
        # Apply business logic checks
        for idx, row in df.iterrows():
            record_result = self.validate_record(row.to_dict())
            if not record_result.is_valid:
                result.violations.extend(record_result.violations)
        
        result.is_valid = len(result.violations) == 0
        
        return result

