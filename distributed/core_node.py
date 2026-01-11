# # #!/usr/bin/env python3
# # """
# # Distributed STGen Core Runner
# # Usage: python core_node.py --bind-ip 0.0.0.0 --protocol mqtt
# # """

# # import argparse
# # import json
# # import subprocess
# # import sys
# # from pathlib import Path

# # def main():
# #     parser = argparse.ArgumentParser(description="Run STGen Core node")
# #     parser.add_argument("--bind-ip", default="0.0.0.0", help="IP to bind to")
# #     parser.add_argument("--sensor-port", default=5000, type=int)
# #     parser.add_argument("--client-port", default=5001, type=int)
# #     parser.add_argument("--protocol", default="mqtt", help="Protocol to use")
# #     parser.add_argument("--duration", default=300, type=int)
# #     parser.add_argument("--enable-elk", action="store_true", help="Enable ELK monitoring")
    
# #     args = parser.parse_args()
    
# #     config = {
# #         "protocol": args.protocol,
# #         "mode": "active",
# #         "server_ip": args.bind_ip,
# #         "server_port": args.sensor_port,
# #         "client_port": args.client_port,
# #         "duration": args.duration,
# #         "role": "core",  # Indicates this is the core node
# #         "enable_elk": args.enable_elk
# #     }
    
# #     config_file = Path("core_node_config.json")
# #     config_file.write_text(json.dumps(config, indent=2))
    
# #     print(f"🎯 Starting STGen Core")
# #     print(f"   Bind IP: {args.bind_ip}")
# #     print(f"   Sensor Port: {args.sensor_port}")
# #     print(f"   Protocol: {args.protocol}")
    
# #     subprocess.run([sys.executable, "-m", "stgen.main", str(config_file)])

# # if __name__ == "__main__":
# #     main()


# #!/usr/bin/env python3
# """
# Distributed STGen Core Runner
# Usage: python core_node.py --bind-ip 0.0.0.0 --protocol mqtt
# """

# import argparse
# import json
# import subprocess
# import sys
# from pathlib import Path

# def main():
#     parser = argparse.ArgumentParser(description="Run STGen Core node")
#     parser.add_argument("--bind-ip", default="0.0.0.0", help="IP to bind to")
#     parser.add_argument("--sensor-port", default=5000, type=int)
#     parser.add_argument("--client-port", default=5001, type=int)
#     parser.add_argument("--protocol", default="mqtt", help="Protocol to use")
#     parser.add_argument("--duration", default=300, type=int)
#     parser.add_argument("--num-clients", default=4, type=int, help="Number of simulated clients")
#     parser.add_argument("--sensors", nargs="+", default=["temp", "humidity", "motion"],
#                         help="List of sensors to simulate (default: temp humidity motion)")
#     parser.add_argument("--enable-elk", action="store_true", help="Enable ELK monitoring")
    
#     args = parser.parse_args()
    
#     # --- Build complete config ---
#     config = {
#         "protocol": args.protocol,
#         "mode": "active",
#         "server_ip": args.bind_ip,
#         "server_port": args.sensor_port,
#         "client_port": args.client_port,
#         "num_clients": args.num_clients,
#         "duration": args.duration,
#         "sensors": args.sensors,
#         "role": "core",  # Indicates this is the core node
#         "enable_elk": args.enable_elk
#     }
    
#     config_file = Path("core_node_config.json")
#     config_file.write_text(json.dumps(config, indent=2))
    
#     print(f"🎯 Starting STGen Core")
#     print(f"   Bind IP: {args.bind_ip}")
#     print(f"   Sensor Port: {args.sensor_port}")
#     print(f"   Protocol: {args.protocol}")
#     print(f"   Clients: {args.num_clients}")
#     print(f"   Sensors: {', '.join(args.sensors)}")
    
#     # Launch main test with generated config
#     subprocess.run([sys.executable, "-m", "stgen.main", str(config_file)])

# if __name__ == "__main__":
#     main()


#!/usr/bin/env python3
"""
Distributed STGen Core Runner (Fixed)
The core node runs broker + subscriber ONLY, no local clients.
Usage: python core_node.py --bind-ip 0.0.0.0 --protocol mqtt
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Run STGen Core node")
    parser.add_argument("--bind-ip", default="0.0.0.0", help="IP to bind to")
    parser.add_argument("--sensor-port", default=5000, type=int)
    parser.add_argument("--protocol", default="mqtt", help="Protocol to use")
    parser.add_argument("--duration", default=300, type=int)
    parser.add_argument("--enable-elk", action="store_true", help="Enable ELK monitoring")
    
    args = parser.parse_args()
    
    # Core node config - NO local clients
    config = {
        "protocol": args.protocol,
        "mode": "active",
        "server_ip": args.bind_ip,
        "server_port": args.sensor_port,
        "num_clients": 0,  # CRITICAL: Core doesn't create clients
        "duration": args.duration,
        "role": "core",
        "enable_elk": args.enable_elk
    }
    
    config_file = Path("core_node_config.json")
    config_file.write_text(json.dumps(config, indent=2))
    
    print(f"🎯 Starting STGen Core (Broker + Subscriber Only)")
    print(f"   Bind IP: {args.bind_ip}")
    print(f"   Sensor Port: {args.sensor_port}")
    print(f"   Protocol: {args.protocol}")
    print(f"   Mode: SERVER ONLY (no local clients)")
    
    # Launch main test with generated config
    subprocess.run([sys.executable, "-m", "stgen.main", str(config_file)])

if __name__ == "__main__":
    main()