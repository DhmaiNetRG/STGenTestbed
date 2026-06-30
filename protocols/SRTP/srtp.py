"""
SRTP protocol plugin for STGen – active mode.
Uses UDP sockets to communicate with SRTP binaries instead of sensor-launcher.
"""

import sys
import subprocess
import socket
import signal
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

# ensure stgen package is discoverable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from stgen.protocol_interface import ProtocolInterface

_LOG = logging.getLogger("srtp")


class Protocol(ProtocolInterface):
    """SRTP protocol wrapper for STGen - operates in ACTIVE mode."""

    def __init__(self, cfg: Dict[str, Any]):
        super().__init__(cfg)
        
        # Use active mode - STGen feeds data via UDP
        self.mode = "active"
        
        self._server_process: subprocess.Popen | None = None
        self._client_processes: List[subprocess.Popen] = []
        
        # SRTP uses two ports: one for sensors, one for clients
        self._sensor_port = cfg.get("server_port", 5004)
        self._client_port = cfg.get("client_port", 5005)
        
        # UDP socket for sending sensor data (replaces sensor-launcher)
        self._sensor_socket: socket.socket | None = None
        
        # Path to SRTP binaries
        self._srtp_dir = Path(__file__).parent
        self._server_bin = self._srtp_dir / "STGen_Server"
        self._client_bin = self._srtp_dir / "STGen_Client"
        
        # Configuration files
        self._client_config = self._srtp_dir.parent.parent / "conf" / "test.conf"
        self._sensor_list = self._srtp_dir / "sensor.list"
        
        # Metrics
        self._sent_count = 0
        self._latencies: List[float] = []
        
        _LOG.info("SRTP initialized: sensor_port=%d, client_port=%d, mode=active", 
                  self._sensor_port, self._client_port)

    def start_server(self) -> None:
        """Start SRTP server binary."""
        # Check if server binary exists
        if not self._server_bin.exists():
            _LOG.error(" STGen_Server binary not found at: %s", self._server_bin)
            raise FileNotFoundError(f"STGen_Server not found: {self._server_bin}")
        
        # Create sensor.list with expected sensors
        num_clients = self.cfg.get("num_clients", 4)
        sensor_types = ["temp", "device", "gps", "camera"]
        
        with open(self._sensor_list, 'w') as f:
            for i in range(num_clients):
                sensor = sensor_types[i % len(sensor_types)]
                f.write(f"{sensor}_{i}\n")
        
        _LOG.info("📝 Created sensor.list with %d entries", num_clients)
        
        # Start the SRTP server
        cmd = [
            str(self._server_bin),
            f"-i{self.cfg['server_ip']}",
            f"-p{self._sensor_port}",
            f"-s{self._client_port}",
            f"-l{self._sensor_list}",
            f"-c{self._client_config}"
        ]
        
        _LOG.info("📡 Starting SRTP Server: %s", " ".join(cmd))
        
        try:
            self._server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self._srtp_dir)
            )
            time.sleep(1.0)  # Give server time to bind
            
            # Check if server started successfully
            if self._server_process.poll() is not None:
                _LOG.error(" Server process died immediately")
                stderr = self._server_process.stderr.read().decode() if self._server_process.stderr else ""
                _LOG.error("Server stderr: %s", stderr)
                raise RuntimeError("SRTP server failed to start")
            
            _LOG.info(" SRTP Server started (PID: %d)", self._server_process.pid)
            
            # Create UDP socket for sending sensor data
            self._sensor_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            _LOG.info(" UDP socket created for sensor data")
            
        except Exception as e:
            _LOG.error("Failed to start SRTP server: %s", e)
            raise

    def start_clients(self, num: int) -> None:
        """Start PRTP client binaries."""
        _LOG.info("Starting %d PRTP clients", num)
        
        # Check if client binary exists
        if not self._client_bin.exists():
            _LOG.error(" STGen_Client binary not found at: %s", self._client_bin)
            raise FileNotFoundError(f"STGen_Client not found: {self._client_bin}")
        
        # Start clients
        for i in range(num):
            client_log = self._srtp_dir / f"client{i+1}_sensor_log"
            sensor_types = ["temp", "device", "gps", "camera"]
            sensor_id = f"{sensor_types[i % len(sensor_types)]}_{i}"
            
            cmd = [
                str(self._client_bin),
                f"-l{client_log}",
                f"-s{self.cfg['server_ip']}",
                f"-r{sensor_id}",
                f"-p{self._client_port}",
                "-A"  # Active mode flag
            ]
            
            _LOG.info("📱 Starting client %d: %s", i+1, " ".join(cmd))
            
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(self._srtp_dir)
                )
                self._client_processes.append(proc)
                time.sleep(0.2)
            except Exception as e:
                _LOG.error("Failed to start client %d: %s", i, e)
        
        _LOG.info(" Started %d clients", len(self._client_processes))

    def send_data(self, client_id: str, data: Dict) -> Tuple[bool, float]:
        """
        Send sensor data via UDP socket (mimics sensor.py behavior).
        
        Args:
            client_id: Client identifier (e.g., "client_0")
            data: Sensor data dict with keys:
                - dev_id: Device identifier
                - ts: Timestamp
                - seq_no: Sequence number
                - sensor_data: Actual sensor reading
        
        Returns:
            Tuple of (success: bool, timestamp: float)
        """
        if not self._sensor_socket:
            _LOG.error(" Sensor socket not initialized")
            return False, 0.0
        
        try:
            # Format message similar to sensor.py output
            message = str(data)  # Convert dict to string representation
            
            # Send via UDP to server's sensor port
            server_address = (self.cfg['server_ip'], self._sensor_port)
            sent_bytes = self._sensor_socket.sendto(
                message.encode('utf-8'), 
                server_address
            )
            
            self._sent_count += 1
            t_sent = time.perf_counter()
            
            # Log every message with full details
            sensor_data_preview = str(data.get('sensor_data', ''))[:50]
            _LOG.info("📤 [%s] SENT msg #%d from %s: %s (size: %d bytes)", 
                      client_id, 
                      data.get('seq_no', 0),
                      data.get('dev_id', 'unknown'),
                      sensor_data_preview,
                      sent_bytes)
            
            return True, t_sent
            
        except Exception as e:
            _LOG.error(" Failed to send data: %s", e)
            return False, 0.0

    def stop(self) -> None:
        """Gracefully shutdown all processes."""
        _LOG.info("Stopping SRTP protocol...")
        
        # Close sensor socket
        if self._sensor_socket:
            self._sensor_socket.close()
            _LOG.debug("Closed UDP sensor socket")
        
        # Stop clients
        for i, proc in enumerate(self._client_processes):
            if proc.poll() is None:
                _LOG.info("Stopping client %d (PID: %d)", i+1, proc.pid)
                try:
                    proc.send_signal(signal.SIGINT)
                    proc.wait(timeout=2)
                except Exception:
                    proc.kill()
        
        # Stop server
        if self._server_process and self._server_process.poll() is None:
            _LOG.info("Stopping server (PID: %d)", self._server_process.pid)
            try:
                self._server_process.send_signal(signal.SIGINT)
                self._server_process.wait(timeout=2)
            except Exception:
                self._server_process.kill()
        
        # Parse client logs for metrics
        self._parse_client_logs()
        
        _LOG.info(" SRTP protocol stopped")
        self._alive = False

    def _parse_client_logs(self) -> None:
        """Parse client logs to extract received message count."""
        total_received = 0
        
        for i, proc in enumerate(self._client_processes):
            client_log_path = self._srtp_dir / f"client{i+1}_sensor_log"
            
            if not client_log_path.exists():
                _LOG.warning("Client %d log not found: %s", i+1, client_log_path)
                continue
            
            try:
                # Check if it's a directory or file
                if client_log_path.is_dir():
                    # Parse all files in the directory
                    log_files = list(client_log_path.glob("*.log")) + list(client_log_path.glob("*.txt"))
                    if not log_files:
                        log_files = list(client_log_path.iterdir())
                    
                    recv_count = 0
                    for log_file in log_files:
                        if log_file.is_file():
                            try:
                                lines = log_file.read_text().strip().split('\n')
                                recv_count += len([l for l in lines if l.strip()])
                                _LOG.debug("📄 Parsed %s: %d messages", log_file.name, len(lines))
                            except Exception as e:
                                _LOG.debug("Could not parse %s: %s", log_file.name, e)
                    
                    total_received += recv_count
                    _LOG.info("📊 Client %d received %d messages", i+1, recv_count)
                else:
                    # It's a single file
                    lines = client_log_path.read_text().strip().split('\n')
                    recv_count = len([l for l in lines if l.strip()])
                    total_received += recv_count
                    _LOG.info("📊 Client %d received %d messages", i+1, recv_count)
                    
            except Exception as e:
                _LOG.warning("Failed to parse client %d log: %s", i+1, e)
        
        if total_received > 0:
            _LOG.info("📊 Total sent: %d, Total received: %d, Loss: %.1f%%",
                      self._sent_count, total_received,
                      (1 - total_received/max(self._sent_count, 1)) * 100)
        else:
            _LOG.warning("📊 No messages found in client logs (sent: %d)", self._sent_count)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Return protocol-specific metrics."""
        return {
            "sent_count": self._sent_count,
            "protocol_type": "UDP-based SRTP"
        }


# Ensure the orchestrator can find the Protocol symbol
__all__ = ["Protocol"]



# """
# SRTP protocol plugin for STGen – passive mode.
# Runs SRTP server, sensors, and clients autonomously and parses their logs for metrics.
# """

