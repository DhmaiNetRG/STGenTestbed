# stgen/comparator.py
"""
Protocol Comparison Framework
Runs multiple protocols on the same workload and generates comparative reports.
"""

import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any
import subprocess
import sys

_LOG = logging.getLogger("stgen.compare")


class ProtocolComparator:
    """Compare multiple protocols on identical workloads."""
    
    def __init__(self, scenario_file: str, protocols: List[str]):
        """
        Initialize comparator.
        
        Args:
            scenario_file: Path to scenario config
            protocols: List of protocol names to compare
        """
        self.scenario = json.loads(Path(scenario_file).read_text())
        self.protocols = protocols
        self.results: Dict[str, Dict] = {}
        
        _LOG.info("Comparing protocols: %s on scenario: %s", 
                  protocols, self.scenario.get("name", "unknown"))
    
    def run_comparison(self) -> Dict[str, Any]:
        """
        Run all protocols on the same scenario.
        
        Returns:
            Dict mapping protocol name to results
        """
        for protocol in self.protocols:
            _LOG.info("=" * 60)
            _LOG.info("Testing protocol: %s", protocol)
            _LOG.info("=" * 60)
            
            # Create temporary config
            cfg = self.scenario.copy()
            cfg["protocol"] = protocol
            
            temp_config = Path(f"temp_{protocol}_config.json")
            temp_config.write_text(json.dumps(cfg, indent=2))
            
            # Run test
            try:
                subprocess.run(
                    [sys.executable, "-m", "stgen.main", str(temp_config)],
                    check=True
                )
                
                # Load results
                result_dirs = sorted(Path("results").glob(f"{protocol}_*"))
                if result_dirs:
                    latest = result_dirs[-1]
                    summary = json.loads((latest / "summary.json").read_text())
                    self.results[protocol] = summary
                    _LOG.info(" %s test completed", protocol)
                else:
                    _LOG.error(" No results found for %s", protocol)
                    
            except subprocess.CalledProcessError as e:
                _LOG.error(" %s test failed: %s", protocol, e)
            finally:
                temp_config.unlink(missing_ok=True)
            
            time.sleep(2)  # Cool-down between tests
        
        return self.results
    
    def generate_report(self, output_file: str = "comparison_report.txt") -> None:
        """
        Generate comparison report.
        
        Args:
            output_file: Where to save the report
        """
        if not self.results:
            _LOG.error("No results to compare")
            return
        
        report = []
        report.append("=" * 80)
        report.append(f"PROTOCOL COMPARISON REPORT")
        report.append(f"Scenario: {self.scenario.get('name', 'Unknown')}")
        report.append(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        report.append("")
        
        # Extract metrics
        metrics = ["sent", "recv", "loss", "lat_avg_ms", "lat_p50_ms", "lat_p95_ms", "lat_p99_ms"]
        
        # Find baseline (first protocol)
        baseline_name = self.protocols[0]
        baseline = self.results.get(baseline_name, {})
        
        # Build header line
        header = f"{'Metric':<25} {baseline_name:<15}"
        for proto in self.protocols[1:]:
            header += f" {proto:<15} Δ vs {baseline_name:<10}"
        report.append(header)
        report.append("-" * 80)
        
        for metric in metrics:
            if metric not in baseline:
                continue
            
            line = f"{metric:<25} "
            baseline_val = baseline[metric]
            
            # Format baseline value
            if "loss" in metric:
                line += f"{baseline_val*100:>6.2f}%     "
            elif "lat" in metric or "ms" in metric:
                line += f"{baseline_val:>6.2f}ms    "
            else:
                line += f"{baseline_val:>6.0f}        "
            
            # Compare with other protocols
            for proto in self.protocols[1:]:
                proto_val = self.results.get(proto, {}).get(metric, 0)
                
                # Calculate delta
                if baseline_val > 0:
                    delta_pct = ((proto_val - baseline_val) / baseline_val) * 100
                else:
                    delta_pct = 0
                
                # Format value
                if "loss" in metric:
                    line += f"{proto_val*100:>6.2f}%  "
                elif "lat" in metric or "ms" in metric:
                    line += f"{proto_val:>6.2f}ms "
                else:
                    line += f"{proto_val:>6.0f}     "
                
                # Format delta with direction
                if "lat" in metric:
                    # Lower latency is better
                    symbol = "↓" if delta_pct < 0 else "↑"
                elif "loss" in metric:
                    # Lower loss is better
                    symbol = "↓" if delta_pct < 0 else "↑"
                else:
                    # Higher throughput is better
                    symbol = "↑" if delta_pct > 0 else "↓"
                
                line += f"{delta_pct:>+6.1f}% {symbol}  "
            
            report.append(line)
        
        report.append("")
        report.append("=" * 80)
        report.append("SUMMARY")
        report.append("=" * 80)
        
        # Determine winner
        winner = self._determine_winner()
        report.append(f"\n Best Overall: {winner['protocol']}")
        report.append(f"   Reason: {winner['reason']}")
        
        # Save report
        report_text = "\n".join(report)
        Path(output_file).write_text(report_text)
        _LOG.info("Report saved to: %s", output_file)
        print(report_text)
    
    def _determine_winner(self) -> Dict[str, str]:
        """
        Determine which protocol performed best.
        
        Returns:
            Dict with winner info
        """
        # Simple scoring: lower latency + lower loss = better
        scores = {}
        
        for proto, results in self.results.items():
            score = 0
            
            # Penalize high latency
            if "lat_p95_ms" in results:
                score -= results["lat_p95_ms"]
            
            # Penalize packet loss
            if "loss" in results:
                score -= results["loss"] * 1000
            
            # Reward throughput (messages delivered)
            if "recv" in results:
                score += results["recv"]
            
            scores[proto] = score
        
        if scores:
            winner_proto = max(scores, key=scores.get)
            return {
                "protocol": winner_proto,
                "reason": f"Lowest latency ({self.results[winner_proto].get('lat_p95_ms', 0):.2f}ms) and loss ({self.results[winner_proto].get('loss', 0)*100:.1f}%)"
            }
        
        return {"protocol": "Unknown", "reason": "No results"}


def main():
    """CLI for comparison tool."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare IoT protocols")
    parser.add_argument("--scenario", required=True, help="Scenario config file")
    parser.add_argument("--protocols", required=True, help="Comma-separated protocol names")
    parser.add_argument("--output", default="comparison_report.txt", help="Output file")
    
    args = parser.parse_args()
    
    protocols = [p.strip() for p in args.protocols.split(",")]
    
    comparator = ProtocolComparator(args.scenario, protocols)
    comparator.run_comparison()
    comparator.generate_report(args.output)


if __name__ == "__main__":
    main()