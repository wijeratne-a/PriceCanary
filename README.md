# PriceCanary – Real-Time E-commerce Guardrails

**Detect and triage drift and anomalies in live e-commerce data streams.**

PriceCanary is an end-to-end machine learning and monitoring system designed to simulate and safeguard an e-commerce storefront's operational data. It ingests live-like telemetry — encompassing pricing, stock, and behavior signals — to detect anomalies, enforce data contracts, and surface explainable alerts via a triage dashboard.

## Overview

Shop monitoring system for price, inventory, and behavioral anomalies. Ingests real-time data, enforces contracts, and triggers explainable alerts. Demonstrates production ML: ingestion, validation, feature creation, model serving, dashboard triage.

## Features

### Core Components

1. **Synthetic Store Stream**: Generates realistic e-commerce telemetry with configurable fault injection
2. **Data Contracts & Quality Checks**: Validates data with Pydantic/Pandera schemas
3. **Online Drift & Anomaly Detection**: Uses PSI/KS for drift, IsolationForest for anomalies
4. **Serving & Monitoring**: FastAPI backend with Prometheus metrics
5. **Triage UI**: Streamlit dashboard with live alerts and visualizations

### Key Capabilities

- **Fault Detection**: Large price jumps, unit errors, negative stock, bot spikes, stale feeds
- **Drift Detection**: PSI/KS metrics for price velocity, stock trends, conversion rates
- **Anomaly Detection**: IsolationForest with feature engineering
- **Alert Management**: Severity levels, suggested fixes, SLA timers
- **Monitoring**: Prometheus and Grafana integration

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Make (optional, for convenience commands)

### One-Command Startup

```bash
make up
```

This will:
- Build Docker images
- Start all services (API, dashboard, Prometheus, Grafana)
- Initialize models with baseline data

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Start API server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Start dashboard (in another terminal)
streamlit run src/dashboard/app.py

# Start with Docker Compose
docker-compose up --build
```

## Architecture

```
┌─────────────────┐
│  Data Sources   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI /ingest│──► Validation ──► Drift Detection
│                 │                   └─► Anomaly Detection
│                 │                   └─► Alert Manager
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Streamlit UI   │◄─── Alerts API
│  Prometheus     │◄─── Metrics API
│  Grafana        │
└─────────────────┘
```

## API Endpoints

### Ingest Telemetry
```bash
POST /api/v1/ingest
Content-Type: application/json

{
  "timestamp": "2024-01-01T12:00:00",
  "sku": "SKU-001",
  "price": 99.99,
  "stock": 100,
  "views": 50,
  "add_to_cart": 10,
  "purchases": 5,
  "referrer": "organic"
}
```

### Get Alerts
```bash
GET /api/v1/alerts?severity=critical&limit=100
```

### Metrics (Prometheus)
```bash
GET /api/v1/metrics
```

### Health Check
```bash
GET /api/v1/health
```

## Services

- **API**: http://localhost:8000
- **Dashboard**: http://localhost:8501
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## Configuration

### Environment Variables

- `PYTHONUNBUFFERED=1`: Enable real-time logging
- Custom thresholds via code configuration

### Data Contracts

- Price validation: > 0, normalized dollars
- Stock validation: >= 0
- Funnel validation: purchases <= add_to_cart <= views
- Timestamp validation: within 24 hours

## Testing

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_contracts.py

# Run with coverage
pytest --cov=src tests/
```

## Success Metrics

- Median alert latency < 10s
- False positive rate < 10%
- Full stack up in < 5 minutes
- 95% validation pass rate

## Documentation

- **RUNBOOK.md**: SLOs, SLAs, alert response procedures
- **MODEL_CARD.md**: Model metrics, features, test coverage
- **API Docs**: http://localhost:8000/docs (Swagger UI)

## Development

### Project Structure

```
PriceCanary-main/
├── src/
│   ├── data/          # Data contracts, validation, generation
│   ├── models/        # ML models (drift, anomaly, kalman)
│   ├── api/           # FastAPI application
│   ├── dashboard/     # Streamlit dashboard
│   └── monitoring/    # Prometheus metrics
├── tests/             # Test suite
├── docker/            # Dockerfiles and configs
└── docker-compose.yml # Service orchestration
```

### Adding New Features

1. Implement feature in appropriate module
2. Add tests in `tests/`
3. Update API endpoints if needed
4. Update dashboard if needed
5. Update documentation

## Troubleshooting

### Services won't start
```bash
docker-compose logs
docker-compose down
docker-compose up --build
```

### Tests failing
```bash
pip install -r requirements.txt
pytest -v
```

### High false positive rate
- Adjust anomaly detector contamination parameter
- Retrain with updated baseline data
- Review drift detection thresholds

See **RUNBOOK.md** for detailed troubleshooting.

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## Contact

For questions or issues, please open a GitHub issue.
