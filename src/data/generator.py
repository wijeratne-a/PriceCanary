"""Synthetic e-commerce data stream generator with fault injection"""

import random
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum


class FaultType(str, Enum):
    """Types of faults to inject"""
    NONE = "none"
    PRICE_JUMP = "price_jump"  # Large price jump (e.g., 19 to 1900)
    UNIT_ERROR_CENTS = "unit_error_cents"  # Price in cents when should be dollars
    UNIT_ERROR_DOLLARS = "unit_error_dollars"  # Price in dollars when should be cents
    NEGATIVE_STOCK = "negative_stock"
    BOT_SPIKE = "bot_spike"  # Spikes in views/carts
    STALE_TIMESTAMP = "stale_timestamp"
    TIMEZONE_SHIFT = "timezone_shift"


class SyntheticStoreGenerator:
    """Generates synthetic e-commerce telemetry with configurable fault injection"""
    
    def __init__(
        self,
        sku_list: Optional[List[str]] = None,
        base_price_range: tuple = (10.0, 500.0),
        base_stock_range: tuple = (0, 1000),
        referrers: Optional[List[str]] = None,
        fault_probability: float = 0.05
    ):
        """
        Initialize synthetic data generator
        
        Args:
            sku_list: List of SKU identifiers (generated if None)
            base_price_range: (min, max) price range in dollars
            base_stock_range: (min, max) stock range
            referrers: List of referrer sources (default list if None)
            fault_probability: Probability of injecting a fault (0.0 to 1.0)
        """
        self.sku_list = sku_list or [f"SKU-{i:04d}" for i in range(1, 101)]
        self.base_price_range = base_price_range
        self.base_stock_range = base_stock_range
        self.referrers = referrers or [
            "organic", "google", "facebook", "email", "direct", "affiliate", "unknown"
        ]
        self.fault_probability = fault_probability
        
        # Track state per SKU
        self.sku_state: Dict[str, Dict[str, Any]] = {}
        for sku in self.sku_list:
            self.sku_state[sku] = {
                "price": random.uniform(*base_price_range),
                "stock": random.randint(*base_stock_range),
                "conversion_rate": random.uniform(0.01, 0.10),  # 1-10% conversion
                "views_per_hour": random.randint(10, 1000)
            }
        
        # Track recent views/carts for bot spike detection
        self.recent_activity: Dict[str, List[datetime]] = {}
    
    def generate_record(
        self,
        timestamp: Optional[datetime] = None,
        sku: Optional[str] = None,
        inject_fault: Optional[FaultType] = None
    ) -> Dict[str, Any]:
        """
        Generate a single telemetry record
        
        Args:
            timestamp: Event timestamp (current time if None)
            sku: SKU identifier (random if None)
            inject_fault: Specific fault to inject (None = random based on probability)
            
        Returns:
            Dictionary with telemetry data
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        if sku is None:
            sku = random.choice(self.sku_list)
        
        state = self.sku_state[sku]
        
        # Determine if we should inject a fault
        fault = inject_fault
        if fault is None and random.random() < self.fault_probability:
            fault = random.choice(list(FaultType)[1:])  # Exclude NONE
        
        # Generate base values
        price = state["price"]
        stock = state["stock"]
        views = max(0, int(np.random.poisson(state["views_per_hour"] / 3600)))
        
        # Apply fault injection
        if fault == FaultType.PRICE_JUMP:
            # Large price jump (e.g., 19 to 1900)
            price = state["price"] * random.uniform(50, 200)
        
        elif fault == FaultType.UNIT_ERROR_CENTS:
            # Price reported in cents (multiply by 100)
            price = state["price"] * 100
        
        elif fault == FaultType.UNIT_ERROR_DOLLARS:
            # Price reported in dollars when should be cents (divide by 100)
            price = state["price"] / 100
        
        elif fault == FaultType.NEGATIVE_STOCK:
            # Negative stock value
            stock = random.randint(-100, -1)
        
        elif fault == FaultType.BOT_SPIKE:
            # Bot spike: 10-100x normal views/carts
            views = views * random.randint(10, 100)
        
        elif fault == FaultType.STALE_TIMESTAMP:
            # Timestamp from 25+ hours ago
            timestamp = timestamp - timedelta(hours=random.randint(25, 72))
        
        elif fault == FaultType.TIMEZONE_SHIFT:
            # Timestamp shifted (future time)
            timestamp = timestamp + timedelta(hours=random.randint(2, 12))
        
        # Calculate add_to_cart and purchases based on conversion funnel
        # Typical funnel: views -> add_to_cart (10-30%) -> purchases (20-50% of carts)
        cart_rate = random.uniform(0.10, 0.30)
        purchase_rate = random.uniform(0.20, 0.50)
        
        add_to_cart = max(0, int(views * cart_rate))
        purchases = max(0, int(add_to_cart * purchase_rate))
        
        # Ensure purchases don't exceed stock
        purchases = min(purchases, stock)
        
        # Random referrer
        referrer = random.choice(self.referrers)
        
        # Update state (with small random walk for price/stock)
        if fault != FaultType.PRICE_JUMP and fault != FaultType.UNIT_ERROR_CENTS and fault != FaultType.UNIT_ERROR_DOLLARS:
            # Normal price drift: ±2%
            price_change = random.uniform(-0.02, 0.02)
            state["price"] = max(self.base_price_range[0], state["price"] * (1 + price_change))
        
        if fault != FaultType.NEGATIVE_STOCK:
            # Stock changes: sales reduce stock, occasional restocking
            state["stock"] = max(0, state["stock"] - purchases)
            if random.random() < 0.1:  # 10% chance of restocking
                state["stock"] += random.randint(10, 100)
            state["stock"] = min(state["stock"], self.base_stock_range[1])
        
        record = {
            "timestamp": timestamp.isoformat(),
            "sku": sku,
            "price": round(price, 2),
            "stock": stock,
            "views": views,
            "add_to_cart": add_to_cart,
            "purchases": purchases,
            "referrer": referrer
        }
        
        return record
    
    def generate_batch(
        self,
        n_records: int,
        start_time: Optional[datetime] = None,
        time_interval_seconds: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Generate a batch of telemetry records
        
        Args:
            n_records: Number of records to generate
            start_time: Starting timestamp (current time if None)
            time_interval_seconds: Seconds between records
            
        Returns:
            List of telemetry record dictionaries
        """
        if start_time is None:
            start_time = datetime.now()
        
        records = []
        current_time = start_time
        
        for i in range(n_records):
            record = self.generate_record(timestamp=current_time)
            records.append(record)
            current_time += timedelta(seconds=time_interval_seconds)
        
        return records
    
    def generate_stream(
        self,
        duration_seconds: int = 3600,
        records_per_second: float = 1.0
    ):
        """
        Generator that yields telemetry records continuously
        
        Args:
            duration_seconds: How long to generate records
            records_per_second: Average records per second
            
        Yields:
            Telemetry record dictionaries
        """
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration_seconds)
        current_time = start_time
        
        interval = 1.0 / records_per_second
        
        while current_time < end_time:
            yield self.generate_record(timestamp=current_time)
            current_time += timedelta(seconds=interval)
    
    def reset_state(self):
        """Reset all SKU states to initial values"""
        for sku in self.sku_list:
            self.sku_state[sku] = {
                "price": random.uniform(*self.base_price_range),
                "stock": random.randint(*self.base_stock_range),
                "conversion_rate": random.uniform(0.01, 0.10),
                "views_per_hour": random.randint(10, 1000)
            }

