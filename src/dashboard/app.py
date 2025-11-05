"""Streamlit dashboard for PriceCanary"""

import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import plotly.graph_objects as go
from typing import Dict, List, Any


# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
REFRESH_INTERVAL = 5  # seconds


@st.cache_data(ttl=60)
def fetch_alerts(severity: str = None, alert_type: str = None, resolved: bool = False):
    """Fetch alerts from API"""
    try:
        params = {"limit": 1000}
        if severity:
            params["severity"] = severity
        if alert_type:
            params["alert_type"] = alert_type
        if resolved is not None:
            params["resolved"] = resolved
        
        response = requests.get(f"{API_BASE_URL}/alerts", params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("alerts", []), data.get("stats", {})
        return [], {}
    except Exception as e:
        st.error(f"Error fetching alerts: {e}")
        return [], {}


def fetch_health():
    """Fetch health status"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        return None


def send_telemetry(record: Dict[str, Any]):
    """Send telemetry record to API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/ingest",
            json=record,
            timeout=5
        )
        return response.json()
    except Exception as e:
        st.error(f"Error sending telemetry: {e}")
        return None


def create_sparkline(data: List[float], title: str, color: str = "blue") -> go.Figure:
    """Create a sparkline chart"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(data))),
        y=data,
        mode='lines',
        line=dict(color=color, width=2),
        showlegend=False
    ))
    fig.update_layout(
        title=title,
        height=100,
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis=dict(showticklabels=False),
        yaxis=dict(showticklabels=False)
    )
    return fig


def main():
    st.set_page_config(
        page_title="PriceCanary Dashboard",
        page_icon="🐦",
        layout="wide"
    )
    
    st.title("🐦 PriceCanary - Real-Time E-commerce Guardrails")
    st.markdown("Detect and triage drift and anomalies in live e-commerce data streams")
    
    # Sidebar
    with st.sidebar:
        st.header("Controls")
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        
        if auto_refresh:
            refresh_interval = st.slider("Refresh interval (seconds)", 1, 60, REFRESH_INTERVAL)
            time.sleep(refresh_interval)
            st.rerun()
        
        # Filter options
        st.subheader("Filters")
        filter_severity = st.selectbox(
            "Severity",
            ["All", "critical", "high", "medium", "low"],
            index=0
        )
        
        filter_alert_type = st.selectbox(
            "Alert Type",
            ["All", "contract_violation", "drift", "anomaly", "conversion_deviation"],
            index=0
        )
        
        show_resolved = st.checkbox("Show resolved alerts", value=False)
        
        # Fault simulation
        st.subheader("Fault Simulation")
        if st.button("Inject Price Jump"):
            record = {
                "timestamp": datetime.now().isoformat(),
                "sku": "SKU-0001",
                "price": 19000.0,  # Large jump
                "stock": 100,
                "views": 50,
                "add_to_cart": 5,
                "purchases": 1,
                "referrer": "organic"
            }
            result = send_telemetry(record)
            if result:
                st.success("Price jump injected!")
        
        if st.button("Inject Negative Stock"):
            record = {
                "timestamp": datetime.now().isoformat(),
                "sku": "SKU-0002",
                "price": 50.0,
                "stock": -10,  # Negative stock
                "views": 30,
                "add_to_cart": 3,
                "purchases": 0,
                "referrer": "organic"
            }
            result = send_telemetry(record)
            if result:
                st.success("Negative stock injected!")
        
        if st.button("Inject Bot Spike"):
            record = {
                "timestamp": datetime.now().isoformat(),
                "sku": "SKU-0003",
                "price": 75.0,
                "stock": 200,
                "views": 10000,  # Bot spike
                "add_to_cart": 5000,
                "purchases": 100,
                "referrer": "unknown"
            }
            result = send_telemetry(record)
            if result:
                st.success("Bot spike injected!")
        
        # Health status
        health = fetch_health()
        if health:
            st.subheader("System Health")
            st.success(" Operational" if health.get("status") == "healthy" else "Unhealthy")
            st.text(f"Baseline: {'Ready' if health.get('baseline_ready') else 'Not Ready'}")
            st.text(f"Anomaly Detector: {'Trained' if health.get('anomaly_detector_trained') else 'Not Trained'}")
    
    # Main content
    # Fetch alerts
    severity_filter = None if filter_severity == "All" else filter_severity
    alert_type_filter = None if filter_alert_type == "All" else filter_alert_type
    
    alerts, stats = fetch_alerts(
        severity=severity_filter,
        alert_type=alert_type_filter,
        resolved=show_resolved
    )
    
    # Stats overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Alerts", stats.get("total", 0))
    
    with col2:
        st.metric("Unresolved", stats.get("unresolved", 0))
    
    with col3:
        st.metric("Unacknowledged", stats.get("unacknowledged", 0))
    
    with col4:
        critical_count = stats.get("by_severity", {}).get("critical", 0)
        st.metric("Critical", critical_count, delta=None)
    
    # Alerts table
    st.subheader("Active Alerts")
    
    if not alerts:
        st.info("No alerts found")
    else:
        # Convert to DataFrame
        df = pd.DataFrame(alerts)
        
        # Add SLA timer (time since alert creation)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["age_minutes"] = (datetime.now() - df["timestamp"]).dt.total_seconds() / 60
        
        # Display key columns
        display_cols = ["alert_id", "severity", "alert_type", "message", "sku", "age_minutes"]
        display_df = df[display_cols].copy() if all(col in df.columns for col in display_cols) else df
        
        # Color code by severity
        def color_severity(val):
            if val == "critical":
                return "background-color: #ff6b6b"
            elif val == "high":
                return "background-color: #ffa500"
            elif val == "medium":
                return "background-color: #ffd93d"
            else:
                return "background-color: #6bcf7f"
        
        if "severity" in display_df.columns:
            styled_df = display_df.style.applymap(color_severity, subset=["severity"])
            st.dataframe(styled_df, use_container_width=True, height=400)
        else:
            st.dataframe(display_df, use_container_width=True, height=400)
        
        # Alert details
        if len(alerts) > 0:
            st.subheader("Alert Details")
            selected_alert_id = st.selectbox("Select alert to view details", [a["alert_id"] for a in alerts])
            
            if selected_alert_id:
                alert = next((a for a in alerts if a["alert_id"] == selected_alert_id), None)
                if alert:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.json(alert.get("metadata", {}))
                        st.text("Last Good State:")
                        st.json(alert.get("last_good_state", {}))
                    
                    with col2:
                        st.text(f"Suggested Fix:")
                        st.info(alert.get("suggested_fix", "No suggestion available"))
                        
                        # Actions
                        if st.button(f"Acknowledge {selected_alert_id}"):
                            try:
                                response = requests.post(
                                    f"{API_BASE_URL}/alerts/{selected_alert_id}/acknowledge",
                                    timeout=5
                                )
                                if response.status_code == 200:
                                    st.success("Alert acknowledged!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                        
                        if st.button(f"Resolve {selected_alert_id}"):
                            try:
                                response = requests.post(
                                    f"{API_BASE_URL}/alerts/{selected_alert_id}/resolve",
                                    timeout=5
                                )
                                if response.status_code == 200:
                                    st.success("Alert resolved!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
    
    # SKU sparklines section
    st.subheader("SKU Trends")
    
    # Get unique SKUs from alerts
    skus = list(set([a.get("sku") for a in alerts if a.get("sku")]))
    
    if skus:
        selected_sku = st.selectbox("Select SKU", skus[:20])  # Limit to first 20
        
        if selected_sku:
            # Filter alerts for this SKU
            sku_alerts = [a for a in alerts if a.get("sku") == selected_sku]
            
            if sku_alerts:
                # Create mock sparklines (in production, would fetch historical data)
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Mock price data
                    price_data = [50 + i * 2 + (i % 10) * 5 for i in range(20)]
                    st.plotly_chart(create_sparkline(price_data, "Price", "blue"), use_container_width=True)
                
                with col2:
                    # Mock stock data
                    stock_data = [100 - i * 3 for i in range(20)]
                    st.plotly_chart(create_sparkline(stock_data, "Stock", "green"), use_container_width=True)
                
                with col3:
                    # Mock conversion data
                    conversion_data = [0.05 + (i % 5) * 0.01 for i in range(20)]
                    st.plotly_chart(create_sparkline(conversion_data, "Conversion", "orange"), use_container_width=True)
                
                # Trend comparison
                st.subheader(f"Trend Analysis for {selected_sku}")
                
                # Create comparison chart
                fig = go.Figure()
                
                # Before/after data (mock)
                before_data = [50 + i * 0.5 for i in range(10)]
                after_data = [60 + i * 2 for i in range(10)]
                
                fig.add_trace(go.Scatter(
                    x=list(range(10)),
                    y=before_data,
                    mode='lines',
                    name='Before',
                    line=dict(color='green')
                ))
                
                fig.add_trace(go.Scatter(
                    x=list(range(10, 20)),
                    y=after_data,
                    mode='lines',
                    name='After',
                    line=dict(color='red')
                ))
                
                fig.update_layout(
                    title="Price Trend: Before vs After Drift",
                    xaxis_title="Time",
                    yaxis_title="Price ($)",
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
    
    # Footer
    st.markdown("---")
    st.markdown("**PriceCanary v0.1.0** | Real-Time E-commerce Guardrails")


if __name__ == "__main__":
    main()

