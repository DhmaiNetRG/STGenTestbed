"""
Template protocol implementation.
Copy this to create your own protocol plugin.
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from stgen.protocol_interface import ProtocolInterface


class Protocol(ProtocolInterface):
    """
    Template protocol - replace with your implementation.
    """
    
    def __init__(self, cfg):
        super().__init__(cfg)
        # Initialize your protocol here
    
    def start_server(self) -> None:
        """
        Start your server process/thread.
        Must be non-blocking.
        """
        # TODO: Implement server startup
        pass
    
    def start_clients(self, num: int) -> None:
        """
        Start N client processes/threads.
        
        Args:
            num: Number of clients to start
        """
        # TODO: Implement client startup
        pass
    
    def send_data(self, client_id: str, data: dict):
        """
        Send data from a client (ACTIVE mode only).
        
        Args:
            client_id: Client identifier
            data: Sensor data dictionary
        
        Returns:
            (success: bool, timestamp: float)
        """
        # TODO: Implement data sending
        # For passive mode, return (True, 0.0)
        return (True, 0.0)
    
    def stop(self) -> None:
        """
        Stop all processes gracefully.
        """
        self._alive = False
        # TODO: Implement cleanup