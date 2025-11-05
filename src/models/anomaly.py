"""IsolationForest-based anomaly detection for e-commerce telemetry"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from sklearn.ensemble import IsolationForest
from collections import defaultdict


class AnomalyDetector:
    """Anomaly detection using IsolationForest with feature engineering"""
    
    def __init__(
        self,
        contamination: float = 0.1,
        n_estimators: int = 100,
        random_state: int = 42
    ):
        """
        Initialize anomaly detector
        
        Args:
            contamination: Expected proportion of anomalies (0.0 to 0.5)
            n_estimators: Number of trees in IsolationForest
            random_state: Random seed for reproducibility
        """
        self.contamination = contamination
        self.model: Optional[IsolationForest] = None
        self.is_trained = False
        
        # Store historical data for feature engineering
        self.price_history: Dict[str, List[float]] = defaultdict(list)
        self.stock_history: Dict[str, List[int]] = defaultdict(list)
        self.referrer_counts: Dict[str, int] = defaultdict(int)
        self.conversion_history: Dict[str, List[float]] = defaultdict(list)
        
        # Track last values for delta calculations
        self.last_price: Dict[str, float] = {}
        self.last_stock: Dict[str, int] = {}
        
        # Normal reference data
        self.normal_referrers = set()
        self.normal_price_range = (0, 1000)
        self.normal_stock_range = (0, 10000)
        
        self.random_state = random_state
    
    def extract_features(self, record: Dict[str, any]) -> np.ndarray:
        """
        Extract features for anomaly detection
        
        Features:
        1. price_delta_pct: Percentage change in price from last value
        2. stock_change: Absolute change in stock
        3. referrer_irregularity: Unusual referrer patterns
        4. conversion_deviation: Deviation from expected conversion
        
        Args:
            record: Telemetry record dictionary
            
        Returns:
            Feature vector as numpy array
        """
        sku = record.get("sku", "unknown")
        price = float(record.get("price", 0))
        stock = int(record.get("stock", 0))
        views = int(record.get("views", 0))
        add_to_cart = int(record.get("add_to_cart", 0))
        purchases = int(record.get("purchases", 0))
        referrer = record.get("referrer", "unknown")
        
        # Feature 1: Price delta percentage
        if sku in self.last_price and self.last_price[sku] > 0:
            price_delta_pct = abs((price - self.last_price[sku]) / self.last_price[sku])
        else:
            price_delta_pct = 0.0
        
        # Feature 2: Stock change
        if sku in self.last_stock:
            stock_change = abs(stock - self.last_stock[sku])
        else:
            stock_change = 0
        
        # Feature 3: Referrer irregularity
        # Measure how unusual this referrer is (based on frequency)
        total_referrers = sum(self.referrer_counts.values())
        if total_referrers > 0:
            referrer_freq = self.referrer_counts.get(referrer, 0) / total_referrers
            referrer_irregularity = 1.0 - referrer_freq  # Higher = more irregular
        else:
            referrer_irregularity = 0.5
        
        # Feature 4: Conversion deviation
        # Calculate conversion rate and compare to historical
        if views > 0:
            current_conversion = purchases / views
            if sku in self.conversion_history and len(self.conversion_history[sku]) > 0:
                avg_conversion = np.mean(self.conversion_history[sku])
                if avg_conversion > 0:
                    conversion_deviation = abs((current_conversion - avg_conversion) / avg_conversion)
                else:
                    conversion_deviation = 1.0 if current_conversion > 0 else 0.0
            else:
                conversion_deviation = 0.5  # Default for new SKUs
        else:
            conversion_deviation = 0.0
        
        # Feature 5: Views to cart ratio irregularity
        if views > 0:
            cart_rate = add_to_cart / views
            # Normal cart rate is typically 10-30%
            if cart_rate > 0.5 or cart_rate < 0.01:
                cart_irregularity = 1.0
            else:
                cart_irregularity = 0.0
        else:
            cart_irregularity = 0.0
        
        # Feature 6: Price magnitude (normalized)
        price_magnitude = min(price / 1000.0, 10.0)  # Cap at 10
        
        # Feature 7: Stock magnitude (normalized)
        stock_magnitude = min(stock / 1000.0, 10.0)  # Cap at 10
        
        features = np.array([
            price_delta_pct,
            stock_change / 100.0,  # Normalize
            referrer_irregularity,
            conversion_deviation,
            cart_irregularity,
            price_magnitude,
            stock_magnitude
        ])
        
        return features
    
    def update_history(self, record: Dict[str, any]):
        """
        Update historical data for feature engineering
        
        Args:
            record: Telemetry record dictionary
        """
        sku = record.get("sku", "unknown")
        price = float(record.get("price", 0))
        stock = int(record.get("stock", 0))
        views = int(record.get("views", 0))
        purchases = int(record.get("purchases", 0))
        referrer = record.get("referrer", "unknown")
        
        # Update price history
        self.price_history[sku].append(price)
        if len(self.price_history[sku]) > 100:
            self.price_history[sku] = self.price_history[sku][-100:]
        
        # Update stock history
        self.stock_history[sku].append(stock)
        if len(self.stock_history[sku]) > 100:
            self.stock_history[sku] = self.stock_history[sku][-100:]
        
        # Update referrer counts
        self.referrer_counts[referrer] += 1
        
        # Update conversion history
        if views > 0:
            conversion = purchases / views
            self.conversion_history[sku].append(conversion)
            if len(self.conversion_history[sku]) > 100:
                self.conversion_history[sku] = self.conversion_history[sku][-100:]
        
        # Update last values
        self.last_price[sku] = price
        self.last_stock[sku] = stock
    
    def train(self, records: List[Dict[str, any]]):
        """
        Train IsolationForest on baseline data
        
        Args:
            records: List of telemetry records for training
        """
        if len(records) < 10:
            raise ValueError("Need at least 10 records for training")
        
        # Extract features for all records
        features_list = []
        for record in records:
            self.update_history(record)
            features = self.extract_features(record)
            features_list.append(features)
        
        X = np.array(features_list)
        
        # Train IsolationForest
        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=100,
            random_state=self.random_state,
            n_jobs=-1
        )
        self.model.fit(X)
        self.is_trained = True
    
    def predict(self, record: Dict[str, any]) -> Dict[str, any]:
        """
        Predict if a record is an anomaly
        
        Args:
            record: Telemetry record dictionary
            
        Returns:
            Dictionary with anomaly detection results
        """
        if not self.is_trained or self.model is None:
            return {
                "is_anomaly": False,
                "anomaly_score": 0.0,
                "reason": "Model not trained"
            }
        
        # Extract features
        features = self.extract_features(record)
        X = features.reshape(1, -1)
        
        # Predict
        prediction = self.model.predict(X)[0]  # -1 for anomaly, 1 for normal
        score = self.model.score_samples(X)[0]  # Lower score = more anomalous
        
        is_anomaly = prediction == -1
        
        # Update history for next prediction
        self.update_history(record)
        
        # Generate explanation
        explanation = self._explain_anomaly(features, is_anomaly)
        
        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": float(score),
            "prediction": int(prediction),
            "features": {
                "price_delta_pct": float(features[0]),
                "stock_change": float(features[1] * 100),
                "referrer_irregularity": float(features[2]),
                "conversion_deviation": float(features[3]),
                "cart_irregularity": float(features[4]),
                "price_magnitude": float(features[5]),
                "stock_magnitude": float(features[6])
            },
            "explanation": explanation
        }
    
    def _explain_anomaly(self, features: np.ndarray, is_anomaly: bool) -> str:
        """
        Generate human-readable explanation for anomaly
        
        Args:
            features: Feature vector
            is_anomaly: Whether this is an anomaly
            
        Returns:
            Explanation string
        """
        if not is_anomaly:
            return "No significant anomalies detected"
        
        explanations = []
        
        if features[0] > 0.5:  # price_delta_pct
            explanations.append(f"Large price change ({features[0]*100:.1f}%)")
        
        if features[1] > 5.0:  # stock_change (normalized)
            explanations.append(f"Significant stock change ({features[1]*100:.0f} units)")
        
        if features[2] > 0.7:  # referrer_irregularity
            explanations.append("Unusual referrer pattern")
        
        if features[3] > 0.5:  # conversion_deviation
            explanations.append("Conversion rate deviation")
        
        if features[4] > 0.5:  # cart_irregularity
            explanations.append("Abnormal cart-to-view ratio")
        
        if features[5] > 5.0:  # price_magnitude
            explanations.append("Unusually high price")
        
        if features[6] > 5.0:  # stock_magnitude
            explanations.append("Unusually high stock level")
        
        if explanations:
            return "; ".join(explanations)
        else:
            return "Multiple subtle anomalies detected"

