
"""
MQTT protocol plugin for STGen - Active mode with distributed support.
Supports:
- Core nodes: Run broker + subscriber (no publishers)
- Sensor nodes: Connect to remote broker as publishers
"""

import sys
import json
import logging
import time
import threading
import subprocess
import socket
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import paho.mqtt.client as mqtt
except ImportError as exc:
    raise ImportError(
        "paho-mqtt not installed — run: pip install paho-mqtt==1.6.1"
    ) from exc

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from stgen.protocol_interface import ProtocolInterface

_LOG = logging.getLogger("mqtt")


class EmbeddedBroker:
    """Minimal embedded MQTT broker manager."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 1883):
        self.host = host
        self.port = port
        self.process = None
        self.config_file = None
        
    def start(self) -> bool:
        """Start embedded Mosquitto broker."""
        # Check if port is already in use
        if self._is_port_open(self.host, self.port):
            _LOG.info("MQTT broker already running on %s:%s", self.host, self.port)
            return True
        
        # Create mosquitto config
        config_content = f"""
        listener {self.port} {self.host}
        allow_anonymous true
        max_queued_messages 10000
        max_inflight_messages 1000
        """
        
        self.config_file = Path(f"/tmp/mosquitto_{self.port}.conf")
        self.config_file.write_text(config_content)
        
        # Try to start mosquitto
        try:
            _LOG.info("Starting embedded Mosquitto broker on %s:%s...", self.host, self.port)
            self.process = subprocess.Popen(
                ["mosquitto", "-c", str(self.config_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for broker to be ready
            for _ in range(20):  # 2 seconds timeout
                if self._is_port_open(self.host, self.port):
                    _LOG.info(" Embedded broker started successfully")
                    return True
                time.sleep(0.1)
            
            _LOG.error("Broker process started but port not available")
            return False
            
        except FileNotFoundError:
            _LOG.error("Mosquitto not found. Install with: sudo apt install mosquitto")
            return False
        except Exception as e:
            _LOG.error("Failed to start embedded broker: %s", e)
            return False
    
    def stop(self):
        """Stop the embedded broker."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                _LOG.info("Embedded broker stopped")
            except Exception as e:
                _LOG.warning("Error stopping broker: %s", e)
                try:
                    self.process.kill()
                except:
                    pass
        
        # Clean up config file
        if self.config_file and self.config_file.exists():
            try:
                self.config_file.unlink()
            except:
                pass
    
    @staticmethod
    def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
        """Check if a port is open."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((host, port))
            return result == 0
        finally:
            sock.close()


class Protocol(ProtocolInterface):
    """MQTT plug-in with distributed architecture support."""

    def __init__(self, cfg: Dict[str, Any]):
        super().__init__(cfg)
        self._server_client: mqtt.Client | None = None
        self._clients: List[mqtt.Client] = []
        self._lat: List[float] = []
        self._alive: bool = True
        self._msg_count: int = 0
        self._recv_count: int = 0
        self._lock = threading.Lock()
        self._pending_msgs: Dict[int, float] = {}
        self._server_connected = False
        self._message_cache: List[Dict] = []  # Cache for query clients
        self._max_cache_size = 1000
        
        # Store config for role checking
        self._cfg = cfg
        self._role = cfg.get("role", "core")
        
        # MQTT config
        self.broker_host = cfg.get("server_ip", "127.0.0.1")
        self.broker_port = cfg.get("server_port", 1883)
        self.topic = cfg.get("topic", "stgen/sensors")
        self.qos = cfg.get("qos", 1)
        self.keepalive = cfg.get("keepalive", 60)
        
        # Embedded broker (only for core nodes)
        self._broker = None
        self._should_start_broker = (self._role == "core")
        
        if self._should_start_broker:
            self._broker = EmbeddedBroker(self.broker_host, self.broker_port)
        
        _LOG.info("MQTT Protocol initialized - Role: %s", self._role)

    def start_server(self):
        """Start MQTT server (broker + subscriber)."""
        
        # Core nodes: Start broker + subscriber
        if self._should_start_broker:
            _LOG.info(" Core mode - starting embedded broker")
            
            if not self._broker.start():
                raise RuntimeError("Failed to start embedded MQTT broker")
            
            time.sleep(0.5)  # Let broker stabilize
        
        # Sensor nodes: Just connect to remote broker
        else:
            _LOG.info(" Sensor mode - connecting to remote broker")
            _LOG.info("   Remote: %s:%s", self.broker_host, self.broker_port)
        
        # Both roles start subscriber
        self._start_subscriber()

    def _start_subscriber(self):
        """Start MQTT subscriber (works for both core and sensor nodes)."""
        try:
            client_id = f"stgen_server_{self._role}"
            
            self._server_client = mqtt.Client(
                client_id=client_id,
                clean_session=True,
                protocol=mqtt.MQTTv311
            )
            
            self._server_client.on_connect = self._on_server_connect
            self._server_client.on_message = self._on_server_message
            self._server_client.on_disconnect = self._on_server_disconnect
            
            _LOG.info("Connecting subscriber to %s:%s...", self.broker_host, self.broker_port)
            self._server_client.connect(
                self.broker_host, 
                self.broker_port, 
                keepalive=self.keepalive
            )
            self._server_client.loop_start()
            
            # Wait for connection
            timeout = 10
            elapsed = 0
            while not self._server_connected and elapsed < timeout:
                time.sleep(0.1)
                elapsed += 0.1
            
            if not self._server_connected:
                raise RuntimeError("Server subscriber failed to connect within 10s")
            
            _LOG.info("✓ Subscriber connected successfully")
            
        except Exception as e:
            _LOG.error("Failed to start subscriber: %s", e)
            raise

    def start_clients(self, num: int) -> None:
        """Start MQTT publisher clients (sensor nodes only)."""
        
        # Core nodes should never create clients
        if self._role == "core":
            _LOG.info("Core node - skipping client creation (server-only mode)")
            return
        
        _LOG.info("MQTT: Starting %d publisher clients", num)
        
        for i in range(num):
            client_id = f"stgen_client_{self._role}_{i}"
            client = mqtt.Client(
                client_id=client_id, 
                clean_session=True, 
                protocol=mqtt.MQTTv311
            )
            
            client.on_connect = lambda c, ud, f, rc, cid=client_id: self._on_client_connect(c, ud, f, rc, cid)
            client.on_publish = self._on_publish
            client.on_disconnect = lambda c, ud, rc, cid=client_id: self._on_client_disconnect(c, ud, rc, cid)
            
            try:
                client.connect(self.broker_host, self.broker_port, self.keepalive)
                client.loop_start()
                self._clients.append(client)
            except Exception as e:
                _LOG.error("Failed to connect client %s: %s", client_id, e)
        
        # Wait for all connections
        time.sleep(1.0)
        connected = sum(1 for c in self._clients if c.is_connected())
        _LOG.info("MQTT: %d/%d clients connected", connected, num)
        
        if connected == 0:
            raise RuntimeError("No MQTT clients could connect")

    def stop(self) -> None:
        """Stop all MQTT clients, subscriber, and embedded broker."""
        self._alive = False
        
        # Stop publisher clients
        for client in self._clients:
            try:
                client.loop_stop()
                client.disconnect()
            except Exception as e:
                _LOG.warning("Error stopping client: %s", e)
        
        # Stop subscriber
        if self._server_client:
            try:
                self._server_client.loop_stop()
                self._server_client.disconnect()
            except Exception as e:
                _LOG.warning("Error stopping subscriber: %s", e)
        
        # Stop embedded broker (only if we started it)
        if self._broker:
            self._broker.stop()
        
        _LOG.info("MQTT stopped - Sent: %d, Received: %d", 
                  self._msg_count, self._recv_count)

    def send_data(self, client_id: str, data: Dict) -> Tuple[bool, float]:
        """Publish sensor data via MQTT."""
        if not self._clients:
            _LOG.error("No MQTT clients available")
            return False, 0.0
        
        try:
            idx = int(client_id.split("_")[-1])
            client = self._clients[idx % len(self._clients)]
        except (ValueError, IndexError):
            client = self._clients[0]
        
        self._msg_count += 1
        payload = json.dumps(data)
        
        _LOG.info(" [%s] SENDING (msg #%d): dev=%s, seq=%s", 
                  client_id, self._msg_count, 
                  data.get('dev_id', '?'), 
                  data.get('seq_no', '?'))
        
        t0 = time.perf_counter()
        
        try:
            result = client.publish(
                topic=self.topic,
                payload=payload,
                qos=self.qos,
                retain=False
            )
            
            with self._lock:
                self._pending_msgs[result.mid] = t0
            
            if self.qos > 0:
                result.wait_for_publish(timeout=5.0)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return True, time.perf_counter()
            else:
                _LOG.warning("Publish failed with rc=%s", result.rc)
                return False, 0.0
                
        except Exception as e:
            _LOG.error("PUBLISH ERROR: %s", e)
            return False, 0.0

    # ==================== MQTT Callbacks ====================
    
    def _on_server_connect(self, client, userdata, flags, rc):
        """Callback when subscriber connects to broker."""
        if rc == 0:
            self._server_connected = True
            _LOG.info(" Subscriber connected (role=%s)", self._role)
            client.subscribe(self.topic, qos=self.qos)
            _LOG.info(" Subscribed to topic: %s (QoS %d)", self.topic, self.qos)
        else:
            _LOG.error(" Subscriber connection failed with code %s", rc)

    def _on_server_message(self, client, userdata, msg):
        """Callback when subscriber receives a message."""
        try:
            data = json.loads(msg.payload.decode())
            self._recv_count += 1
            
            node_id = data.get('node_id', 'unknown')
            dev_id = data.get('dev_id', '?')
            seq_no = data.get('seq_no', '?')
            
            _LOG.info(" RECEIVED (msg #%d): node=%s, dev=%s, seq=%s", 
                     self._recv_count, node_id, dev_id, seq_no)
            
            if "ts" in data:
                latency_ms = (time.time() - data["ts"]) * 1000
                self._lat.append(latency_ms)
                _LOG.debug("  End-to-end latency: %.2f ms", latency_ms)
                
        except Exception as e:
            _LOG.warning("Failed to parse received message: %s", e)

    def _on_server_disconnect(self, client, userdata, rc):
        """Callback when subscriber disconnects."""
        self._server_connected = False
        if rc != 0:
            _LOG.warning("  Subscriber disconnected unexpectedly (rc=%s)", rc)
        else:
            _LOG.info("Subscriber disconnected")

    def _on_client_connect(self, client, userdata, flags, rc, client_id):
        """Callback when publisher client connects."""
        if rc == 0:
            _LOG.debug(" Client %s connected", client_id)
        else:
            _LOG.error(" Client %s connection failed (rc=%s)", client_id, rc)

    def _on_publish(self, client, userdata, mid):
        """Callback when message is published."""
        with self._lock:
            if mid in self._pending_msgs:
                t0 = self._pending_msgs.pop(mid)
                latency_ms = (time.perf_counter() - t0) * 1000
                _LOG.debug("✓ Published (mid=%s, latency=%.2f ms)", mid, latency_ms)

    def _on_client_disconnect(self, client, userdata, rc, client_id):
        """Callback when publisher disconnects."""
        if rc != 0:
            _LOG.warning("  Client %s disconnected unexpectedly (rc=%s)", client_id, rc)

    def is_alive(self) -> bool:
        """Check if MQTT clients are still connected."""
        if self._role == "core":
            # Core just needs subscriber alive
            return self._alive and self._server_connected
        else:
            # Sensors need at least one client alive
            return self._alive and any(c.is_connected() for c in self._clients)


__all__ = ["Protocol"]