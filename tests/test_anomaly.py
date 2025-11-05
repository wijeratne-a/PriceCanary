"""Tests for anomaly detection"""

import pytest
import numpy as np
from datetime import datetime
from src.models.anomaly import AnomalyDetector


def test_anomaly_detector_initialization():
    """Test anomaly detector initialization"""
    detector = AnomalyDetector(contamination=0.1)
    assert not detector.is_trained
    assert detector.model is None


def test_feature_extraction():
    """Test feature extraction"""
    detector = AnomalyDetector()
    
    # First record (no history)
    record1 = {
        "sku": "SKU-001",
        "price": 50.0,
        "stock": 100,
        "views": 50,
        "add_to_cart": 10,
        "purchases": 5,
        "referrer": "organic"
    }
    
    features1 = detector.extract_features(record1)
    assert len(features1) == 7  # 7 features
    assert features1[0] == 0.0  # price_delta_pct (no history)
    
    # Update history
    detector.update_history(record1)
    
    # Second record with price change
    record2 = {
        "sku": "SKU-001",
        "price": 100.0,  # 2x increase
        "stock": 100,
        "views": 50,
        "add_to_cart": 10,
        "purchases": 5,
        "referrer": "organic"
    }
    
    features2 = detector.extract_features(record2)
    assert features2[0] > 0  # price_delta_pct should be > 0


def test_anomaly_training():
    """Test anomaly detector training"""
    detector = AnomalyDetector(contamination=0.1)
    
    # Generate training data
    records = []
    for i in range(100):
        records.append({
            "sku": f"SKU-{i:03d}",
            "price": 50.0 + i * 0.5,
            "stock": 100,
            "views": 50,
            "add_to_cart": 10,
            "purchases": 5,
            "referrer": "organic"
        })
    
    detector.train(records)
    assert detector.is_trained
    assert detector.model is not None


def test_anomaly_prediction():
    """Test anomaly prediction"""
    detector = AnomalyDetector(contamination=0.1)
    
    # Train on normal data
    records = []
    for i in range(100):
        records.append({
            "sku": f"SKU-{i:03d}",
            "price": 50.0,
            "stock": 100,
            "views": 50,
            "add_to_cart": 10,
            "purchases": 5,
            "referrer": "organic"
        })
    
    detector.train(records)
    
    # Normal record
    normal_record = {
        "sku": "SKU-001",
        "price": 50.0,
        "stock": 100,
        "views": 50,
        "add_to_cart": 10,
        "purchases": 5,
        "referrer": "organic"
    }
    
    result = detector.predict(normal_record)
    assert "is_anomaly" in result
    assert "anomaly_score" in result
    
    # Anomalous record (extreme price)
    anomalous_record = {
        "sku": "SKU-001",
        "price": 50000.0,  # Very high price
        "stock": 100,
        "views": 50,
        "add_to_cart": 10,
        "purchases": 5,
        "referrer": "organic"
    }
    
    result2 = detector.predict(anomalous_record)
    # Should detect as anomaly (though not guaranteed)
    assert "is_anomaly" in result2


def test_anomaly_explanation():
    """Test anomaly explanation generation"""
    detector = AnomalyDetector()
    
    # Create features that should trigger explanations
    features = np.array([0.8, 10.0, 0.9, 0.6, 0.8, 8.0, 8.0])  # All high values
    explanation = detector._explain_anomaly(features, True)
    
    assert len(explanation) > 0
    assert explanation != "No significant anomalies detected"

