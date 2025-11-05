"""Kalman filter for tracking conversion rates with uncertainty estimates"""

import numpy as np
from typing import Dict, Optional, Tuple
from collections import defaultdict


class ConversionKalmanFilter:
    """Kalman filter to track conversion rates with uncertainty estimates"""
    
    def __init__(
        self,
        process_variance: float = 0.01,
        measurement_variance: float = 0.05,
        initial_estimate: float = 0.05,
        initial_uncertainty: float = 1.0
    ):
        """
        Initialize Kalman filter for conversion rate tracking
        
        Args:
            process_variance: Variance of the process (how much conversion can change)
            measurement_variance: Variance of measurements (observation noise)
            initial_estimate: Initial conversion rate estimate
            initial_uncertainty: Initial uncertainty in the estimate
        """
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        
        # Per-SKU state
        self.sku_state: Dict[str, Dict[str, float]] = defaultdict(lambda: {
            "estimate": initial_estimate,
            "uncertainty": initial_uncertainty
        })
    
    def update(self, sku: str, views: int, purchases: int) -> Tuple[float, float]:
        """
        Update Kalman filter with new observation
        
        Args:
            sku: SKU identifier
            views: Number of views
            purchases: Number of purchases
            
        Returns:
            Tuple of (updated_estimate, updated_uncertainty)
        """
        state = self.sku_state[sku]
        current_estimate = state["estimate"]
        current_uncertainty = state["uncertainty"]
        
        # Calculate observed conversion rate
        if views == 0:
            # No views, no update
            return current_estimate, current_uncertainty
        
        observed_conversion = purchases / views
        
        # Prediction step: predict next state
        # Assuming conversion rate doesn't change much (process variance)
        predicted_estimate = current_estimate
        predicted_uncertainty = current_uncertainty + self.process_variance
        
        # Measurement step: incorporate observation
        # Measurement uncertainty depends on sample size (more views = more confident)
        # Use binomial variance: p(1-p)/n, but scale by measurement_variance
        if views > 0:
            # Measurement uncertainty decreases with more views
            effective_measurement_variance = self.measurement_variance / np.sqrt(views)
        else:
            effective_measurement_variance = self.measurement_variance
        
        # Kalman gain
        kalman_gain = predicted_uncertainty / (predicted_uncertainty + effective_measurement_variance)
        
        # Update estimate
        updated_estimate = predicted_estimate + kalman_gain * (observed_conversion - predicted_estimate)
        
        # Update uncertainty
        updated_uncertainty = (1 - kalman_gain) * predicted_uncertainty
        
        # Ensure estimate stays in valid range [0, 1]
        updated_estimate = np.clip(updated_estimate, 0.0, 1.0)
        
        # Update state
        state["estimate"] = updated_estimate
        state["uncertainty"] = updated_uncertainty
        
        return updated_estimate, updated_uncertainty
    
    def predict(self, sku: str) -> Tuple[float, float]:
        """
        Get current estimate and uncertainty for a SKU
        
        Args:
            sku: SKU identifier
            
        Returns:
            Tuple of (estimate, uncertainty)
        """
        state = self.sku_state[sku]
        return state["estimate"], state["uncertainty"]
    
    def detect_deviation(
        self,
        sku: str,
        views: int,
        purchases: int,
        threshold_sigma: float = 2.0
    ) -> Dict[str, any]:
        """
        Detect if current observation deviates significantly from expected conversion
        
        Args:
            sku: SKU identifier
            views: Number of views
            purchases: Number of purchases
            threshold_sigma: Number of standard deviations for alert threshold
            
        Returns:
            Dictionary with deviation detection results
        """
        if views == 0:
            return {
                "deviation_detected": False,
                "reason": "No views"
            }
        
        estimate, uncertainty = self.predict(sku)
        observed_conversion = purchases / views
        
        # Calculate z-score (how many standard deviations away)
        # Use uncertainty as standard deviation
        std_dev = np.sqrt(uncertainty) if uncertainty > 0 else 0.1
        z_score = abs(observed_conversion - estimate) / std_dev if std_dev > 0 else 0.0
        
        deviation_detected = z_score > threshold_sigma
        
        # Update filter with observation
        updated_estimate, updated_uncertainty = self.update(sku, views, purchases)
        
        result = {
            "deviation_detected": deviation_detected,
            "expected_conversion": float(estimate),
            "observed_conversion": float(observed_conversion),
            "updated_conversion": float(updated_estimate),
            "z_score": float(z_score),
            "threshold_sigma": threshold_sigma,
            "uncertainty": float(uncertainty),
            "updated_uncertainty": float(updated_uncertainty),
            "deviation_pct": float((observed_conversion - estimate) / estimate * 100) if estimate > 0 else 0.0
        }
        
        return result
    
    def get_all_estimates(self) -> Dict[str, Dict[str, float]]:
        """
        Get conversion rate estimates for all SKUs
        
        Returns:
            Dictionary mapping SKU to {estimate, uncertainty}
        """
        return {
            sku: {
                "estimate": state["estimate"],
                "uncertainty": state["uncertainty"]
            }
            for sku, state in self.sku_state.items()
        }
    
    def reset_sku(self, sku: str, initial_estimate: float = 0.05, initial_uncertainty: float = 1.0):
        """
        Reset Kalman filter state for a specific SKU
        
        Args:
            sku: SKU identifier
            initial_estimate: Initial conversion rate estimate
            initial_uncertainty: Initial uncertainty
        """
        self.sku_state[sku] = {
            "estimate": initial_estimate,
            "uncertainty": initial_uncertainty
        }

