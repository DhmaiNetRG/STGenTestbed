#!/usr/bin/env python3
##! @file stgen_controller.py
##! @brief STGen Experiment Controller for Web UI Backend
##! 
##! @details
##! Manages STGen experiments programmatically with:
##! - Experiment lifecycle management (create, start, stop, cleanup)
##! - Real-time metrics collection from log files
##! - Subprocess orchestration and monitoring
##! - Persistence across server restarts
##! - Threading-based background execution
##!
##! @author STGen Development Team
##! @version 2.0
##! @date 2024

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional
import threading
import uuid

import psutil

logger = logging.getLogger(__name__)

# STGen path
STGEN_ROOT = Path(__file__).parent.parent.parent
RESULTS_DIR = STGEN_ROOT / "results" / "ui_experiments"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Python executable with STGen environment
PYTHON_EXECUTABLE = str(STGEN_ROOT / "myenv" / "bin" / "python3")

class ExperimentStatus(Enum):
    ##! @enum ExperimentStatus
    ##! @brief States of an experiment lifecycle
    CREATED = "created"      ##! Initial state after creation
    RUNNING = "running"      ##! Currently executing
    COMPLETED = "completed"  ##! Finished successfully
    FAILED = "failed"        ##! Execution failed
    STOPPED = "stopped"      ##! Manually stopped

