"""Violation tracking and CSV logging"""

import csv
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class ViolationLogger:
    """Logs data contract violations to CSV"""
    
    def __init__(self, violations_file: str = "violations.csv"):
        """
        Initialize violation logger
        
        Args:
            violations_file: Path to CSV file for storing violations
        """
        self.violations_file = violations_file
        self.violations_path = Path(violations_file)
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create violations file with headers if it doesn't exist"""
        if not self.violations_path.exists():
            self.violations_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.violations_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "timestamp",
                    "sku",
                    "violation_type",
                    "reason",
                    "severity"
                ])
                writer.writeheader()
    
    def log_violation(
        self,
        violation_type: str,
        reason: str,
        sku: Optional[str] = None,
        severity: str = "medium"
    ):
        """
        Log a single violation to CSV
        
        Args:
            violation_type: Type of violation
            reason: Human-readable reason
            sku: SKU identifier (optional)
            severity: Severity level (low, medium, high, critical)
        """
        violation = {
            "timestamp": datetime.now().isoformat(),
            "sku": sku or "",
            "violation_type": violation_type,
            "reason": reason,
            "severity": severity
        }
        
        with open(self.violations_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "timestamp",
                "sku",
                "violation_type",
                "reason",
                "severity"
            ])
            writer.writerow(violation)
    
    def log_violations(self, violations: List[Dict[str, Any]]):
        """
        Log multiple violations to CSV
        
        Args:
            violations: List of violation dictionaries
        """
        if not violations:
            return
        
        with open(self.violations_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "timestamp",
                "sku",
                "violation_type",
                "reason",
                "severity"
            ])
            
            for violation in violations:
                # Ensure all required fields are present
                violation_row = {
                    "timestamp": violation.get("timestamp", datetime.now().isoformat()),
                    "sku": violation.get("sku", ""),
                    "violation_type": violation.get("violation_type", "unknown"),
                    "reason": violation.get("reason", ""),
                    "severity": violation.get("severity", "medium")
                }
                writer.writerow(violation_row)
    
    def get_violations(
        self,
        sku: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Read violations from CSV with optional filtering
        
        Args:
            sku: Filter by SKU (optional)
            severity: Filter by severity (optional)
            limit: Maximum number of violations to return
            
        Returns:
            List of violation dictionaries
        """
        if not self.violations_path.exists():
            return []
        
        violations = []
        with open(self.violations_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if sku and row.get("sku") != sku:
                    continue
                if severity and row.get("severity") != severity:
                    continue
                violations.append(row)
                if len(violations) >= limit:
                    break
        
        return violations
    
    def get_violation_stats(self) -> Dict[str, Any]:
        """
        Get statistics about violations
        
        Returns:
            Dictionary with violation statistics
        """
        if not self.violations_path.exists():
            return {
                "total_violations": 0,
                "by_type": {},
                "by_severity": {},
                "by_sku": {}
            }
        
        stats = {
            "total_violations": 0,
            "by_type": {},
            "by_severity": {},
            "by_sku": {}
        }
        
        with open(self.violations_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats["total_violations"] += 1
                
                # Count by type
                vtype = row.get("violation_type", "unknown")
                stats["by_type"][vtype] = stats["by_type"].get(vtype, 0) + 1
                
                # Count by severity
                severity = row.get("severity", "medium")
                stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1
                
                # Count by SKU
                sku = row.get("sku", "")
                if sku:
                    stats["by_sku"][sku] = stats["by_sku"].get(sku, 0) + 1
        
        return stats

