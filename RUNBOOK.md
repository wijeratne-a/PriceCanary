# PriceCanary Runbook

## Service Level Objectives (SLOs)

### Alert Latency
- **Target**: Median alert latency < 10 seconds
- **Measurement**: Time from event ingestion to alert creation
- **Current**: Monitored via `pricecanary_alert_latency_seconds` metric

### Validation Pass Rate
- **Target**: 95% validation pass rate
- **Measurement**: Ratio of valid records to total records ingested
- **Current**: Monitored via `pricecanary_validation_pass_rate` gauge

### False Positive Rate
- **Target**: < 10% false positive rate
- **Measurement**: Ratio of false alerts to total alerts
- **Current**: Requires manual review and feedback loop

### System Availability
- **Target**: 99.9% uptime
- **Measurement**: API health check endpoint availability
- **Current**: Monitored via `/api/v1/health` endpoint

## Service Level Agreements (SLAs)

### Alert Response Times
- **Critical**: Respond within 5 minutes
- **High**: Respond within 15 minutes
- **Medium**: Respond within 1 hour
- **Low**: Respond within 4 hours

### Alert Resolution Times
- **Critical**: Resolve within 1 hour
- **High**: Resolve within 4 hours
- **Medium**: Resolve within 24 hours
- **Low**: Resolve within 72 hours

## Alert Response Procedures

### Critical Alerts

1. **Immediate Actions**:
   - Acknowledge alert in dashboard
   - Review alert metadata and last good state
   - Check system logs for errors
   - Verify data source integrity

2. **Investigation**:
   - Check recent ingestion patterns
   - Review drift scores and anomaly detection results
   - Examine related SKUs for similar issues
   - Review suggested fixes

3. **Resolution**:
   - Apply fix (e.g., freeze price, delist SKU, fix data pipeline)
   - Verify fix resolves the issue
   - Mark alert as resolved
   - Document root cause

### High Priority Alerts

1. **Actions**:
   - Acknowledge within 15 minutes
   - Review within 1 hour
   - Investigate root cause
   - Apply fix and verify

2. **Common Issues**:
   - Price jumps: Check for unit conversion errors, data entry mistakes
   - Stock anomalies: Check inventory system, data pipeline
   - Conversion drift: Review checkout process, pricing, inventory availability

### Medium/Low Priority Alerts

1. **Actions**:
   - Review during regular maintenance window
   - Batch process similar alerts
   - Update monitoring thresholds if needed

## Monitoring and Dashboards

### Key Metrics to Monitor

1. **Throughput**: `pricecanary_records_per_second`
   - Normal: 1-100 records/second
   - Alert if: < 0.1 or > 1000 records/second

2. **Latency**: `pricecanary_ingest_latency_seconds`
   - Normal: p95 < 1 second
   - Alert if: p95 > 5 seconds

3. **Validation Pass Rate**: `pricecanary_validation_pass_rate`
   - Normal: > 0.95
   - Alert if: < 0.90

4. **Drift Scores**: `pricecanary_drift_score_price`, `pricecanary_drift_score_stock`
   - Normal: PSI < 0.2
   - Alert if: PSI > 0.5

5. **Active Alerts**: `pricecanary_active_alerts`
   - Normal: < 10 critical, < 50 total
   - Alert if: > 20 critical, > 200 total

### Dashboard Access

- **Streamlit Dashboard**: http://localhost:8501
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **API**: http://localhost:8000

## Troubleshooting

### High Alert Latency

1. Check API server logs
2. Review Prometheus metrics for bottlenecks
3. Check database/CSV file write performance
4. Verify anomaly detector training completed

### Low Validation Pass Rate

1. Review violation logs in `violations.csv`
2. Check data source schema changes
3. Review validation thresholds
4. Check for data pipeline issues

### False Positives

1. Review alert patterns
2. Adjust model thresholds (PSI, contamination, z-score)
3. Retrain anomaly detector with updated baseline
4. Update business logic rules

### System Errors

1. Check API health endpoint
2. Review container logs: `docker-compose logs api`
3. Verify all services are running: `docker-compose ps`
4. Check disk space and memory usage

## Common Fixes

### Price Jump Alerts
- **Fix**: Freeze price at last known good value
- **Command**: Update price in source system
- **Verification**: Monitor price drift after fix

### Negative Stock Alerts
- **Fix**: Set stock to 0 or correct value
- **Command**: Update inventory system
- **Verification**: Check stock validation passes

### Unit Error Alerts
- **Fix**: Normalize price units (dollars/cents)
- **Command**: Update data pipeline configuration
- **Verification**: Check price normalization working

### Stale Timestamp Alerts
- **Fix**: Check data feed freshness, timezone settings
- **Command**: Verify system clock synchronization
- **Verification**: Check timestamp validation

### Bot Spike Alerts
- **Fix**: Review traffic sources, implement rate limiting
- **Command**: Check referrer patterns
- **Verification**: Monitor view/cart ratios

## Maintenance

### Daily
- Review critical and high priority alerts
- Check system health metrics
- Review violation logs

### Weekly
- Review false positive rate
- Update model thresholds if needed
- Clean up old alerts (> 7 days)

### Monthly
- Retrain anomaly detector with updated baseline
- Review and update SLOs/SLAs
- Performance optimization

## Escalation

### Level 1: On-Call Engineer
- Respond to critical alerts
- Investigate and resolve issues
- Update documentation

### Level 2: Team Lead
- Review recurring issues
- Approve threshold changes
- Coordinate with data sources

### Level 3: Engineering Manager
- Review SLO/SLA compliance
- Approve system changes
- Coordinate with stakeholders

## Contact Information

- **On-Call**: Check team rotation schedule
- **Slack**: #pricecanary-alerts
- **Email**: pricecanary-team@company.com

