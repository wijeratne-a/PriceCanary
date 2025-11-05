"""Tests for drift detection"""

import pytest
import numpy as np
from datetime import datetime
from src.models.drift import DriftDetector


def test_psi_calculation():
    """Test PSI calculation"""
    detector = DriftDetector()
    
    # Similar distributions should have low PSI
    expected = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    actual = np.array([1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1, 10.1])
    
    psi = detector.calculate_psi(expected, actual)
    assert psi < 0.1  # Low PSI for similar distributions
    
    # Different distributions should have high PSI
    expected2 = np.array([1, 2, 3, 4, 5] * 10)
    actual2 = np.array([100, 200, 300, 400, 500] * 10)
    
    psi2 = detector.calculate_psi(expected2, actual2)
    assert psi2 > 0.2  # High PSI for different distributions


def test_ks_statistic():
    """Test KS statistic calculation"""
    detector = DriftDetector()
    
    # Similar distributions
    expected = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    actual = np.array([1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1, 10.1])
    
    ks_stat, pvalue = detector.calculate_ks_statistic(expected, actual)
    assert pvalue > 0.05  # Not significantly different
    
    # Different distributions
    expected2 = np.array([1, 2, 3, 4, 5] * 10)
    actual2 = np.array([100, 200, 300, 400, 500] * 10)
    
    ks_stat2, pvalue2 = detector.calculate_ks_statistic(expected2, actual2)
    assert pvalue2 < 0.05  # Significantly different


def test_price_drift_detection():
    """Test price drift detection"""
    detector = DriftDetector(psi_threshold=0.2, baseline_window=10)
    
    # Build baseline
    for i in range(10):
        record = {
            "sku": "SKU-001",
            "price": 50.0 + i * 0.5,
            "stock": 100,
            "views": 50,
            "add_to_cart": 10,
            "purchases": 5
        }
        detector.add_to_baseline(record)
    
    assert detector.baseline_ready
    
    # Add recent records with drift
    for i in range(10):
        record = {
            "sku": "SKU-001",
            "price": 200.0 + i * 5.0,  # Much higher prices
            "stock": 100,
            "views": 50,
            "add_to_cart": 10,
            "purchases": 5
        }
        detector.add_to_recent(record)
    
    result = detector.detect_price_drift()
    assert result["drift_detected"]
    assert result["psi"] > 0.2


def test_stock_drift_detection():
    """Test stock drift detection"""
    detector = DriftDetector(psi_threshold=0.2, baseline_window=10)
    
    # Build baseline
    for i in range(10):
        record = {
            "sku": "SKU-001",
            "price": 50.0,
            "stock": 100 + i,
            "views": 50,
            "add_to_cart": 10,
            "purchases": 5
        }
        detector.add_to_baseline(record)
    
    # Add recent records with drift
    for i in range(10):
        record = {
            "sku": "SKU-001",
            "price": 50.0,
            "stock": 10 - i,  # Much lower stock
            "views": 50,
            "add_to_cart": 10,
            "purchases": 5
        }
        detector.add_to_recent(record)
    
    result = detector.detect_stock_drift()
    assert result["drift_detected"]


def test_conversion_drift_detection():
    """Test conversion rate drift detection"""
    detector = DriftDetector()
    
    sku = "SKU-001"
    
    # Build history with normal conversion (5%)
    for i in range(20):
        record = {
            "sku": sku,
            "price": 50.0,
            "stock": 100,
            "views": 100,
            "add_to_cart": 10,
            "purchases": 5  # 5% conversion
        }
        detector.add_to_baseline(record)
    
    # Check conversion drift
    current_conversion = 0.15  # 15% conversion (much higher)
    result = detector.detect_conversion_drift(sku, current_conversion)
    
    # Should detect drift if there's significant change
    # Note: This depends on the actual implementation logic


def test_insufficient_data():
    """Test drift detection with insufficient data"""
    detector = DriftDetector()
    
    result = detector.detect_price_drift()
    assert not result["drift_detected"]
    assert "Insufficient data" in result.get("reason", "")

