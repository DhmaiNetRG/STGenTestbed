#!/usr/bin/env python3
"""
Network Tax Experiment Runner for Section 7.3
==============================================

Demonstrates that STGen's distributed deployment adheres to network profiles
by measuring performance degradation across three scenarios:

- Scenario A (Localhost): Baseline performance with minimal network overhead
- Scenario B (Distributed LAN): LAN deployment with 1ms latency
- Scenario C (WAN Emulated): High-latency WAN with packet loss and bandwidth limits

The "Network Tax" shows the percentage degradation in throughput and increase
in latency compared to the localhost baseline.

Usage:
    python run_network_tax_experiment.py --protocol mqtt --duration 60
    python run_network_tax_experiment.py --protocol coap --num-sensors 1000
    python run_network_tax_experiment.py --all-protocols
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
LOG = logging.getLogger("network_tax")


class NetworkTaxExperiment:
    """Orchestrates network tax experiments across three scenarios."""
    
    def __init__(self, protocol: str, num_sensors: int = 500, duration: int = 60):
        """
        Initialize experiment.
        
        Args:
            protocol: Protocol to test (mqtt, coap, custom_udp, srtp)
            num_sensors: Number of simulated sensors
            duration: Test duration in seconds
        """
        self.protocol = protocol
        self.num_sensors = num_sensors
        self.duration = duration
        self.results_dir = Path("results/network_tax")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.scenarios = [
            {
                "name": "Localhost",
                "label": "A",
                "profile": "configs/network_conditions/localhost.json",
                "description": "Baseline: Local deployment"
            },
            {
                "name": "Distributed LAN",
                "label": "B",
                "profile": "configs/network_conditions/distributed_lan.json",
                "description": "LAN: 1ms latency, gigabit bandwidth"
            },
            {
                "name": "WAN Emulated",
                "label": "C",
                "profile": "configs/network_conditions/wan_emulated.json",
                "description": "WAN: 150ms latency, 10Mbps, 1% loss"
            }
        ]
        
        self.results = {}
    
    def run_scenario(self, scenario: dict) -> dict:
        """
        Run a single scenario.
        
        Args:
            scenario: Scenario configuration
            
        Returns:
            Dictionary with metrics
        """
        LOG.info("=" * 70)
        LOG.info("Scenario %s: %s", scenario["label"], scenario["name"])
        LOG.info("%s", scenario["description"])
        LOG.info("=" * 70)
        
        # Load network profile
        profile_path = Path(scenario["profile"])
        if not profile_path.exists():
            LOG.error("Profile not found: %s", profile_path)
            return None
        
        profile = json.loads(profile_path.read_text())
        
        # Build STGen configuration
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
            "server_ip": "127.0.0.1",
            "server_port": port_map.get(self.protocol, 5000),
            "num_clients": self.num_sensors,
            "duration": self.duration,
            "network_profile": str(profile_path.resolve()),
            "scenario": scenario["label"],
            "experiment": "network_tax"
        }
        
        config_file.write_text(json.dumps(stgen_config, indent=2))
        
        LOG.info("Running STGen with profile: %s", profile["name"])
        LOG.info("  Latency: %dms ± %dms", profile["latency_ms"], profile["jitter_ms"])
        LOG.info("  Packet Loss: %.1f%%", profile["loss_percent"])
        LOG.info("  Bandwidth: %d kbps", profile["bandwidth_kbps"])
        
        # Run STGen
        try:
            result = subprocess.run(
                [sys.executable, "-m", "stgen.main", str(config_file)],
                capture_output=True,
                text=True,
                timeout=self.duration + 60
            )
            
            if result.returncode != 0:
                LOG.error("STGen failed: %s", result.stderr)
                return None
            
            LOG.info("✓ Scenario %s completed", scenario["label"])
            
            # Find and parse results
            metrics = self._parse_results(scenario["label"])
            return metrics
            
        except subprocess.TimeoutExpired:
            LOG.error("Scenario timed out")
            return None
        except Exception as e:
            LOG.error("Error running scenario: %s", e)
            return None
    
    def _parse_results(self, scenario_label: str) -> dict:
        """
        Parse results from the most recent run.
        
        Args:
            scenario_label: Scenario identifier (A, B, C)
            
        Returns:
            Dictionary with parsed metrics
        """
        # Find the most recent result directory for this protocol
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
            
            # Extract key metrics
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
        """Run all three scenarios and collect results."""
        LOG.info("Starting Network Tax Experiment")
        LOG.info("Protocol: %s", self.protocol)
        LOG.info("Sensors: %d", self.num_sensors)
        LOG.info("Duration: %d seconds", self.duration)
        
        for scenario in self.scenarios:
            metrics = self.run_scenario(scenario)
            if metrics:
                self.results[scenario["label"]] = metrics
            
            # Cool-down period between tests
            if scenario != self.scenarios[-1]:
                LOG.info("Cooling down for 10 seconds...")
                time.sleep(10)
        
        # Calculate network tax
        self._calculate_network_tax()
        
        # Save consolidated results
        self._save_results()
    
    def _calculate_network_tax(self):
        """Calculate the network tax (performance degradation)."""
        if "A" not in self.results:
            LOG.warning("Baseline scenario (A) not found, cannot calculate network tax")
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
                    / baseline_latency * 100
                ) if baseline_latency > 0 else 0
                
                scenario["network_tax"] = {
                    "throughput_degradation_pct": round(throughput_tax, 2),
                    "latency_increase_pct": round(latency_increase, 2)
                }
                
                LOG.info("Scenario %s Network Tax:", label)
                LOG.info("  Throughput degradation: %.2f%%", throughput_tax)
                LOG.info("  Latency increase: %.2f%%", latency_increase)
    
    def _save_results(self):
        """Save consolidated results to JSON."""
        output_file = self.results_dir / f"network_tax_{self.protocol}_{int(time.time())}.json"
        
        output = {
            "experiment": "network_tax",
            "protocol": self.protocol,
            "num_sensors": self.num_sensors,
            "duration": self.duration,
            "timestamp": datetime.now().isoformat(),
            "scenarios": self.results
        }
        
        output_file.write_text(json.dumps(output, indent=2))
        LOG.info("Results saved to: %s", output_file)
        
        # Also save as latest
        latest_file = self.results_dir / f"network_tax_{self.protocol}_latest.json"
        latest_file.write_text(json.dumps(output, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Network Tax Experiment for STGen Section 7.3",
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
        help="Test duration in seconds (default: 60)"
    )
    
    args = parser.parse_args()
    
    if not args.protocol and not args.all_protocols:
        parser.error("Either --protocol or --all-protocols must be specified")
    
    protocols = (
        ["mqtt", "coap", "custom_udp", "srtp"] 
        if args.all_protocols 
        else [args.protocol]
    )
    
    for protocol in protocols:
        LOG.info("")
        LOG.info("=" * 70)
        LOG.info("TESTING PROTOCOL: %s", protocol.upper())
        LOG.info("=" * 70)
        
        experiment = NetworkTaxExperiment(
            protocol=protocol,
            num_sensors=args.num_sensors,
            duration=args.duration
        )
        
        experiment.run_all_scenarios()
        
        if protocol != protocols[-1]:
            LOG.info("Waiting 30 seconds before next protocol...")
            time.sleep(30)
    
    LOG.info("")
    LOG.info("All experiments completed!")
    LOG.info("Results saved in: results/network_tax/")


if __name__ == "__main__":
    main()
