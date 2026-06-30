# #!/usr/bin/env python3
# """
# Distributed Sensor Node Runner
# Usage: python sensor_node.py --core-ip 192.168.1.100 --node-id A --sensors 1000
# """

# import argparse
# import json
# import subprocess
# import sys
# from pathlib import Path

# def main():
#     parser = argparse.ArgumentParser(description="Run distributed sensor cluster")
#     parser.add_argument("--core-ip", required=True, help="STGen Core IP address")
#     parser.add_argument("--core-port", default=5000, type=int, help="STGen Core port")
#     parser.add_argument("--node-id", required=True, help="Node identifier (A, B, C...)")
#     parser.add_argument("--sensors", default=1000, type=int, help="Number of sensors")
#     parser.add_argument("--sensor-types", default="temp:40,humidity:30,gps:20,camera:10", 
#                        help="Sensor distribution")
#     parser.add_argument("--duration", default=300, type=int, help="Test duration (seconds)")
#     parser.add_argument("--protocol", default="mqtt", help="Protocol to use")
    
#     parser.add_argument("--network-profile", help="Path to network condition profile JSON")
#     parser.add_argument("--interface", default="eth0", help="Network interface to apply conditions")

#     args = parser.parse_args()

#     if args.network_profile:
#         apply_network_profile(args.network_profile, args.interface)

    
#     # Build sensor configuration
#     config = {
#         "protocol": args.protocol,
#         "mode": "active",
#         "server_ip": args.core_ip,
#         "server_port": args.core_port,
#         "num_clients": args.sensors,
#         "duration": args.duration,
#         "node_id": args.node_id,  # Tag for identification
#         "role": "sensor",  # CRITICAL: Indicates this is a sensor node (client-only)
#         "sensors": parse_sensor_types(args.sensor_types)
#     }
    
#     # Save config
#     config_file = Path(f"node_{args.node_id}_config.json")
#     config_file.write_text(json.dumps(config, indent=2))
    
#     print(f"🚀 Starting Node {args.node_id} with {args.sensors} sensors")
#     print(f"   Core: {args.core_ip}:{args.core_port}")
#     print(f"   Protocol: {args.protocol}")
#     print(f"   Duration: {args.duration}s")
#     print(f"   Mode: CLIENT-ONLY (connecting to remote broker)")
    
#     # Run STGen
#     subprocess.run([sys.executable, "-m", "stgen.main", str(config_file)])

# def parse_sensor_types(spec):
#     """Parse 'temp:40,gps:30' into sensor list."""
#     sensors = []
#     for item in spec.split(","):
#         sensor_type, percentage = item.split(":")
#         sensors.append(f"{sensor_type}:{percentage}")
#     return sensors

# def apply_network_profile(profile_path: str, interface: str = "eth0"):
#     """Apply network profile to this sensor node."""
#     try:
#         from stgen.network_emulator import NetworkEmulator
#         emulator = NetworkEmulator.from_profile(profile_path, interface)
#         print(f"   Network Profile: {emulator.profile_name}")
#         return emulator
#     except ImportError:
#         print(f"   Warning: NetworkEmulator not available")
#         return None

# if __name__ == "__main__":
#     main()



#!/usr/bin/env python3
"""
Distributed Sensor Node Runner (Fixed)
Usage: python sensor_node.py --core-ip 192.168.1.100 --node-id A --sensors 1000
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Run distributed sensor cluster")
    parser.add_argument("--core-ip", required=True, help="STGen Core IP address")
    parser.add_argument("--core-port", default=5000, type=int, help="STGen Core port")
    parser.add_argument("--node-id", required=True, help="Node identifier (A, B, C...)")
    parser.add_argument("--sensors", default=1000, type=int, help="Number of sensors")
    parser.add_argument("--sensor-types", default="temp,humidity,motion", 
                       help="Comma-separated sensor types (e.g., temp,humidity,gps)")
    parser.add_argument("--duration", default=300, type=int, help="Test duration (seconds)")
    parser.add_argument("--protocol", default="mqtt", help="Protocol to use")
    
    parser.add_argument("--network-profile", help="Path to network condition profile JSON")
    parser.add_argument("--interface", default="eth0", help="Network interface to apply conditions")

    args = parser.parse_args()

    if args.network_profile:
        apply_network_profile(args.network_profile, args.interface)

    
    # Parse sensor types - now just a simple list
    sensor_list = [s.strip() for s in args.sensor_types.split(",")]
    
    # Build sensor configuration
    config = {
        "protocol": args.protocol,
        "mode": "active",
        "server_ip": args.core_ip,
        "server_port": args.core_port,
        "num_clients": args.sensors,
        "duration": args.duration,
        "node_id": args.node_id,
        "role": "sensor",  # CRITICAL: Indicates this is a sensor node (client-only)
        "sensors": sensor_list  # Simple list: ["temp", "humidity", "motion"]
    }
    
    # Save config
    config_file = Path(f"node_{args.node_id}_config.json")
    config_file.write_text(json.dumps(config, indent=2))
    
    print(f" Starting Node {args.node_id} with {args.sensors} sensors")
    print(f"   Core: {args.core_ip}:{args.core_port}")
    print(f"   Protocol: {args.protocol}")
    print(f"   Sensor Types: {', '.join(sensor_list)}")
    print(f"   Duration: {args.duration}s")
    print(f"   Mode: CLIENT-ONLY (connecting to remote broker)")
    
    # Run STGen
    subprocess.run([sys.executable, "-m", "stgen.main", str(config_file)])

def apply_network_profile(profile_path: str, interface: str = "eth0"):
    """Apply network profile to this sensor node."""
    try:
        from stgen.network_emulator import NetworkEmulator
        emulator = NetworkEmulator.from_profile(profile_path, interface)
        print(f"   Network Profile: {emulator.profile_name}")
        return emulator
    except ImportError:
        print(f"   Warning: NetworkEmulator not available")
        return None

if __name__ == "__main__":
    main()