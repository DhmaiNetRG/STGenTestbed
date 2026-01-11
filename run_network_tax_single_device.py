#!/usr/bin/env python3
"""
Single-Device Network Tax Experiment
=====================================

Runs the complete network tax experiment on a single machine by:
1. Running all components (clients + server) on localhost
2. Applying network emulation to loopback interface
3. Comparing three scenarios: no emulation, LAN emulation, WAN emulation

This demonstrates the "Network Tax" without requiring multiple physical machines.

Usage:
    python run_network_tax_single_device.py --protocol mqtt --duration 60
    python run_network_tax_single_device.py --all-protocols
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
LOG = logging.getLogger("network_tax_single")


class SingleDeviceNetworkTax:
    """Run network tax experiment on single device using loopback interface."""
    
    def __init__(self, protocol: str, num_sensors: int = 500, duration: int = 60):
        self.protocol = protocol
        self.num_sensors = num_sensors
        self.duration = duration
        self.results_dir = Path("results/network_tax_single_device")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Single device scenarios - all run on localhost with different network conditions
        self.scenarios = [
            {
                "name": "Scenario A: No Emulation (Baseline)",
                "label": "A",
                "description": "Pure localhost, no network emulation",
                "latency_ms": 0,
                "jitter_ms": 0,
                "loss_percent": 0.0,
                "bandwidth_kbps": 0,
                "apply_emulation": False
            },
            {
                "name": "Scenario B: LAN Emulation",
                "label": "B", 
                "description": "1ms latency on localhost",
                "latency_ms": 1,
                "jitter_ms": 0,
                "loss_percent": 0.0,
                "bandwidth_kbps": 1000000,
                "apply_emulation": True
            },
            {
                "name": "Scenario C: WAN Emulation",
                "label": "C",
                "description": "150ms latency + 1% loss on localhost",
                "latency_ms": 150,
                "jitter_ms": 10,
                "loss_percent": 1.0,
                "bandwidth_kbps": 10000,
                "apply_emulation": True
            }
        ]
        
        self.results = {}
    
    def apply_network_emulation(self, scenario: dict):
        """Apply network emulation to loopback interface."""
        if not scenario["apply_emulation"]:
            LOG.info("✓ No emulation (baseline)")
            return
        
        try:
            # Clear existing rules on loopback
            subprocess.run(
                ["sudo", "tc", "qdisc", "del", "dev", "lo", "root"],
                stderr=subprocess.DEVNULL
            )
            
            # Build tc command for loopback interface
            cmd = ["sudo", "tc", "qdisc", "add", "dev", "lo", "root", "netem"]
            
            if scenario["latency_ms"] > 0:
                cmd.extend(["delay", f"{scenario['latency_ms']}ms"])
                if scenario["jitter_ms"] > 0:
                    cmd.append(f"{scenario['jitter_ms']}ms")
            
            if scenario["loss_percent"] > 0:
                cmd.extend(["loss", f"{scenario['loss_percent']}%"])
            
            if scenario["bandwidth_kbps"] > 0:
                cmd.extend(["rate", f"{scenario['bandwidth_kbps']}kbit"])
            
            subprocess.run(cmd, check=True)
            
            LOG.info("✓ Applied network emulation to loopback (lo):")
            LOG.info("  Latency: %dms ± %dms", scenario["latency_ms"], scenario["jitter_ms"])
            LOG.info("  Loss: %.1f%%", scenario["loss_percent"])
            
        except subprocess.CalledProcessError as e:
            LOG.error("Failed to apply network emulation: %s", e)
            LOG.error("Run with sudo or ensure you have CAP_NET_ADMIN capability")
            sys.exit(1)
    
    def clear_network_emulation(self):
        """Remove network emulation from loopback."""
        try:
            subprocess.run(
                ["sudo", "tc", "qdisc", "del", "dev", "lo", "root"],
                stderr=subprocess.DEVNULL,
                check=False
            )
            LOG.info("✓ Cleared network emulation")
        except Exception as e:
            LOG.warning("Could not clear emulation: %s", e)
    
    def run_scenario(self, scenario: dict) -> dict:
        """Run a single scenario."""
        LOG.info("=" * 70)
        LOG.info("Scenario %s: %s", scenario["label"], scenario["name"])
        LOG.info("%s", scenario["description"])
        LOG.info("=" * 70)
        
        # Apply network conditions
        self.apply_network_emulation(scenario)
        
        # Build STGen configuration for localhost
        config_file = self.results_dir / f"config_{scenario['label']}_{self.protocol}.json"
        
        # Protocol-specific default ports
        port_map = {
            "mqtt": 1883,
            "coap": 5683,
            "custom_udp": 5000,
            "srtp": 5004
        }
        
        stgen_config = {
            "protocol": self.protocol,
            "mode": "active",
            "server_ip": "127.0.0.1",  # Localhost
            "server_port": port_map.get(self.protocol, 5000),
            "num_clients": self.num_sensors,
            "duration": self.duration,
            "scenario": scenario["label"],
            "experiment": "network_tax_single_device"
        }
        
        config_file.write_text(json.dumps(stgen_config, indent=2))
        
        LOG.info("Running STGen on localhost with %d sensors for %ds...", 
                 self.num_sensors, self.duration)
        
        # Run STGen
        try:
            start_time = time.time()
            result = subprocess.run(
                [sys.executable, "-m", "stgen.main", str(config_file)],
                capture_output=True,
                text=True,
                timeout=self.duration + 60
            )
            
            elapsed = time.time() - start_time
            
            if result.returncode != 0:
                LOG.error("STGen failed: %s", result.stderr[-500:] if result.stderr else "Unknown error")
                return None
            
            LOG.info("✓ Scenario %s completed in %.1fs", scenario["label"], elapsed)
            
            # Parse results
            metrics = self._parse_results(scenario["label"])
            return metrics
            
        except subprocess.TimeoutExpired:
            LOG.error("Scenario timed out")
            return None
        except Exception as e:
            LOG.error("Error running scenario: %s", e)
            return None
        finally:
            # Always clear emulation after run
            if scenario["apply_emulation"]:
                self.clear_network_emulation()
    
    def _parse_results(self, scenario_label: str) -> dict:
        """Parse results from the most recent run."""
        # Find the most recent result directory
        result_dirs = sorted(
            Path("results").glob(f"{self.protocol}_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not result_dirs:
            LOG.warning("No results found for %s", self.protocol)
            return {}
        
        latest_dir = result_dirs[0]
        metrics_file = latest_dir / "metrics_summary.json"
        
        if not metrics_file.exists():
            LOG.warning("Metrics file not found: %s", metrics_file)
            return {}
        
        try:
            metrics = json.loads(metrics_file.read_text())
            
            return {
                "scenario": scenario_label,
                "throughput_msg_sec": metrics.get("throughput_msg_sec", 0),
                "latency_p50_ms": metrics.get("latency_percentiles", {}).get("p50", 0),
                "latency_p95_ms": metrics.get("latency_percentiles", {}).get("p95", 0),
                "latency_p99_ms": metrics.get("latency_percentiles", {}).get("p99", 0),
                "packet_loss_pct": metrics.get("packet_loss_percent", 0),
                "messages_sent": metrics.get("packets_sent", 0),
                "messages_received": metrics.get("packets_recv", 0),
                "duration_sec": metrics.get("duration_sec", 0),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            LOG.error("Failed to parse metrics: %s", e)
            return {}
    
    def run_all_scenarios(self):
        """Run all three scenarios."""
        LOG.info("=" * 70)
        LOG.info("SINGLE-DEVICE NETWORK TAX EXPERIMENT")
        LOG.info("=" * 70)
        LOG.info("Protocol: %s", self.protocol)
        LOG.info("Sensors: %d", self.num_sensors)
        LOG.info("Duration per scenario: %d seconds", self.duration)
        LOG.info("All traffic: localhost (127.0.0.1)")
        LOG.info("=" * 70)
        
        for i, scenario in enumerate(self.scenarios):
            LOG.info("\n[%d/%d] Starting %s", i+1, len(self.scenarios), scenario["name"])
            
            metrics = self.run_scenario(scenario)
            if metrics:
                self.results[scenario["label"]] = metrics
            
            # Cool-down between scenarios
            if scenario != self.scenarios[-1]:
                LOG.info("Cooling down for 10 seconds...\n")
                time.sleep(10)
        
        # Calculate network tax
        self._calculate_network_tax()
        
        # Save results
        self._save_results()
        
        # Display summary
        self._display_summary()
    
    def _calculate_network_tax(self):
        """Calculate network tax compared to baseline."""
        if "A" not in self.results:
            LOG.warning("Baseline scenario not found")
            return
        
        baseline = self.results["A"]
        baseline_throughput = baseline["throughput_msg_sec"]
        baseline_latency = baseline["latency_p50_ms"]
        
        for label in ["B", "C"]:
            if label in self.results:
                scenario = self.results[label]
                
                # Throughput degradation
                throughput_tax = (
                    (baseline_throughput - scenario["throughput_msg_sec"]) 
                    / baseline_throughput * 100
                ) if baseline_throughput > 0 else 0
                
                # Latency increase
                latency_increase = (
                    (scenario["latency_p50_ms"] - baseline_latency) 
                    / max(baseline_latency, 0.001) * 100
                )
                
                scenario["network_tax"] = {
                    "throughput_degradation_pct": round(throughput_tax, 2),
                    "latency_increase_pct": round(latency_increase, 2)
                }
    
    def _save_results(self):
        """Save consolidated results."""
        output_file = self.results_dir / f"network_tax_{self.protocol}_{int(time.time())}.json"
        
        output = {
            "experiment": "network_tax_single_device",
            "protocol": self.protocol,
            "num_sensors": self.num_sensors,
            "duration": self.duration,
            "timestamp": datetime.now().isoformat(),
            "scenarios": self.results
        }
        
        output_file.write_text(json.dumps(output, indent=2))
        LOG.info("\n✓ Results saved: %s", output_file)
        
        # Also save as latest
        latest_file = self.results_dir / f"network_tax_{self.protocol}_latest.json"
        latest_file.write_text(json.dumps(output, indent=2))
    
    def _display_summary(self):
        """Display results summary table."""
        LOG.info("\n" + "=" * 70)
        LOG.info("RESULTS SUMMARY: %s", self.protocol.upper())
        LOG.info("=" * 70)
        
        print("\n| Scenario | Throughput (msg/s) | Latency p50 (ms) | Network Tax |")
        print("|----------|-------------------:|-----------------:|-------------|")
        
        for label in ["A", "B", "C"]:
            if label not in self.results:
                continue
            
            s = self.results[label]
            scenario_name = {"A": "Baseline", "B": "LAN", "C": "WAN"}[label]
            throughput = f"{s['throughput_msg_sec']:,.0f}"
            latency = f"{s['latency_p50_ms']:.2f}"
            
            if "network_tax" in s:
                tax = s["network_tax"]
                network_tax = f"-{tax['throughput_degradation_pct']:.1f}% / +{tax['latency_increase_pct']:.1f}%"
            else:
                network_tax = "---"
            
            print(f"| {label} ({scenario_name}) | {throughput} | {latency} | {network_tax} |")
        
        print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Single-Device Network Tax Experiment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--protocol",
        choices=["mqtt", "coap", "custom_udp", "srtp"],
        help="Protocol to test"
    )
    
    parser.add_argument(
        "--all-protocols",
        action="store_true",
        help="Run experiment for all protocols"
    )
    
    parser.add_argument(
        "--num-sensors",
        type=int,
        default=500,
        help="Number of simulated sensors (default: 500)"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Test duration in seconds per scenario (default: 60)"
    )
    
    args = parser.parse_args()
    
    if not args.protocol and not args.all_protocols:
        parser.error("Either --protocol or --all-protocols must be specified")
    
    # Check for sudo access
    try:
        result = subprocess.run(["sudo", "-n", "true"], capture_output=True)
        if result.returncode != 0:
            LOG.warning("⚠️  Sudo access required for network emulation")
            LOG.warning("   Run: sudo -v")
            subprocess.run(["sudo", "-v"], check=True)
    except Exception as e:
        LOG.error("Cannot obtain sudo access: %s", e)
        sys.exit(1)
    
    protocols = (
        ["mqtt", "coap", "custom_udp", "srtp"] 
        if args.all_protocols 
        else [args.protocol]
    )
    
    for protocol in protocols:
        LOG.info("\n" + "=" * 70)
        LOG.info("TESTING PROTOCOL: %s", protocol.upper())
        LOG.info("=" * 70)
        
        experiment = SingleDeviceNetworkTax(
            protocol=protocol,
            num_sensors=args.num_sensors,
            duration=args.duration
        )
        
        experiment.run_all_scenarios()
        
        if protocol != protocols[-1]:
            LOG.info("\nWaiting 20 seconds before next protocol...\n")
            time.sleep(20)
    
    LOG.info("\n" + "=" * 70)
    LOG.info("✓ ALL EXPERIMENTS COMPLETED!")
    LOG.info("=" * 70)
    LOG.info("\nResults directory: results/network_tax_single_device/")
    LOG.info("\nTo analyze results:")
    LOG.info("  python analyze_network_tax.py --protocol mqtt --results-dir results/network_tax_single_device")


if __name__ == "__main__":
    main()