# import sys
# import subprocess
# import signal
# import time
# import logging
# import re
# from pathlib import Path
# from typing import Any, Dict, List, Tuple

# sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# from stgen.protocol_interface import ProtocolInterface

# _LOG = logging.getLogger("srtp")


# class Protocol(ProtocolInterface):
#     """SRTP protocol wrapper for STGen - operates in PASSIVE mode."""

#     def __init__(self, cfg: Dict[str, Any]):
#         super().__init__(cfg)
        
#         self.mode = "active"
        
#         self._server_process: subprocess.Popen | None = None
#         self._sensor_processes: List[subprocess.Popen] = []
#         self._client_processes: List[subprocess.Popen] = []
        
#         # SRTP uses two ports
#         self._sensor_port = cfg.get("server_port", 5004)
#         self._client_port = cfg.get("client_port", 5005)
        
#         # Paths
#         self._srtp_dir = Path(__file__).parent
#         self._server_bin = self._srtp_dir / "STGen_Server"
#         self._client_bin = self._srtp_dir / "STGen_Client"
#         self._sensor_script = self._srtp_dir.parent.parent / "stgen" / "sensor.py"
        
#         # Config files
#         self._client_config = self._srtp_dir.parent.parent / "conf" / "test.conf"
#         self._sensor_list = self._srtp_dir / "sensor.list"
        
