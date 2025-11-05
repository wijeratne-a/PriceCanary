"""Drift detection using PSI (Population Stability Index) and KS (Kolmogorov-Smirnov) tests"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from scipy import stats


class DriftDetector:
    """Detects drift in e-commerce metrics using PSI and KS tests"""
    
    def __init__(
        self,
        psi_threshold: float = 0.2,
        ks_threshold: float = 0.05,
        baseline_window: int = 1000
    ):
        """
        Initialize drift detector
        
        Args:
            psi_threshold: PSI threshold for drift detection (>0.2 indicates significant drift)
            ks_threshold: KS test p-value threshold (<0.05 indicates significant drift)
            baseline_window: Number of records to use for baseline
        """
        self.psi_threshold = psi_threshold
        self.ks_threshold = ks_threshold
        self.baseline_window = baseline_window
        
        # Store baseline data
        self.baseline_data: Dict[str, List[float]] = defaultdict(list)
        self.baseline_ready = False
        
        # Store recent data for comparison
        self.recent_data: Dict[str, List[float]] = defaultdict(list)
        
        # SKU-level conversion tracking
        self.sku_conversion_history: Dict[str, List[Tuple[float, int]]] = defaultdict(list)
        # Format: (conversion_rate, timestamp_ordinal)
    
    def calculate_psi(self, expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
        """
        Calculate Population Stability Index (PSI)
        
        PSI measures how much a distribution has shifted over time.
        PSI < 0.1: No significant change
        PSI 0.1-0.2: Moderate change
        PSI > 0.2: Significant change
        
        Args:
            expected: Baseline distribution
            actual: Current distribution
            bins: Number of bins for histogram
            
        Returns:
            PSI value
        """
        if len(expected) == 0 or len(actual) == 0:
            return 0.0
        
        # Find common range
        min_val = min(np.min(expected), np.min(actual))
        max_val = max(np.max(expected), np.max(actual))
        
        if min_val == max_val:
            return 0.0
        
        # Create bins
        bin_edges = np.linspace(min_val, max_val, bins + 1)
        
        # Calculate histograms
        expected_hist, _ = np.histogram(expected, bins=bin_edges)
        actual_hist, _ = np.histogram(actual, bins=bin_edges)
        
        # Normalize to probabilities
        expected_pct = expected_hist / len(expected)
        actual_pct = actual_hist / len(actual)
        
        # Avoid division by zero
        expected_pct = np.where(expected_pct == 0, 1e-10, expected_pct)
        actual_pct = np.where(actual_pct == 0, 1e-10, actual_pct)
        
        # Calculate PSI
        psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
        
        return float(psi)
    
    def calculate_ks_statistic(self, expected: np.ndarray, actual: np.ndarray) -> Tuple[float, float]:
        """
        Calculate Kolmogorov-Smirnov test statistic
        
        Args:
            expected: Baseline distribution
            actual: Current distribution
            
        Returns:
            Tuple of (KS statistic, p-value)
        """
        if len(expected) == 0 or len(actual) == 0:
            return 0.0, 1.0
        
        statistic, pvalue = stats.ks_2samp(expected, actual)
        return float(statistic), float(pvalue)
    
    def add_to_baseline(self, record: Dict[str, any]):
        """
        Add record to baseline data
        
        Args:
            record: Telemetry record dictionary
        """
        if self.baseline_ready:
            return
        
        sku = record.get("sku")
        price = record.get("price")
        stock = record.get("stock")
        
        if price is not None:
            self.baseline_data["price"].append(float(price))
        if stock is not None:
            self.baseline_data["stock"].append(float(stock))
        if sku:
            # Track conversion rate
            views = record.get("views", 0)
            purchases = record.get("purchases", 0)
            if views > 0:
                conversion_rate = purchases / views
                self.sku_conversion_history[sku].append(conversion_rate)
        
        # Check if baseline is ready
        if len(self.baseline_data["price"]) >= self.baseline_window:
            self.baseline_ready = True
    
    def add_to_recent(self, record: Dict[str, any]):
        """
        Add record to recent data window
        
        Args:
            record: Telemetry record dictionary
        """
        sku = record.get("sku")
        price = record.get("price")
        stock = record.get("stock")
        
        if price is not None:
            self.recent_data["price"].append(float(price))
        if stock is not None:
            self.recent_data["stock"].append(float(stock))
        
        # Keep recent window size manageable
        max_recent = self.baseline_window // 2
        if len(self.recent_data["price"]) > max_recent:
            self.recent_data["price"] = self.recent_data["price"][-max_recent:]
        if len(self.recent_data["stock"]) > max_recent:
            self.recent_data["stock"] = self.recent_data["stock"][-max_recent:]
    
    def detect_price_drift(self) -> Dict[str, any]:
        """
        Detect drift in price distribution
        
        Returns:
            Dictionary with drift detection results
        """
        if len(self.baseline_data["price"]) < 10 or len(self.recent_data["price"]) < 5:
            return {
                "drift_detected": False,
                "psi": 0.0,
                "ks_statistic": 0.0,
                "ks_pvalue": 1.0,
                "reason": "Insufficient data"
            }
        
        baseline_prices = np.array(self.baseline_data["price"])
        recent_prices = np.array(self.recent_data["price"])
        
        # Calculate PSI directly on price distributions for robustness
        psi = self.calculate_psi(baseline_prices, recent_prices)
        
        # Calculate KS test
        ks_stat, ks_pvalue = self.calculate_ks_statistic(baseline_prices, recent_prices)
        
        drift_detected = psi > self.psi_threshold or ks_pvalue < self.ks_threshold
        
        return {
            "drift_detected": drift_detected,
            "psi": psi,
            "ks_statistic": ks_stat,
            "ks_pvalue": ks_pvalue,
            "threshold_psi": self.psi_threshold,
            "threshold_ks": self.ks_threshold,
            "baseline_mean": float(np.mean(baseline_prices)),
            "recent_mean": float(np.mean(recent_prices)),
            "baseline_std": float(np.std(baseline_prices)),
            "recent_std": float(np.std(recent_prices))
        }
    
    def detect_stock_drift(self) -> Dict[str, any]:
        """
        Detect drift in stock distribution
        
        Returns:
            Dictionary with drift detection results
        """
        if len(self.baseline_data["stock"]) < 10 or len(self.recent_data["stock"]) < 5:
            return {
                "drift_detected": False,
                "psi": 0.0,
                "ks_statistic": 0.0,
                "ks_pvalue": 1.0,
                "reason": "Insufficient data"
            }
        
        baseline_stock = np.array(self.baseline_data["stock"])
        recent_stock = np.array(self.recent_data["stock"])
        
        # Calculate PSI for stock trends
        psi = self.calculate_psi(baseline_stock, recent_stock)
        
        # Calculate KS test
        ks_stat, ks_pvalue = self.calculate_ks_statistic(baseline_stock, recent_stock)
        
        drift_detected = psi > self.psi_threshold or ks_pvalue < self.ks_threshold
        
        return {
            "drift_detected": drift_detected,
            "psi": psi,
            "ks_statistic": ks_stat,
            "ks_pvalue": ks_pvalue,
            "threshold_psi": self.psi_threshold,
            "threshold_ks": self.ks_threshold,
            "baseline_mean": float(np.mean(baseline_stock)),
            "recent_mean": float(np.mean(recent_stock)),
            "baseline_std": float(np.std(baseline_stock)),
            "recent_std": float(np.std(recent_stock))
        }
    
    def get_sku_conversion_rate(self, sku: str, window: int = 100) -> Optional[float]:
        """
        Get recent conversion rate for a SKU
        
        Args:
            sku: SKU identifier
            window: Number of recent records to consider
            
        Returns:
            Conversion rate (0-1) or None if insufficient data
        """
        if sku not in self.sku_conversion_history:
            return None
        
        history = self.sku_conversion_history[sku]
        if len(history) == 0:
            return None
        
        recent = history[-window:]
        return float(np.mean(recent))
    
    def detect_conversion_drift(self, sku: str, current_conversion: float, window: int = 100) -> Dict[str, any]:
        """
        Detect drift in SKU-level conversion rate
        
        Args:
            sku: SKU identifier
            current_conversion: Current conversion rate
            window: Number of historical records to compare
            
        Returns:
            Dictionary with conversion drift results
        """
        if sku not in self.sku_conversion_history or len(self.sku_conversion_history[sku]) < 10:
            return {
                "drift_detected": False,
                "reason": "Insufficient historical data"
            }
        
        history = self.sku_conversion_history[sku]
        baseline_conversions = np.array(history[-window:-window//2] if len(history) > window else history[:-len(history)//2])
        recent_conversions = np.array(history[-window//2:] if len(history) > window//2 else history[-len(history)//2:])
        
        if len(baseline_conversions) == 0 or len(recent_conversions) == 0:
            return {
                "drift_detected": False,
                "reason": "Insufficient data for comparison"
            }
        
        baseline_mean = np.mean(baseline_conversions)
        recent_mean = np.mean(recent_conversions)
        
        # Calculate statistical significance
        if len(baseline_conversions) > 1 and len(recent_conversions) > 1:
            statistic, pvalue = stats.ttest_ind(baseline_conversions, recent_conversions)
            drift_detected = pvalue < 0.05 and abs(recent_mean - baseline_mean) > 0.02  # 2% change
        else:
            drift_detected = abs(recent_mean - baseline_mean) > 0.05  # 5% change
            pvalue = 1.0
        
        return {
            "drift_detected": drift_detected,
            "baseline_conversion": float(baseline_mean),
            "recent_conversion": float(recent_mean),
            "current_conversion": float(current_conversion),
            "change_pct": float((recent_mean - baseline_mean) / baseline_mean * 100) if baseline_mean > 0 else 0.0,
            "pvalue": float(pvalue) if 'pvalue' in locals() else 1.0
        }
    
    def detect_all_drift(self, record: Optional[Dict[str, any]] = None) -> Dict[str, any]:
        """
        Detect all types of drift
        
        Args:
            record: Optional current record to add before detection
            
        Returns:
            Dictionary with all drift detection results
        """
        if record:
            if not self.baseline_ready:
                self.add_to_baseline(record)
            else:
                self.add_to_recent(record)
        
        results = {
            "baseline_ready": self.baseline_ready,
            "price_drift": self.detect_price_drift(),
            "stock_drift": self.detect_stock_drift()
        }
        
        return results