class Experiment:
    ##! @class Experiment
    ##! @brief Represents a single STGen experiment
    ##! @details
    ##! Handles subprocess management, metrics parsing, and persistence
    
    def __init__(self, exp_id: str, name: str, config: dict):
        self.id = exp_id
        self.name = name
        self.config = config
        self.status = ExperimentStatus.CREATED
        self.process: Optional[subprocess.Popen] = None
        self.pid: Optional[int] = None
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.metrics: Dict = {}
        self.log_file = RESULTS_DIR / f"{exp_id}_log.txt"
        self.config_file = RESULTS_DIR / f"{exp_id}_config.json"
        self.results_file = RESULTS_DIR / f"{exp_id}_results.json"
        
        # Save config
        self.config_file.write_text(json.dumps(config, indent=2))
    
    def start(self):
        """Start the experiment"""
        if self.status != ExperimentStatus.CREATED:
            raise RuntimeError(f"Cannot start experiment in {self.status} state")
        
        try:
            # Start STGen process with output redirection using myenv Python
            cmd = [
                PYTHON_EXECUTABLE,
                "-m", "stgen.main",
                str(self.config_file)
            ]
            
            # Open log file in unbuffered mode
            self.log_fp = open(self.log_file, 'w', buffering=1)
            
            # Redirect stdin to /dev/null to prevent sudo prompts
            stdin_fp = open(os.devnull, 'r')
            
            self.process = subprocess.Popen(
                cmd,
                cwd=str(STGEN_ROOT),
                stdout=self.log_fp,
                stderr=subprocess.STDOUT,
                stdin=stdin_fp,
                text=True,
                bufsize=1
            )
            
            self.pid = self.process.pid
            self.status = ExperimentStatus.RUNNING
            self.started_at = datetime.now()
            
            logger.info(f"Experiment {self.id} started with PID {self.pid}")
            
            # Monitor in background thread
            threading.Thread(target=self._monitor, daemon=True).start()
            
        except Exception as e:
            self.status = ExperimentStatus.FAILED
            logger.error(f"Failed to start experiment {self.id}: {e}")
            if hasattr(self, 'log_fp'):
                self.log_fp.close()
            raise
    
    def _monitor(self):
        """Monitor experiment process"""
        if not self.process:
            return
        
        try:
            # Wait for process to complete
            self.process.wait()
            
            # Close log file
            if hasattr(self, 'log_fp'):
                self.log_fp.flush()
                self.log_fp.close()
            
            if self.process.returncode == 0:
                self.status = ExperimentStatus.COMPLETED
                self.completed_at = datetime.now()
                logger.info(f"Experiment {self.id} completed successfully")
                
                # Collect final metrics
                self._collect_final_metrics()
            else:
                self.status = ExperimentStatus.FAILED
                self.completed_at = datetime.now()
                logger.error(f"Experiment {self.id} failed with code {self.process.returncode}")
                
        except Exception as e:
            logger.error(f"Error monitoring experiment {self.id}: {e}")
            self.status = ExperimentStatus.FAILED
            if hasattr(self, 'log_fp'):
                self.log_fp.close()
    
    def stop(self):
        """Stop the experiment"""
        if self.status != ExperimentStatus.RUNNING:
            return
        
        try:
            if self.process:
                # Terminate gracefully
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                
                # Close log file
                if hasattr(self, 'log_fp'):
                    self.log_fp.flush()
                    self.log_fp.close()
                
                self.status = ExperimentStatus.STOPPED
                self.completed_at = datetime.now()
                logger.info(f"Experiment {self.id} stopped")
                
        except Exception as e:
            logger.error(f"Error stopping experiment {self.id}: {e}")
    
    def _collect_final_metrics(self):
        """Collect final metrics from results"""
        try:
            # Look for results in standard STGen results directory
            protocol = self.config.get('protocol', 'unknown')
            scenario_name = self.name.lower().replace(' ', '_')
            
            # Search for most recent result file matching this experiment
            results_pattern = STGEN_ROOT / "results"
            
            # Try to find result JSON
            for result_file in results_pattern.glob(f"{protocol}*/*.json"):
                # Read and check timestamp
                try:
                    with open(result_file, 'r') as f:
                        data = json.load(f)
                        
                        # Copy to our results directory
                        self.results_file.write_text(json.dumps(data, indent=2))
                        
                        self.metrics = {
                            "messages_sent": data.get("sent", 0),
                            "messages_received": data.get("recv", 0),
                            "packet_loss_percent": data.get("loss_percent", 0),
                            "avg_latency_ms": data.get("avg_latency", 0),
                            "p95_latency_ms": data.get("p95_latency", 0),
                            "throughput_mbps": data.get("throughput_mbps", 0),
                            "duration_sec": data.get("duration", 0)
                        }
                        break
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Error collecting final metrics for {self.id}: {e}")
    
    def get_current_metrics(self) -> Dict:
        """Get current real-time metrics"""
        metrics = {
            "status": self.status.value,
            "uptime_seconds": 0,
            "cpu_percent": 0,
            "memory_mb": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "packet_loss_percent": 0.0,
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "throughput_mbps": 0.0,
            "duration_sec": 0
        }
        
        if self.started_at:
            metrics["uptime_seconds"] = (datetime.now() - self.started_at).total_seconds()
        
        # Get process stats if running
        if self.pid and self.status == ExperimentStatus.RUNNING:
            try:
                process = psutil.Process(self.pid)
                metrics["cpu_percent"] = process.cpu_percent(interval=0.1)
                metrics["memory_mb"] = process.memory_info().rss / (1024 * 1024)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Parse metrics from log file (for both running and completed experiments)
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    log_content = f.read()
                    
                    # Look for final summary metrics (most accurate)
                    # Pattern: "Sent: 300, Received: 300" or "Sent: 300, Recv: 300"
                    import re
                    
                    # Try to find summary line first (from orchestrator)
                    summary_match = re.search(r'Sent:\s*(\d+),\s*(?:Received|Recv):\s*(\d+)', log_content)
                    if summary_match:
                        metrics["messages_sent"] = int(summary_match.group(1))
                        metrics["messages_received"] = int(summary_match.group(2))
                    else:
                        # Count individual SENDING and RECEIVED messages
                        sending_matches = re.findall(r'SENDING \(msg #(\d+)\)', log_content)
                        received_matches = re.findall(r'(?:RECEIVED|SERVER RECEIVED) \(msg #(\d+)\)', log_content)
                        
                        if sending_matches:
                            metrics["messages_sent"] = max([int(m) for m in sending_matches])
                        if received_matches:
                            metrics["messages_received"] = max([int(m) for m in received_matches])
                    
                    # Look for loss and latency
                    loss_match = re.search(r'Loss:\s*([\d.]+)%', log_content)
                    latency_match = re.search(r'Latency:\s*avg=([\d.]+)ms', log_content)
                    p50_match = re.search(r'p50=([\d.]+)ms', log_content)
                    
                    if loss_match:
                        metrics["packet_loss_percent"] = float(loss_match.group(1))
                    if latency_match:
                        metrics["avg_latency_ms"] = float(latency_match.group(1))
                    if p50_match:
                        metrics["p95_latency_ms"] = float(p50_match.group(1))
                        
            except Exception as e:
                logger.debug(f"Could not parse metrics from log: {e}")
        
        return metrics


