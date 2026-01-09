import sys
import json
import logging
import argparse
import subprocess
import shutil
from pathlib import Path
import time
from typing import Dict, Any

# Add current directory to path
sys.path.append(str(Path.cwd()))

from stgen.comparator import ProtocolComparator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

def create_comparison_scenario(node_count=100, duration=10, rate_hz=10.0):
    """Create a temporary scenario file for the comparison."""
    scenario = {
        "name": f"Comparison_{node_count}Nodes",
        "description": "Cross-protocol comparison test",
        "protocol": "placeholder",
        "mode": "active",
        "server_ip": "127.0.0.1",
        "server_port": 5000,
        "num_clients": node_count,
        "duration": duration,
        "sensors": ["temp"],
        "traffic_pattern": {
            "temp": {"rate_hz": rate_hz, "burst": False} 
        }
    }
    
    filename = f"scenario_comparison_{node_count}.json"
    Path(filename).write_text(json.dumps(scenario, indent=2))
    return filename, scenario

def validate_results(results, expected_msg_per_protocol=None):
    """Validate fair comparison."""
    print("\n=== Validation ===")
    valid = True
    
    # Check message counts
    # We expect roughly node_count * 10Hz * duration messages
    if expected_msg_per_protocol:
        EXPECTED = expected_msg_per_protocol
    else:
        # Fallback loose validation
        EXPECTED = 15000
        
    TOLERANCE = 0.5 # 50% tolerance (broad) to allow for overhead
    
    for proto, summary in results.items():
        sent = summary.get("sent", 0)
        print(f"[{proto}] Sent: {sent}")
        
        if sent < EXPECTED * (1 - TOLERANCE):
            print(f"⚠️  WARNING: {proto} sent {sent}, expected ~{EXPECTED}")
            print("   Comparison might be invalid!")
            valid = False
            
    return valid

def calculate_best_protocol(results: Dict[str, Any], use_case: str = "balanced") -> str:
    """Context-aware protocol selection."""
    scores = {}
    
    print("\n=== Context-Aware Recommendation ===")
    print(f"Evaluating for use case: {use_case.upper()}")
    
    for protocol, metrics in results.items():
        score = 0
        loss = float(metrics.get('loss', 0.0)) * 100 # Convert to percentage
        lat_avg = float(metrics.get('lat_avg_ms', 0.0))
        lat_p95 = float(metrics.get('lat_p95_ms', 0.0))
        sent = metrics.get('sent', 0)
        
        if use_case == "critical_data":
            # Reliability matters most
            # Start with 100, subtract penalty for loss (heavy) and latency (light)
            score = 100 - (loss * 10) - (lat_avg * 0.1)
            
        elif use_case == "real_time":
            # Latency matters most
            # Start with 100, subtract penalty for p95 latency and loss
            score = 100 - (lat_p95 * 2) - (loss * 0.5)
            
        elif use_case == "high_throughput":
            # Message rate matters most
            score = (sent / 1000.0) - (lat_avg * 0.1)
        
        else: # Balanced
            score = 100 - (loss * 2) - (lat_avg * 0.5)
            
        scores[protocol] = score
        print(f"  {protocol:<8} Score: {score:.2f} (Loss: {loss:.1f}%, Latency: {lat_avg:.2f}ms)")
    
    best = max(scores, key=scores.get)
    print(f"🏆 Winner for {use_case}: {best}")
    return best

def add_network_impairment(loss_pct=0.5, delay_ms=10, jitter_ms=5):
    """Simulate real WiFi/cellular conditions using tc (Linux).
    
    Note: Localhost testing requires gentler impairment than real networks.
    Real WiFi: 1-5% loss, 50-200ms latency
    Localhost: 0.5-2% loss, 10-50ms latency (to avoid protocol timeouts)
    """
    if shutil.which("tc") is None:
        print("⚠️  'tc' command not found. Skipping network impairment.")
        return False

    print(f"\n⚡ Applying Network Impairment: {loss_pct}% loss, {delay_ms}ms ±{jitter_ms}ms delay")
    print("   (Note: Real-world WiFi typically has 50-200ms latency)")
    try:
        # Clean up any existing rules first
        subprocess.run(
            ["sudo", "tc", "qdisc", "del", "dev", "lo", "root"], 
            stderr=subprocess.DEVNULL, check=False
        )
        
        # Add impairment
        subprocess.run([
            "sudo", "tc", "qdisc", "add", "dev", "lo", "root", "netem",
            "delay", f"{delay_ms}ms", f"{jitter_ms}ms",
            "loss", f"{loss_pct}%"
        ], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Failed to apply network rules (sudo required?): {e}")
        return False

def remove_network_impairment():
    if shutil.which("tc") is None:
        return

    print("\n🧹 Cleaning up network rules...")
    subprocess.run(
        ["sudo", "tc", "qdisc", "del", "dev", "lo", "root"],
        stderr=subprocess.DEVNULL, check=False
    )

def main():
    print("=== STGen Protocol Comparison Experiment (Realistic) ===")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodes", type=int, default=100)
    parser.add_argument("--duration", type=int, default=15)
    parser.add_argument("--impairment", action="store_true", help="Enable network impairment (needs sudo)")
    parser.add_argument("--loss", type=float, default=0.5, help="Packet loss percentage (default: 0.5%)")
    parser.add_argument("--latency", type=int, default=10, help="Additional latency in ms (default: 10ms)")
    parser.add_argument("--jitter", type=int, default=5, help="Latency jitter in ms (default: 5ms)")
    parser.add_argument("--use-case", type=str, default="critical_data", 
                        choices=["critical_data", "real_time", "high_throughput", "balanced"])
    args = parser.parse_args()
    
    # Setup
    protocols = ["mqtt", "coap", "my_udp"]
    
    print(f"Generating scenario for {args.nodes} nodes, {args.duration}s duration...")
    scenario_file, config = create_comparison_scenario(args.nodes, args.duration)
    
    # Apply Network Conditions
    impairment_active = False
    if args.impairment:
        impairment_active = add_network_impairment(args.loss, args.latency, args.jitter)
    
    # Run Comparison
    print(f"Running comparison for: {', '.join(protocols)}")
    comparator = ProtocolComparator(scenario_file, protocols)
    
    results = {}
    try:
        results = comparator.run_comparison()
    except Exception as e:
        print(f"Error during comparison: {e}")
    finally:
        # Always cleanup network rules
        if impairment_active:
            remove_network_impairment()
    
    # Validation & Analysis
    expected = args.nodes * 10 * args.duration # 10Hz hardcoded in scenario creation
    validate_results(results, expected)
    
    print("\n=== Results Analysis ===")
    comparator.generate_report(f"comparison_report_realistic_{args.nodes}_nodes.txt")
    
    # Best Protocol Selection
    calculate_best_protocol(results, args.use_case)

    # Cleanup
    if Path(scenario_file).exists():
        Path(scenario_file).unlink()

if __name__ == "__main__":
    main()
