#!/usr/bin/env python3
"""
STGen Web UI Backend
FastAPI server for managing STGen experiments
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import psutil

# Add parent directory to path for STGen imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from stgen_controller import ExperimentController, ExperimentStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="STGen Web UI API",
    description="REST API for STGen IoT Protocol Testing Framework",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global experiment controller
controller = ExperimentController()

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, exp_id: str):
        await websocket.accept()
        self.active_connections[exp_id].append(websocket)
        logger.info(f"WebSocket connected for experiment {exp_id}")

    def disconnect(self, websocket: WebSocket, exp_id: str):
        self.active_connections[exp_id].remove(websocket)
        logger.info(f"WebSocket disconnected for experiment {exp_id}")

    async def broadcast(self, exp_id: str, message: dict):
        for connection in self.active_connections[exp_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to websocket: {e}")

manager = ConnectionManager()

# Pydantic models
class ExperimentConfig(BaseModel):
    name: str
    protocol: str
    mode: str = "active"
    server_ip: str = "127.0.0.1"
    server_port: int
    num_clients: int = 10
    duration: int = 30
    sensors: List[str] = ["temp", "humidity", "motion"]
    network_profile: str = "perfect"
    deployment_mode: str = "single"  # single or distributed

class ExperimentResponse(BaseModel):
    id: str
    name: str
    status: str
    config: dict
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metrics: Optional[dict] = None

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    """API health check"""
    return {
        "status": "running",
        "service": "STGen Web UI API",
        "version": "1.0.0",
        "stgen_available": True
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    return {
        "api": "healthy",
        "experiments": {
            "total": len(controller.experiments),
            "running": len([e for e in controller.experiments.values() if e.status == ExperimentStatus.RUNNING]),
            "completed": len([e for e in controller.experiments.values() if e.status == ExperimentStatus.COMPLETED])
        },
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    }

@app.get("/api/protocols")
async def get_protocols():
    """Get available protocols"""
    return {
        "protocols": [
            {"id": "mqtt", "name": "MQTT", "port": 1883, "description": "Message Queue Telemetry Transport"},
            {"id": "coap", "name": "CoAP", "port": 5683, "description": "Constrained Application Protocol"},
            {"id": "srtp", "name": "SRTP", "port": 5004, "description": "Secure Real-time Transport Protocol"},
            {"id": "my_udp", "name": "Custom UDP", "port": 6000, "description": "Custom UDP-based protocol"}
        ]
    }

@app.get("/api/sensors")
async def get_sensors():
    """Get available sensor types"""
    return {
        "sensors": [
            {"id": "temp", "name": "Temperature", "rate_hz": 1.0},
            {"id": "humidity", "name": "Humidity", "rate_hz": 0.5},
            {"id": "motion", "name": "Motion", "rate_hz": 2.0},
            {"id": "light", "name": "Light", "rate_hz": 0.5},
            {"id": "gps", "name": "GPS", "rate_hz": 0.2},
            {"id": "camera", "name": "Camera", "rate_hz": 15.0},
            {"id": "soil_moisture", "name": "Soil Moisture", "rate_hz": 0.017}
        ]
    }

@app.get("/api/network-profiles")
async def get_network_profiles():
    """Get available network profiles"""
    return {
        "profiles": [
            {"id": "perfect", "name": "Perfect", "latency": 0, "loss": 0, "bandwidth": "unlimited"},
            {"id": "wifi", "name": "WiFi", "latency": 10, "loss": 0.1, "bandwidth": "54 Mbps"},
            {"id": "4g", "name": "4G/LTE", "latency": 50, "loss": 1, "bandwidth": "10 Mbps"},
            {"id": "lorawan", "name": "LoRaWAN", "latency": 1000, "loss": 5, "bandwidth": "50 Kbps"},
            {"id": "congested", "name": "Congested", "latency": 200, "loss": 5, "bandwidth": "128 Kbps"}
        ]
    }

@app.get("/api/experiments", response_model=List[ExperimentResponse])
async def list_experiments():
    """List all experiments"""
    experiments = []
    for exp_id, exp in controller.experiments.items():
        experiments.append(ExperimentResponse(
            id=exp_id,
            name=exp.name,
            status=exp.status.value,
            config=exp.config,
            created_at=exp.created_at.isoformat(),
            started_at=exp.started_at.isoformat() if exp.started_at else None,
            completed_at=exp.completed_at.isoformat() if exp.completed_at else None,
            metrics=exp.get_current_metrics()
        ))
    return experiments

@app.post("/api/experiments", response_model=ExperimentResponse)
async def create_experiment(config: ExperimentConfig):
    """Create new experiment"""
    try:
        exp_id = controller.create_experiment(
            name=config.name,
            config=config.model_dump()
        )
        exp = controller.experiments[exp_id]
        
        return ExperimentResponse(
            id=exp_id,
            name=exp.name,
            status=exp.status.value,
            config=exp.config,
            created_at=exp.created_at.isoformat()
        )
    except Exception as e:
        logger.error(f"Error creating experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/experiments/{exp_id}", response_model=ExperimentResponse)
async def get_experiment(exp_id: str):
    """Get experiment details"""
    if exp_id not in controller.experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    exp = controller.experiments[exp_id]
    return ExperimentResponse(
        id=exp_id,
        name=exp.name,
        status=exp.status.value,
        config=exp.config,
        created_at=exp.created_at.isoformat(),
        started_at=exp.started_at.isoformat() if exp.started_at else None,
        completed_at=exp.completed_at.isoformat() if exp.completed_at else None,
        metrics=exp.get_current_metrics()
    )

@app.post("/api/experiments/{exp_id}/start")
async def start_experiment(exp_id: str, background_tasks: BackgroundTasks):
    """Start experiment in background"""
    if exp_id not in controller.experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    try:
        # Start experiment in background
        background_tasks.add_task(controller.start_experiment, exp_id)
        
        return {"status": "starting", "message": "Experiment started in background"}
    except Exception as e:
        logger.error(f"Error starting experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/experiments/{exp_id}/stop")
async def stop_experiment(exp_id: str):
    """Stop running experiment"""
    if exp_id not in controller.experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    try:
        controller.stop_experiment(exp_id)
        return {"status": "stopped", "message": "Experiment stopped"}
    except Exception as e:
        logger.error(f"Error stopping experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/experiments/{exp_id}")
async def delete_experiment(exp_id: str):
    """Delete experiment"""
    if exp_id not in controller.experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    try:
        controller.delete_experiment(exp_id)
        return {"status": "deleted", "message": "Experiment deleted"}
    except Exception as e:
        logger.error(f"Error deleting experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/experiments/{exp_id}/logs")
async def get_experiment_logs(exp_id: str, lines: int = 100):
    """Get experiment logs"""
    if exp_id not in controller.experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    try:
        logs = controller.get_logs(exp_id, lines)
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/experiments/{exp_id}/results")
async def get_experiment_results(exp_id: str):
    """Get experiment results"""
    if exp_id not in controller.experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    try:
        results = controller.get_results(exp_id)
        return results
    except Exception as e:
        logger.error(f"Error getting results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/experiments/{exp_id}/download")
async def download_results(exp_id: str):
    """Download results as JSON"""
    if exp_id not in controller.experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    try:
        results_path = controller.get_results_file(exp_id)
        if not results_path or not os.path.exists(results_path):
            raise HTTPException(status_code=404, detail="Results file not found")
        
        return FileResponse(
            results_path,
            media_type='application/json',
            filename=f"{exp_id}_results.json"
        )
    except Exception as e:
        logger.error(f"Error downloading results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/stats")
async def get_system_stats():
    """Get system resource usage"""
    return {
        "cpu": {
            "percent": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count()
        },
        "memory": {
            "percent": psutil.virtual_memory().percent,
            "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 2)
        },
        "disk": {
            "percent": psutil.disk_usage('/').percent,
            "free_gb": round(psutil.disk_usage('/').free / (1024**3), 2)
        }
    }

@app.websocket("/ws/{exp_id}")
async def websocket_endpoint(websocket: WebSocket, exp_id: str):
    """WebSocket for real-time experiment updates"""
    await manager.connect(websocket, exp_id)
    try:
        while True:
            # Get current metrics
            if exp_id in controller.experiments:
                exp = controller.experiments[exp_id]
                metrics = controller.get_current_metrics(exp_id)
                
                await websocket.send_json({
                    "type": "metrics",
                    "status": exp.status.value,
                    "data": metrics,
                    "timestamp": datetime.now().isoformat()
                })
            
            await asyncio.sleep(1)  # Update every second
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, exp_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, exp_id)

# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 STGen Web UI Backend")
    print("=" * 60)
    print(f"API Server: http://localhost:8000")
    print(f"API Docs: http://localhost:8000/docs")
    print("=" * 60)
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