class ExperimentController:
    """Controller for managing multiple experiments"""
    
    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}
        self._load_existing_experiments()
        logger.info("Experiment controller initialized")
    
    def _load_existing_experiments(self):
        """Load existing experiments from disk"""
        try:
            for config_file in RESULTS_DIR.glob("*_config.json"):
                exp_id = config_file.stem.replace("_config", "")
                
                # Read config
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Create experiment object
                name = config.get('name', exp_id)
                exp = Experiment(exp_id, name, config)
                
                # Set the file paths explicitly
                exp.log_file = RESULTS_DIR / f"{exp_id}_log.txt"
                exp.config_file = config_file
                exp.results_file = RESULTS_DIR / f"{exp_id}_results.json"
                
                # Check if log file exists to determine status
                if exp.log_file.exists():
                    exp.created_at = datetime.fromtimestamp(config_file.stat().st_ctime)
                    exp.started_at = datetime.fromtimestamp(exp.log_file.stat().st_ctime)
                    
                    # Check if completed
                    with open(exp.log_file, 'r') as f:
                        log_content = f.read()
                        if 'Test completed successfully' in log_content or 'Sensor stream complete' in log_content:
                            exp.status = ExperimentStatus.COMPLETED
                            exp.completed_at = datetime.fromtimestamp(exp.log_file.stat().st_mtime)
                        elif 'failed' in log_content.lower() or 'error' in log_content.lower():
                            exp.status = ExperimentStatus.FAILED
                            exp.completed_at = datetime.fromtimestamp(exp.log_file.stat().st_mtime)
                
                self.experiments[exp_id] = exp
                logger.info(f"Loaded experiment {exp_id} with status {exp.status.value}")
                
        except Exception as e:
            logger.error(f"Error loading existing experiments: {e}")
    
    def create_experiment(self, name: str, config: dict) -> str:
        """Create a new experiment"""
        exp_id = str(uuid.uuid4())[:8]
        
        experiment = Experiment(exp_id, name, config)
        self.experiments[exp_id] = experiment
        
        logger.info(f"Created experiment {exp_id}: {name}")
        return exp_id
    
    def start_experiment(self, exp_id: str):
        """Start an experiment"""
        if exp_id not in self.experiments:
            raise ValueError(f"Experiment {exp_id} not found")
        
        experiment = self.experiments[exp_id]
        experiment.start()
    
    def stop_experiment(self, exp_id: str):
        """Stop an experiment"""
        if exp_id not in self.experiments:
            raise ValueError(f"Experiment {exp_id} not found")
        
        experiment = self.experiments[exp_id]
        experiment.stop()
    
    def delete_experiment(self, exp_id: str):
        """Delete an experiment"""
        if exp_id not in self.experiments:
            raise ValueError(f"Experiment {exp_id} not found")
        
        experiment = self.experiments[exp_id]
        
        # Stop if running
        if experiment.status == ExperimentStatus.RUNNING:
            experiment.stop()
        
        # Clean up files
        for file_path in [experiment.log_file, experiment.config_file, experiment.results_file]:
            if file_path.exists():
                file_path.unlink()
        
        del self.experiments[exp_id]
        logger.info(f"Deleted experiment {exp_id}")
    
    def get_logs(self, exp_id: str, lines: int = 100) -> str:
        """Get experiment logs"""
        if exp_id not in self.experiments:
            raise ValueError(f"Experiment {exp_id} not found")
        
        experiment = self.experiments[exp_id]
        
        if not experiment.log_file.exists():
            return ""
        
        # Read last N lines
        try:
            with open(experiment.log_file, 'r') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
            return f"Error reading logs: {e}"
    
    def get_results(self, exp_id: str) -> Dict:
        """Get experiment results"""
        if exp_id not in self.experiments:
            raise ValueError(f"Experiment {exp_id} not found")
        
        experiment = self.experiments[exp_id]
        
        if not experiment.results_file.exists():
            return {"status": "no_results", "message": "Results not yet available"}
        
        try:
            with open(experiment.results_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading results: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_results_file(self, exp_id: str) -> Optional[Path]:
        """Get path to results file"""
        if exp_id not in self.experiments:
            return None
        
        return self.experiments[exp_id].results_file
    
    def get_current_metrics(self, exp_id: str) -> Dict:
        """Get current metrics for experiment"""
        if exp_id not in self.experiments:
            return {}
        
        return self.experiments[exp_id].get_current_metrics()