#         # Metrics
#         self._latencies: List[float] = []
#         self._recv_count = 0
        
#         _LOG.info("SRTP initialized (passive mode): sensor_port=%d, client_port=%d", 
#                   self._sensor_port, self._client_port)

#     def start_server(self) -> None:
#         """Start SRTP server binary."""
#         if not self._server_bin.exists():
#             _LOG.error("STGen_Server binary not found: %s", self._server_bin)
#             raise FileNotFoundError(f"STGen_Server not found: {self._server_bin}")
        
#         # Create sensor.list
#         num_clients = self.cfg.get("num_clients", 4)
#         sensor_types = ["temp", "device", "gps", "camera"]
        
#         with open(self._sensor_list, 'w') as f:
#             for i in range(num_clients):
#                 sensor = sensor_types[i % len(sensor_types)]
#                 f.write(f"{sensor}_{i}\n")
        
#         _LOG.info("Created sensor.list with %d entries", num_clients)
        
#         # Start server
#         cmd = [
#             str(self._server_bin),
#             f"-i{self.cfg['server_ip']}",
#             f"-p{self._sensor_port}",
#             f"-s{self._client_port}",
#             f"-l{self._sensor_list}",
#             f"-c{self._client_config}"
#         ]
        
#         _LOG.info("Starting SRTP Server")
        
#         try:
#             self._server_process = subprocess.Popen(
#                 cmd,
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE,
#                 cwd=str(self._srtp_dir)
#             )
#             time.sleep(1.0)
            
#             if self._server_process.poll() is not None:
#                 stderr = self._server_process.stderr.read().decode() if self._server_process.stderr else ""
#                 _LOG.error("Server failed to start: %s", stderr)
#                 raise RuntimeError("SRTP server failed to start")
            
#             _LOG.info("SRTP Server started (PID: %d)", self._server_process.pid)
            
#         except Exception as e:
#             _LOG.error("Failed to start SRTP server: %s", e)
#             raise

