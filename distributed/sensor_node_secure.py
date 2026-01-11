#!/usr/bin/env python3
"""
Add API key authentication to distributed STGen
Usage: python sensor_node_secure.py --core-ip X.X.X.X --api-key YOUR_SECRET_KEY
"""

import argparse
import hashlib
import hmac
import json
import subprocess
import sys
import time
from pathlib import Path

# Shared secret key (in production, use environment variable or config file)
SECRET_KEY = "your-secret-key-here-change-this"

def generate_auth_token(node_id: str, timestamp: int = None) -> str:
    """Generate HMAC-based authentication token."""
    if timestamp is None:
        timestamp = int(time.time())
    
    message = f"{node_id}:{timestamp}"
    token = hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"{message}:{token}"

def verify_auth_token(token: str, max_age: int = 300) -> tuple[bool, str]:
    """Verify authentication token."""
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return False, "Invalid token format"
        
        node_id, timestamp_str, provided_token = parts
        timestamp = int(timestamp_str)
        
        # Check timestamp freshness (prevent replay attacks)
        current_time = int(time.time())
        if abs(current_time - timestamp) > max_age:
            return False, "Token expired"
        
        # Verify HMAC
        message = f"{node_id}:{timestamp}"
        expected_token = hmac.new(
            SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if hmac.compare_digest(expected_token, provided_token):
            return True, node_id
        else:
            return False, "Invalid signature"
    
    except Exception as e:
        return False, f"Verification error: {e}"

def main():
    parser = argparse.ArgumentParser(description="Run secure distributed sensor cluster")
    parser.add_argument("--core-ip", required=True, help="STGen Core IP address")
    parser.add_argument("--core-port", default=5000, type=int)
    parser.add_argument("--node-id", required=True, help="Node identifier")
    parser.add_argument("--sensors", default=1000, type=int)
    parser.add_argument("--protocol", default="mqtt", help="Protocol to use")
    parser.add_argument("--duration", default=300, type=int)
    parser.add_argument("--api-key", help="API key for authentication (optional)")
    
    args = parser.parse_args()
    
    # Generate authentication token
    auth_token = generate_auth_token(args.node_id)
    
    # Build configuration with authentication
    config = {
        "protocol": args.protocol,
        "mode": "active",
        "server_ip": args.core_ip,
        "server_port": args.core_port,
        "num_clients": args.sensors,
        "duration": args.duration,
        "node_id": args.node_id,
        "role": "sensor",
        "sensors": ["temp", "humidity", "motion"],
        
        # Authentication metadata
        "auth_token": auth_token,
        "api_key": args.api_key or "default-key"
    }
    
    config_file = Path(f"node_{args.node_id}_secure_config.json")
    config_file.write_text(json.dumps(config, indent=2))
    
    print(f"🔒 Starting Secure Node {args.node_id}")
    print(f"   Core: {args.core_ip}:{args.core_port}")
    print(f"   Auth Token: {auth_token[:20]}...")
    print(f"   Sensors: {args.sensors}")
    
    # Verify token (demo)
    valid, node = verify_auth_token(auth_token)
    if valid:
        print(f"   ✅ Token verified for node: {node}")
    else:
        print(f"   ❌ Token verification failed: {node}")
        return
    
    # Run STGen with secure config
    subprocess.run([sys.executable, "-m", "stgen.main", str(config_file)])

if __name__ == "__main__":
    main()
