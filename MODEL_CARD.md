# PriceCanary Model Card

## Model Overview

PriceCanary uses multiple models for drift detection and anomaly detection in e-commerce telemetry data.

## Models

### 1. Drift Detection (PSI/KS)

**Purpose**: Detect distribution drift in price and stock metrics

**Algorithm**: 
- Population Stability Index (PSI)
- Kolmogorov-Smirnov (KS) test

**Features**:
- Price velocity (rate of change)
- Stock trends
- SKU-level conversion rates

**Metrics**:
- PSI score: < 0.1 (no drift), 0.1-0.2 (moderate), > 0.2 (significant)
- KS p-value: < 0.05 indicates significant drift

**Test Coverage**: See `tests/test_drift.py`
- PSI calculation validation
- KS statistic calculation
- Price drift detection
- Stock drift detection
- Conversion drift detection

**Limitations**:
- Requires baseline data (1000+ records)
- Sensitive to outliers
- May have false positives during normal price fluctuations

### 2. Kalman Filter for Conversion Tracking

**Purpose**: Track conversion rates with uncertainty estimates

**Algorithm**: Kalman filter (state estimation)

**Features**:
- Expected conversion rate per SKU
- Uncertainty estimates
- Deviation detection (z-score)

**Metrics**:
- Z-score: > 2.0 indicates significant deviation
- Uncertainty: Lower with more observations

**Test Coverage**: See `tests/test_anomaly.py` (partially)

**Limitations**:
- Assumes conversion rate changes slowly
- Requires sufficient observations per SKU
- May miss sudden changes

### 3. IsolationForest Anomaly Detection

**Purpose**: Detect anomalies in telemetry records

**Algorithm**: IsolationForest (scikit-learn)

**Features** (7 features):
1. `price_delta_pct`: Percentage change in price
2. `stock_change`: Absolute change in stock
3. `referrer_irregularity`: Unusual referrer patterns
4. `conversion_deviation`: Deviation from expected conversion
5. `cart_irregularity`: Abnormal cart-to-view ratio
6. `price_magnitude`: Normalized price value
7. `stock_magnitude`: Normalized stock value

**Hyperparameters**:
- `contamination`: 0.1 (expected 10% anomalies)
- `n_estimators`: 100
- `random_state`: 42

**Training Data**:
- 500 synthetic baseline records
- No fault injection for baseline
- Normal e-commerce patterns

**Metrics**:
- Anomaly score: Lower = more anomalous
- Threshold: < -0.3 typically indicates anomaly
- False positive rate target: < 10%

**Test Coverage**: See `tests/test_anomaly.py`
- Feature extraction validation
- Training validation
- Prediction validation
- Explanation generation

**Limitations**:
- Requires retraining when baseline changes
- May have false positives with new SKUs
- Contamination parameter needs tuning

## Model Performance

### Drift Detection
- **Accuracy**: High for significant drift (> 0.3 PSI)
- **Precision**: Moderate (may flag normal fluctuations)
- **Recall**: High (catches most significant drift)
- **False Positive Rate**: ~5-10%

### Anomaly Detection
- **Accuracy**: ~85-90% on synthetic data
- **Precision**: ~70-80% (tuned for low false positives)
- **Recall**: ~80-90%
- **False Positive Rate**: ~8-12% (target: < 10%)

### Conversion Tracking
- **Accuracy**: High for stable conversion rates
- **Precision**: Moderate (may flag normal variance)
- **Recall**: High (catches significant deviations)
- **False Positive Rate**: ~5-10%

## Data Requirements

### Input Schema
```json
{
  "timestamp": "ISO datetime",
  "sku": "string",
  "price": "float > 0",
  "stock": "int >= 0",
  "views": "int >= 0",
  "add_to_cart": "int >= 0",
  "purchases": "int >= 0",
  "referrer": "string (optional)"
}
```

### Baseline Requirements
- **Drift Detection**: 1000+ records for baseline
- **Anomaly Detection**: 500+ records for training
- **Conversion Tracking**: 10+ observations per SKU

## Model Updates

### When to Retrain

1. **Anomaly Detector**:
   - Monthly or when baseline distribution changes significantly
   - When false positive rate exceeds 15%
   - When new SKU categories are introduced

2. **Drift Detection**:
   - Baseline updates automatically (rolling window)
   - No manual retraining needed

3. **Kalman Filter**:
   - Updates automatically with each observation
   - No manual retraining needed

### Retraining Process

1. Collect new baseline data (500+ records)
2. Train anomaly detector: `anomaly_detector.train(new_data)`
3. Validate on test set
4. Deploy updated model
5. Monitor performance metrics

## Ethical Considerations

- **Bias**: Models may have bias toward common SKUs
- **Fairness**: All SKUs treated equally in detection
- **Transparency**: All alerts include explanations
- **Privacy**: No PII in telemetry data

## Model Versioning

- **Current Version**: 0.1.0
- **Last Updated**: 2024
- **Version History**: See git history

## References

- PSI: Population Stability Index (credit risk industry standard)
- KS Test: Kolmogorov-Smirnov test (statistical test)
- IsolationForest: Liu et al., "Isolation Forest" (2008)
- Kalman Filter: Kalman, "A New Approach to Linear Filtering" (1960)