#     def start_clients(self, num: int) -> None:
#         """
#         Start SRTP sensors (these send data to server).
#         Then start SRTP clients (these subscribe to sensors).
#         """
#         _LOG.info("Starting %d SRTP sensors and clients", num)
        
#         if not self._sensor_script.exists():
#             _LOG.error("sensor.py not found: %s", self._sensor_script)
#             raise FileNotFoundError(f"sensor.py not found: {self._sensor_script}")
        
#         if not self._client_bin.exists():
#             _LOG.error("STGen_Client binary not found: %s", self._client_bin)
#             raise FileNotFoundError(f"STGen_Client not found: {self._client_bin}")
        
#         # Create log directory
#         log_dir = self._srtp_dir / "client_logs"
#         log_dir.mkdir(exist_ok=True)
        
#         sensor_types = ["temp", "device", "gps", "camera"]
        
#         # Start SENSORS first (they send data to server on sensor_port)
#         _LOG.info("Starting %d sensors", num)
#         for i in range(num):
#             sensor_type = sensor_types[i % len(sensor_types)]
#             sensor_id = str(i)
            
#             cmd = [
#                 "python3",
#                 str(self._sensor_script),
#                 sensor_type,
#                 self.cfg['server_ip'],
#                 str(self._sensor_port),
#                 sensor_id
#             ]
            
#             _LOG.debug("Starting sensor: %s_%s", sensor_type, sensor_id)
#             try:
#                 proc = subprocess.Popen(
#                     cmd,
#                     stdout=subprocess.PIPE,
#                     stderr=subprocess.PIPE,
#                     cwd=str(self._srtp_dir.parent.parent / "stgen")  # Run from stgen/ directory
#                 )
#                 self._sensor_processes.append(proc)
                
#                 # ADD THIS: Check if process died immediately
#                 time.sleep(0.5)
#                 if proc.poll() is not None:
#                     stdout = proc.stdout.read().decode() if proc.stdout else ""
#                     stderr = proc.stderr.read().decode() if proc.stderr else ""
#                     _LOG.error("Sensor %d died immediately. stdout: %s stderr: %s", i, stdout, stderr)
#                 else:
#                     _LOG.info("Sensor %d started successfully", i)
                
#                 time.sleep(0.1)
#             except Exception as e:
#                 _LOG.error("Failed to start sensor %d: %s", i, e)
            
#             # try:
#             #     proc = subprocess.Popen(
#             #         cmd,
#             #         stdout=subprocess.PIPE,
#             #         stderr=subprocess.PIPE,
#             #         cwd=str(log_dir)
#             #     )
#             #     self._sensor_processes.append(proc)
#             #     time.sleep(0.1)
#             # except Exception as e:
#             #     _LOG.error("Failed to start sensor %d: %s", i, e)
        
#         _LOG.info("Started %d sensors", len(self._sensor_processes))
#         time.sleep(1.0)  # Let sensors start sending data
        
#         # Start CLIENTS (they subscribe to sensors on client_port)
#         # _LOG.info("Starting %d client subscribers", num)
#         # for i in range(num):
#         #     cmd = [
#         #         str(self._client_bin),
#         #         f"-l{log_dir}",
#         #         f"-s{self.cfg['server_ip']}",
#         #         f"-p{self._client_port}",
#         #         "-A"  # Subscribe to all sensors reliably
#         #     ]
            
#         # Start CLIENTS (they subscribe to sensors on client_port)
#         _LOG.info("Starting %d client subscribers", num)
#         for i in range(num):
#             # Define the specific sensor ID for this client
#             sensor_type = sensor_types[i % len(sensor_types)]
#             sensor_id = f"{sensor_type}_{i}"
            
#             cmd = [
#                 str(self._client_bin),
#                 f"-l{log_dir}",
#                 f"-s{self.cfg['server_ip']}",
#                 f"-p{self._client_port}",
#                 # Add the -r flag to subscribe to one sensor immediately
#                 "-r", sensor_id,
#                 # Keep the -A flag to ensure it subscribes to all others as well
#                 "-A"
#             ]
#             _LOG.debug("Starting client %d", i+1)
            
#             try:
#                 proc = subprocess.Popen(
#                     cmd,
#                     stdout=subprocess.PIPE,
#                     stderr=subprocess.PIPE,
#                     cwd=str(self._srtp_dir)
#                 )
#                 self._client_processes.append(proc)
#                 time.sleep(0.1)
#             except Exception as e:
#                 _LOG.error("Failed to start client %d: %s", i, e)
        
