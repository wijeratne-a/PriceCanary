"""FastAPI application main entry point"""

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.api.routes import router, initialize_anomaly_detector
from src.monitoring.metrics import start_metrics_server


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    print("Initializing PriceCanary...")
    initialize_anomaly_detector()
    
    # Start metrics server in background
    try:
        start_metrics_server(port=9090)
    except Exception as e:
        print(f"Warning: Could not start metrics server: {e}")
    
    yield
    
    # Shutdown
    print("Shutting down PriceCanary...")


app = FastAPI(
    title="PriceCanary API",
    description="Real-Time E-commerce Guardrails - Detect and triage drift and anomalies",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1", tags=["api"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "PriceCanary",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "ingest": "/api/v1/ingest",
            "alerts": "/api/v1/alerts",
            "metrics": "/api/v1/metrics",
            "health": "/api/v1/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

