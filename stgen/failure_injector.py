##! @file failure_injector.py
##! @brief Failure Injection Framework for Testing Protocol Robustness
##! 
##! @details
##! Simulates realistic network failures and client crashes:
##! - Packet loss (random or targeted)
##! - Client crashes and recoveries
##! - Network partitions
##! - Data corruption
##! - Byzantine failures
##!
##! @author STGen Development Team
##! @version 2.0
##! @date 2024

import random
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

_LOG = logging.getLogger("failure_injector")


@dataclass
class FailureEvent:
    ##! @struct FailureEvent
    ##! @brief Represents a single failure event
    time_sec: float          ##! When failure occurs (seconds into test)
    failure_type: str        ##! Type: packet_loss, client_crash, network_partition, corruption
    target: Optional[str] = None  ##! Target client ID or None for global
    duration_sec: Optional[float] = None  ##! How long failure lasts
    metadata: Dict[str, Any] = None  ##! Additional failure parameters


class FailureInjector:
    ##! @class FailureInjector
    ##! @brief Injects realistic failures during protocol testing
    ##! @details
    ##! Supported failure modes:
    ##! - Packet loss (random or targeted)
    ##! - Client crashes and recovery
    ##! - Network partitions
    ##! - Client crashes and restarts
    ##! - Network partitions (split-brain)
    ##! - Message corruption
    ##! - Latency spikes
    
    def __init__(self, cfg: Dict[str, Any]):
        """
        Initialize failure injector.
        
        Args:
            cfg: Configuration with 'failure_injection' section:
                - packet_loss: float (0.0-1.0)
                - client_crashes: List[int] (times in seconds)
                - network_partition: {start_sec, duration_sec}
                - message_corruption: float (0.0-1.0)
                - latency_spike: {probability, duration_ms}
        """
        self.cfg = cfg  # Store the whole config, or look for 'failure_injection' key
        # Check if 'failure_injection' exists as a dict, or if we passed flat args
        fi_cfg = cfg.get("failure_injection", {})
        
        # If 'failure_rate' is at top level (e.g. from CLI overrides), use it for packet loss
        top_loss = cfg.get("failure_rate", 0.0)
        
        self.packet_loss_rate = fi_cfg.get("packet_loss", top_loss)
        self.corruption_rate = fi_cfg.get("message_corruption", 0.0)
        
        self.crash_times = fi_cfg.get("client_crashes", [])
        self.partition_cfg = self.cfg.get("network_partition", None)
        self.latency_spike_cfg = self.cfg.get("latency_spike", None)
        
        self.crashed_clients: set[str] = set()
        self.partition_active = False
        self.partition_end_time = 0.0
        
        self.start_time = time.time()
        self.events: List[FailureEvent] = []
        self.protocol = None
        
        _LOG.info("Failure Injector initialized: loss=%.1f%%, corruption=%.1f%%",
                  self.packet_loss_rate * 100, self.corruption_rate * 100)

    def attach_protocol(self, protocol_instance):
        """
        Attach protocol instance to control socket/client lifecycles.
        """
        self.protocol = protocol_instance
    
    def start(self):
        """Start failure injector (no-op for now unless running a background thread)."""
        self.start_time = time.time()
        _LOG.info("Failure Injection started")
    
    def stop(self):
        """Stop failure injector (no-op)."""
        _LOG.info("Failure Injection stopped")
        summary = self.get_failure_summary()
        _LOG.info("Failure Summary: %s", summary)
    
    def should_drop_packet(self, client_id: str) -> bool:
        """
        Determine if a packet should be dropped.
        
        Args:
            client_id: Client sending the packet
            
        Returns:
            bool: True if packet should be dropped
        """
        elapsed = time.time() - self.start_time
        
        # Check if client is crashed
        if client_id in self.crashed_clients:
            _LOG.debug(" Packet dropped: client %s crashed", client_id)
            return True
        
        # Check network partition
        if self.partition_active and time.time() < self.partition_end_time:
            # Partition affects half the clients (simple split-brain)
            if hash(client_id) % 2 == 0:
                _LOG.debug(" Packet dropped: network partition active")
                return True
        
        # Random packet loss
        if random.random() < self.packet_loss_rate:
            _LOG.debug(" Packet dropped: random loss")
            self.events.append(FailureEvent(
                time_sec=elapsed,
                failure_type="packet_loss",
                target=client_id
            ))
            return True
        
        return False
    
    def should_corrupt_message(self) -> bool:
        """
        Determine if message should be corrupted.
        
        Returns:
            bool: True if message should be corrupted
        """
        if random.random() < self.corruption_rate:
            elapsed = time.time() - self.start_time
            _LOG.warning("  Message corrupted")
            self.events.append(FailureEvent(
                time_sec=elapsed,
                failure_type="corruption"
            ))
            return True
        return False
    
    def corrupt_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Corrupt a message payload.
        
        Args:
            payload: Original message
            
        Returns:
            Corrupted message
        """
        corrupted = payload.copy()
        
        # Randomly corrupt one field
        if "sensor_data" in corrupted:
            # Flip bits in sensor data
            corrupted["sensor_data"] = "CORRUPTED_" + str(corrupted["sensor_data"])
        
        if "seq_no" in corrupted and random.random() > 0.5:
            # Corrupt sequence number
            corrupted["seq_no"] = (corrupted["seq_no"] + random.randint(-100, 100)) % 65536
        
        return corrupted
    
    def check_client_crashes(self) -> List[str]:
        """
        Check if any clients should crash now.
        
        Returns:
            List of client IDs to crash
        """
        elapsed = time.time() - self.start_time
        crashed_now = []
        
        for crash_time in self.crash_times:
            if abs(elapsed - crash_time) < 0.5 and crash_time not in [e.time_sec for e in self.events if e.failure_type == "client_crash"]:
                # Time to crash a random client
                client_id = f"client_{random.randint(0, 10)}"
                self.crashed_clients.add(client_id)
                crashed_now.append(client_id)
                
                _LOG.warning(" Client %s CRASHED at %.1fs", client_id, elapsed)
                self.events.append(FailureEvent(
                    time_sec=elapsed,
                    failure_type="client_crash",
                    target=client_id
                ))
        
        return crashed_now
    
    def revive_client(self, client_id: str) -> None:
        """
        Revive a crashed client.
        
        Args:
            client_id: Client to revive
        """
        if client_id in self.crashed_clients:
            self.crashed_clients.remove(client_id)
            elapsed = time.time() - self.start_time
            _LOG.info(" Client %s REVIVED at %.1fs", client_id, elapsed)
            self.events.append(FailureEvent(
                time_sec=elapsed,
                failure_type="client_revive",
                target=client_id
            ))
    
    def check_network_partition(self) -> bool:
        """
        Check if network partition should be activated.
        
        Returns:
            bool: True if partition just started
        """
        if not self.partition_cfg:
            return False
        
        elapsed = time.time() - self.start_time
        start_time = self.partition_cfg.get("start_sec", 0)
        duration = self.partition_cfg.get("duration_sec", 10)
        
        # Check if partition should start
        if not self.partition_active and abs(elapsed - start_time) < 0.5:
            self.partition_active = True
            self.partition_end_time = time.time() + duration
            _LOG.warning("NETWORK PARTITION started at %.1fs (duration: %ds)", elapsed, duration)
            self.events.append(FailureEvent(
                time_sec=elapsed,
                failure_type="network_partition",
                duration_sec=duration
            ))
            return True
        
        # Check if partition should end
        if self.partition_active and time.time() >= self.partition_end_time:
            self.partition_active = False
            _LOG.info(" NETWORK PARTITION healed at %.1fs", elapsed)
            self.events.append(FailureEvent(
                time_sec=elapsed,
                failure_type="partition_healed"
            ))
        
        return False
    
    def inject_latency_spike(self) -> Optional[float]:
        """
        Potentially inject artificial latency.
        
        Returns:
            Optional[float]: Extra delay in seconds, or None
        """
        if not self.latency_spike_cfg:
            return None
        
        probability = self.latency_spike_cfg.get("probability", 0.01)
        duration_ms = self.latency_spike_cfg.get("duration_ms", 500)
        
        if random.random() < probability:
            elapsed = time.time() - self.start_time
            delay_sec = duration_ms / 1000.0
            _LOG.warning("⏱️  Latency spike: +%.0fms", duration_ms)
            self.events.append(FailureEvent(
                time_sec=elapsed,
                failure_type="latency_spike",
                metadata={"delay_ms": duration_ms}
            ))
            return delay_sec
        
        return None
    
    def get_failure_summary(self) -> Dict[str, Any]:
        """
        Generate summary of all injected failures.
        
        Returns:
            Dict with failure statistics
        """
        summary = {
            "total_events": len(self.events),
            "packet_losses": len([e for e in self.events if e.failure_type == "packet_loss"]),
            "corruptions": len([e for e in self.events if e.failure_type == "corruption"]),
            "client_crashes": len([e for e in self.events if e.failure_type == "client_crash"]),
            "network_partitions": len([e for e in self.events if e.failure_type == "network_partition"]),
            "latency_spikes": len([e for e in self.events if e.failure_type == "latency_spike"]),
            "events": [
                {
                    "time_sec": e.time_sec,
                    "type": e.failure_type,
                    "target": e.target,
                    "duration_sec": e.duration_sec
                }
                for e in self.events[:50]  # Limit to first 50 events
            ]
        }
        
        return summary


# Helper function to enable failure injection in orchestrator
def wrap_send_with_failures(send_func, injector: FailureInjector):
    """
    Wrap protocol send_data() with failure injection.
    
    Args:
        send_func: Original send_data method
        injector: FailureInjector instance
        
    Returns:
        Wrapped function that may drop/corrupt packets
    """
    def wrapped_send(client_id: str, data: Dict) -> tuple:
        # Check for crashes
        injector.check_client_crashes()
        
        # Check for network partition
        injector.check_network_partition()
        
        # Should drop packet?
        if injector.should_drop_packet(client_id):
            return False, 0.0
        
        # Corrupt message?
        if injector.should_corrupt_message():
            data = injector.corrupt_payload(data)
        
        # Inject latency spike?
        spike_delay = injector.inject_latency_spike()
        if spike_delay:
            time.sleep(spike_delay)
        
        # Actually send
        return send_func(client_id, data)
    
    return wrapped_send