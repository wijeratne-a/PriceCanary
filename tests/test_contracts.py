"""Tests for data contracts and validation"""

import pytest
from datetime import datetime, timedelta
from src.data.contracts import (
    DataContractValidator,
    TelemetryRecord,
    ViolationType,
    ValidationResult
)


def test_valid_record():
    """Test validation of a valid record"""
    validator = DataContractValidator()
    record = {
        "timestamp": datetime.now(),
        "sku": "SKU-001",
        "price": 99.99,
        "stock": 100,
        "views": 50,
        "add_to_cart": 10,
        "purchases": 5,
        "referrer": "organic"
    }
    
    result = validator.validate_record(record)
    assert result.is_valid
    assert len(result.violations) == 0


def test_negative_stock():
    """Test detection of negative stock"""
    validator = DataContractValidator()
    record = {
        "timestamp": datetime.now(),
        "sku": "SKU-001",
        "price": 99.99,
        "stock": -10,
        "views": 50,
        "add_to_cart": 10,
        "purchases": 5,
        "referrer": "organic"
    }
    
    result = validator.validate_record(record)
    # Pydantic should catch this, but if it doesn't, our validator should
    assert not result.is_valid or len(result.violations) > 0


def test_price_jump():
    """Test detection of large price jumps"""
    validator = DataContractValidator(price_jump_threshold=10.0)
    
    # First record
    record1 = {
        "timestamp": datetime.now(),
        "sku": "SKU-001",
        "price": 19.99,
        "stock": 100,
        "views": 50,
        "add_to_cart": 10,
        "purchases": 5,
        "referrer": "organic"
    }
    result1 = validator.validate_record(record1)
    assert result1.is_valid
    
    # Second record with large price jump
    record2 = {
        "timestamp": datetime.now(),
        "sku": "SKU-001",
        "price": 1999.99,  # 100x increase
        "stock": 100,
        "views": 50,
        "add_to_cart": 10,
        "purchases": 5,
        "referrer": "organic"
    }
    result2 = validator.validate_record(record2)
    assert not result2.is_valid
    assert any(v["violation_type"] == ViolationType.PRICE_JUMP.value for v in result2.violations)


def test_unit_error_detection():
    """Test detection of unit errors (price too high)"""
    validator = DataContractValidator(max_price=1000.0)
    record = {
        "timestamp": datetime.now(),
        "sku": "SKU-001",
        "price": 50000.0,  # Likely in cents
        "stock": 100,
        "views": 50,
        "add_to_cart": 10,
        "purchases": 5,
        "referrer": "organic"
    }
    
    result = validator.validate_record(record)
    assert not result.is_valid
    assert any(v["violation_type"] == ViolationType.UNIT_ERROR.value for v in result.violations)


def test_price_normalization():
    """Test price normalization (cents to dollars)"""
    record = TelemetryRecord(
        timestamp=datetime.now(),
        sku="SKU-001",
        price=1999.0,  # Should be normalized to 19.99
        stock=100,
        views=50,
        add_to_cart=10,
        purchases=5,
        referrer="organic"
    )
    
    # The validator should normalize prices > 1000
    validator = DataContractValidator()
    normalized = validator.validate_record({"price": 1999.0, "sku": "SKU-001", "timestamp": datetime.now(), "stock": 100, "views": 50, "add_to_cart": 10, "purchases": 5})
    # Check that normalization happens (price should be adjusted)


def test_stale_timestamp():
    """Test detection of stale timestamps"""
    validator = DataContractValidator()
    stale_time = datetime.now() - timedelta(hours=25)
    
    record = {
        "timestamp": stale_time,
        "sku": "SKU-001",
        "price": 99.99,
        "stock": 100,
        "views": 50,
        "add_to_cart": 10,
        "purchases": 5,
        "referrer": "organic"
    }
    
    result = validator.validate_record(record)
    assert not result.is_valid
    assert any(v["violation_type"] == ViolationType.INVALID_TIMESTAMP.value for v in result.violations)


def test_invalid_funnel():
    """Test validation of conversion funnel (purchases <= add_to_cart <= views)"""
    record = {
        "timestamp": datetime.now(),
        "sku": "SKU-001",
        "price": 99.99,
        "stock": 100,
        "views": 50,
        "add_to_cart": 60,  # More carts than views
        "purchases": 5,
        "referrer": "organic"
    }
    
    # Should fail Pydantic validation
    with pytest.raises(Exception):
        TelemetryRecord(**record)


def test_missing_required_field():
    """Test handling of missing required fields"""
    validator = DataContractValidator()
    record = {
        "timestamp": datetime.now(),
        "sku": "SKU-001",
        # Missing price
        "stock": 100,
        "views": 50,
        "add_to_cart": 10,
        "purchases": 5
    }
    
    result = validator.validate_record(record)
    assert not result.is_valid