#         _LOG.info("Started %d clients", len(self._client_processes))

#     def send_data(self, client_id: str, data: Dict) -> Tuple[bool, float]:
#         """Not used in passive mode."""
#         raise NotImplementedError("SRTP uses passive mode")

#     def stop(self) -> None:
#         """Gracefully shutdown all processes."""
#         _LOG.info("Stopping SRTP protocol...")
        
#         # Stop clients first
#         for i, proc in enumerate(self._client_processes):
#             if proc.poll() is None:
#                 _LOG.debug("Stopping client %d (PID: %d)", i+1, proc.pid)
#                 try:
#                     proc.send_signal(signal.SIGINT)
#                     proc.wait(timeout=2)
#                 except Exception:
#                     proc.kill()
        
#         # Stop sensors
#         for i, proc in enumerate(self._sensor_processes):
#             if proc.poll() is None:
#                 _LOG.debug("Stopping sensor %d (PID: %d)", i+1, proc.pid)
#                 try:
#                     proc.send_signal(signal.SIGINT)
#                     proc.wait(timeout=2)
#                 except Exception:
#                     proc.kill()
        
#         # Stop server
#         if self._server_process and self._server_process.poll() is None:
#             _LOG.debug("Stopping server (PID: %d)", self._server_process.pid)
#             try:
#                 self._server_process.send_signal(signal.SIGINT)
#                 self._server_process.wait(timeout=2)
#             except Exception:
#                 self._server_process.kill()
        
#         time.sleep(0.5)
        
#         # Parse logs
#         self._parse_client_logs()
        
#         _LOG.info("SRTP protocol stopped")
#         self._alive = False

#     def _parse_client_logs(self) -> None:
#         """Parse sensor log files to extract latencies and message counts."""
#         total_received = 0
#         self._latencies = []
        
#         log_dir = self._srtp_dir / "client_logs"
        
#         if not log_dir.exists():
#             _LOG.warning("Log directory not found: %s", log_dir)
#             return
        
#         # Find all sensor log files
#         sensor_log_files = list(log_dir.glob("*.log"))
        
#         if not sensor_log_files:
#             _LOG.warning("No .log files found in %s", log_dir)
#             return
        
#         _LOG.debug("Found %d sensor log files", len(sensor_log_files))
        
#         for log_file in sensor_log_files:
#             try:
#                 with open(log_file, 'r') as f:
#                     lines = f.readlines()
                
#                 prev_timestamp = None
                
#                 for line in lines:
#                     line = line.strip()
#                     if not line:
#                         continue
                    
#                     try:
#                         # Format: timestamp<tab>seq_no<tab>value
#                         parts = line.split('\t')
#                         if len(parts) >= 2:
#                             timestamp = float(parts[0])
                            
#                             total_received += 1
                            
#                             # Calculate inter-packet latency (time between messages)
#                             if prev_timestamp is not None:
#                                 latency_ms = (timestamp - prev_timestamp) * 1000
#                                 self._latencies.append(latency_ms)
                            
#                             prev_timestamp = timestamp
#                     except (ValueError, IndexError):
#                         pass
                
#                 _LOG.debug("Parsed %s: %d messages", log_file.name, len(lines))
                
#             except Exception as e:
#                 _LOG.warning("Failed to parse %s: %s", log_file.name, e)
        
#         self._recv_count = total_received
        
#         if total_received > 0:
#             _LOG.info("Total messages received: %d", total_received)
#             if self._latencies:
#                 avg_latency = sum(self._latencies) / len(self._latencies)
#                 min_latency = min(self._latencies)
#                 max_latency = max(self._latencies)
#                 _LOG.info("Latencies - Count: %d, Avg: %.2f ms, Min: %.2f ms, Max: %.2f ms",
#                          len(self._latencies), avg_latency, min_latency, max_latency)
#         else:
#             _LOG.warning("No messages found in sensor logs")

#     def get_metrics(self) -> Dict[str, Any]:
#         """Return protocol-specific metrics."""
#         return {
#             "messages_received": self._recv_count,
#             "latencies_collected": len(self._latencies),
#             "protocol_type": "SRTP-Publish-Subscribe"
#         }


# __all__ = ["Protocol"]