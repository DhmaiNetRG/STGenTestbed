"""
Protocol Interface Contract for STGen
All protocol implementations must inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any


class ProtocolInterface(ABC):
    """
    Base class for all protocol implementations in STGen.
    
    Protocols can operate in two modes:
    - 'active': STGen orchestrator drives send_data() for each packet
    - 'passive': Protocol binaries run autonomously, STGen monitors
    """
    
    def __init__(self, cfg: Dict[str, Any]):
        """
        Initialize protocol with configuration.
        
        Args:
            cfg: Configuration dict containing:
                - mode: 'active' or 'passive'
                - server_ip: Server address
                - server_port: Server port
                - num_clients: Number of client instances
                - duration: Test duration in seconds
                - protocol-specific params
        """
        self.cfg = cfg
        self.mode = cfg.get("mode", "active")
        self._alive = True
    
    @abstractmethod
    def start_server(self) -> None:
        """
        Start the server process/thread.
        Should bind to cfg['server_ip:port'] and run in background.
        Must return immediately (non-blocking).
        """
        pass
    
    @abstractmethod
    def start_clients(self, num: int) -> None:
        """
        Launch N client processes/threads.
        Clients should connect to server but not send data yet.
        
        Args:
            num: Number of client instances to start
        """
        pass
    
    def send_data(self, client_id: str, data: Dict) -> Tuple[bool, float]:
        """
        Send sensor data from a specific client (ACTIVE MODE ONLY).
        
        Args:
            client_id: Identifier for the client
            data: Sensor data dict with keys:
                - dev_id: Device identifier
                - ts: Timestamp
                - seq_no: Sequence number
                - sensor_data: Actual sensor reading
        
        Returns:
            Tuple of (success: bool, timestamp: float)
            timestamp is server receipt time for latency calculation
        
        Note:
            For passive protocols, this can raise NotImplementedError
            or return (True, 0.0) placeholder values.
        """
        raise NotImplementedError("Use passive mode or override send_data")
    
    @abstractmethod
    def stop(self) -> None:
        """
        Gracefully shutdown all clients and server.
        Must kill/terminate all spawned processes.
        """
        pass
    
    def is_alive(self) -> bool:
        """
        Check if protocol processes are still running.
        
        Returns:
            bool: True if protocol is operational
        """
        return self._alive
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Optional: Return protocol-specific metrics.
        
        Returns:
            Dict with protocol-specific performance data
        """
        return {}