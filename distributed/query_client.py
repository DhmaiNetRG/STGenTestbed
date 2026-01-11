#!/usr/bin/env python3
"""
Query Client - Requests sensor data from the server
This client actively polls/queries the server for specific sensor data.

Usage:
  python query_client.py --server-ip 192.168.1.108 --server-port 5000 \
                         --protocol mqtt --query-interval 5 --query-filter "temp"
"""

import argparse
import json
import time
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path to find protocols and stgen modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S"
)
_LOG = logging.getLogger("query_client")


class QueryClient:
    """Client that queries server for sensor data."""
    
    def __init__(self, protocol: str, server_ip: str, server_port: int, cfg: Dict[str, Any]):
        self.protocol_name = protocol
        self.server_ip = server_ip
        self.server_port = server_port
        self.cfg = cfg
        self.protocol = None
        self.received_data: List[Dict] = []
        self.mqtt_client = None
        self.connected = False
        
    def connect(self):
        """Connect to server using specified protocol."""
        _LOG.info(f"Connecting to {self.protocol_name} server at {self.server_ip}:{self.server_port}")
        
        if self.protocol_name == "mqtt":
            self._connect_mqtt()
        else:
            self._connect_generic()
    
    def _connect_mqtt(self):
        """Connect to MQTT broker for querying."""
        try:
            import paho.mqtt.client as mqtt
            
            self.mqtt_client = mqtt.Client(
                client_id=f"query_client_{int(time.time())}",
                clean_session=True
            )
            
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            
            _LOG.info("Connecting to MQTT broker...")
            self.mqtt_client.connect(self.server_ip, self.server_port, 60)
            self.mqtt_client.loop_start()
            
            # Wait for connection
            timeout = 10
            elapsed = 0
            while not self.connected and elapsed < timeout:
                time.sleep(0.1)
                elapsed += 0.1
            
            if not self.connected:
                raise RuntimeError("Failed to connect to MQTT broker")
            
            _LOG.info("✓ Connected to MQTT broker")
            
        except ImportError:
            _LOG.error("paho-mqtt not installed. Run: pip install paho-mqtt")
            raise
        except Exception as e:
            _LOG.error(f"MQTT connection failed: {e}")
            raise
    
    def _connect_generic(self):
        """Generic protocol connection (fallback)."""
        # Import protocol dynamically
        try:
            import importlib
            try:
                mod = importlib.import_module(f"protocols.{self.protocol_name}.{self.protocol_name}")
            except (ImportError, ModuleNotFoundError):
                mod = importlib.import_module(f"protocols.{self.protocol_name}")
            
            # Create protocol instance in query mode
            query_cfg = {
                **self.cfg,
                "mode": "query",
                "server_ip": self.server_ip,
                "server_port": self.server_port,
                "role": "query_client",
                "num_clients": 0
            }
            
            self.protocol = mod.Protocol(query_cfg)
            self.protocol.start_server()
            self.connected = True
            _LOG.info("✓ Protocol loaded successfully")
            
        except Exception as e:
            _LOG.error(f"Failed to load protocol: {e}")
            raise
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback."""
        if rc == 0:
            self.connected = True
            # Subscribe to sensor data topic
            topic = self.cfg.get("topic", "stgen/sensors")
            client.subscribe(topic, qos=1)
            _LOG.debug(f"Subscribed to topic: {topic}")
        else:
            _LOG.error(f"MQTT connection failed with code {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback - collect incoming data."""
        try:
            data = json.loads(msg.payload.decode())
            self.received_data.append(data)
        except Exception as e:
            _LOG.warning(f"Failed to parse message: {e}")
    
    def query_data(self, query_filter: Dict[str, Any]) -> List[Dict]:
        """
        Query collected sensor data with filter.
        For MQTT, this returns filtered data from what we've received.
        
        Args:
            query_filter: Filter criteria (e.g., {"sensor_type": "temp", "node_id": "W1"})
            
        Returns:
            List of matching sensor readings
        """
        _LOG.info(f"📊 Querying data with filter: {query_filter}")
        
        try:
            # For MQTT, filter from received data
            if self.mqtt_client and self.mqtt_client.is_connected():
                return self._filter_data(self.received_data, query_filter)
            
            # For other protocols with query support
            elif self.protocol and hasattr(self.protocol, 'query_data'):
                results = self.protocol.query_data(query_filter)
                self.received_data.extend(results)
                _LOG.info(f"✓ Received {len(results)} data points")
                return results
            
            else:
                _LOG.warning("Not connected or no data available yet")
                return []
                
        except Exception as e:
            _LOG.error(f"Query failed: {e}")
            return []
    
    def _filter_data(self, data_list: List[Dict], query_filter: Dict[str, Any]) -> List[Dict]:
        """Apply filters to data list."""
        if not query_filter:
            return data_list
        
        filtered = []
        for data in data_list:
            match = True
            
            # Filter by node_id
            if 'node_id' in query_filter:
                if data.get('node_id') != query_filter['node_id']:
                    match = False
            
            # Filter by sensor type (extracted from dev_id)
            if 'sensor_type' in query_filter and match:
                dev_id = data.get('dev_id', '')
                sensor_type = dev_id.split('_')[0] if '_' in dev_id else ''
                
                # Support single type or list of types
                filter_types = query_filter['sensor_type']
                if isinstance(filter_types, str):
                    filter_types = [filter_types]
                
                if sensor_type not in filter_types:
                    match = False
            
            # Filter by device ID
            if 'dev_id' in query_filter and match:
                if data.get('dev_id') != query_filter['dev_id']:
                    match = False
            
            # Filter by minimum value (for numeric sensors)
            if 'min_value' in query_filter and match:
                sensor_value = data.get('sensor_data', {}).get('value')
                if sensor_value is not None and sensor_value < query_filter['min_value']:
                    match = False
            
            # Filter by maximum value (for numeric sensors)
            if 'max_value' in query_filter and match:
                sensor_value = data.get('sensor_data', {}).get('value')
                if sensor_value is not None and sensor_value > query_filter['max_value']:
                    match = False
            
            if match:
                filtered.append(data)
        
        return filtered
    
    def continuous_query(self, query_filter: Dict[str, Any], interval: int, duration: int):
        """
        Continuously collect and display filtered data.
        
        Args:
            query_filter: Filter criteria
            interval: Display interval in seconds
            duration: Total duration in seconds
        """
        _LOG.info(f"Starting continuous query (interval={interval}s, duration={duration}s)")
        
        # Check connection
        if self.mqtt_client and not self.mqtt_client.is_connected():
            _LOG.warning("Waiting for MQTT connection...")
            time.sleep(2)
        
        start_time = time.time()
        query_count = 0
        
        # Clear previous data
        self.received_data.clear()
        
        while (time.time() - start_time) < duration:
            query_count += 1
            _LOG.info(f"\n{'='*60}")
            _LOG.info(f"Query #{query_count} - Collected {len(self.received_data)} messages so far")
            _LOG.info(f"{'='*60}")
            
            # Query filtered data
            results = self.query_data(query_filter)
            
            if results:
                _LOG.info(f"✓ Found {len(results)} matching messages")
                # Display last 5 results
                display_count = min(5, len(results))
                _LOG.info(f"Showing last {display_count} results:")
                self._display_results(results[-display_count:])
            else:
                if len(self.received_data) == 0:
                    _LOG.info("⏳ Waiting for sensor data... (no messages received yet)")
                else:
                    _LOG.info(f"No messages match filter (collected {len(self.received_data)} total)")
            
            time.sleep(interval)
        
        _LOG.info(f"\n{'='*60}")
        _LOG.info(f"Query session complete")
        _LOG.info(f"  Total queries: {query_count}")
        _LOG.info(f"  Total messages collected: {len(self.received_data)}")
        _LOG.info(f"  Matching messages: {len(self._filter_data(self.received_data, query_filter))}")
        _LOG.info(f"{'='*60}")
    
    def _display_results(self, results: List[Dict]):
        """Display query results in a nice format."""
        for i, data in enumerate(results, 1):
            node_id = data.get('node_id', 'unknown')
            dev_id = data.get('dev_id', 'unknown')
            sensor_data = data.get('sensor_data', {})
            timestamp = data.get('ts', 0)
            
            _LOG.info(f"  [{i}] Node: {node_id} | Device: {dev_id}")
            _LOG.info(f"      Data: {sensor_data}")
            _LOG.info(f"      Time: {time.strftime('%H:%M:%S', time.localtime(timestamp))}")
    
    def save_results(self, output_file: str):
        """Save collected data to file."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.received_data, f, indent=2)
        
        _LOG.info(f"Results saved to {output_file}")
    
    def disconnect(self):
        """Disconnect from server."""
        if self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
                _LOG.info("Disconnected from MQTT broker")
            except Exception as e:
                _LOG.warning(f"Error disconnecting: {e}")
        
        if self.protocol and hasattr(self.protocol, 'stop'):
            self.protocol.stop()
            _LOG.info("Protocol stopped")


def main():
    parser = argparse.ArgumentParser(
        description="Query Client - Request sensor data from server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query all temperature sensors every 5 seconds
  python query_client.py --server-ip 192.168.1.108 --protocol mqtt \\
                         --query-filter '{"sensor_type": "temp"}' --query-interval 5

  # Query specific node
  python query_client.py --server-ip 192.168.1.108 --protocol mqtt \\
                         --query-filter '{"node_id": "W1"}' --query-interval 3

  # One-time query
  python query_client.py --server-ip 192.168.1.108 --protocol mqtt \\
                         --query-filter '{"sensor_type": "humidity"}' --once
        """
    )
    
    parser.add_argument("--server-ip", required=True, help="Server IP address")
    parser.add_argument("--server-port", type=int, default=5000, help="Server port")
    parser.add_argument("--protocol", default="mqtt", help="Protocol to use")
    parser.add_argument("--query-filter", default="{}", help="JSON filter for queries")
    parser.add_argument("--query-interval", type=int, default=5, 
                       help="Query interval in seconds")
    parser.add_argument("--duration", type=int, default=60,
                       help="Total query duration in seconds")
    parser.add_argument("--once", action="store_true", 
                       help="Run single query and exit")
    parser.add_argument("--output", default="results/query_results.json",
                       help="Output file for results")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Parse query filter
    try:
        query_filter = json.loads(args.query_filter)
    except json.JSONDecodeError as e:
        _LOG.error(f"Invalid query filter JSON: {e}")
        sys.exit(1)
    
    # Create configuration
    cfg = {
        "protocol": args.protocol,
        "server_ip": args.server_ip,
        "server_port": args.server_port,
        "query_filter": query_filter,
        "query_interval": args.query_interval
    }
    
    # Create and run query client
    client = QueryClient(
        protocol=args.protocol,
        server_ip=args.server_ip,
        server_port=args.server_port,
        cfg=cfg
    )
    
    try:
        print("\n" + "="*60)
        print("🔍 STGen Query Client")
        print("="*60)
        print(f"  Server: {args.server_ip}:{args.server_port}")
        print(f"  Protocol: {args.protocol}")
        print(f"  Filter: {query_filter}")
        print("="*60 + "\n")
        
        client.connect()
        
        if args.once:
            # Single query
            results = client.query_data(query_filter)
            if results:
                client._display_results(results)
        else:
            # Continuous querying
            client.continuous_query(
                query_filter=query_filter,
                interval=args.query_interval,
                duration=args.duration
            )
        
        # Save results
        if client.received_data:
            client.save_results(args.output)
        
    except KeyboardInterrupt:
        _LOG.info("\nQuery interrupted by user")
    except Exception as e:
        _LOG.exception("Query client failed")
        sys.exit(1)
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()