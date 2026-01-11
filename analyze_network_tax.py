#!/usr/bin/env python3
"""
Network Tax Results Analyzer
=============================

Analyzes results from network tax experiments and generates publication-ready
tables for Section 7.3 of the JSA paper.

Usage:
    python analyze_network_tax.py --protocol mqtt
    python analyze_network_tax.py --all
    python analyze_network_tax.py --protocol coap --format latex
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import sys


class NetworkTaxAnalyzer:
    """Analyze and format network tax experiment results."""
    
    def __init__(self, results_dir: str = "results/network_tax"):
        self.results_dir = Path(results_dir)
        if not self.results_dir.exists():
            print(f"Error: Results directory not found: {self.results_dir}")
            sys.exit(1)
    
    def load_results(self, protocol: str) -> Dict:
        """Load the latest results for a protocol."""
        result_file = self.results_dir / f"network_tax_{protocol}_latest.json"
        
        if not result_file.exists():
            print(f"Warning: No results found for {protocol}")
            return None
        
        try:
            return json.loads(result_file.read_text())
        except Exception as e:
            print(f"Error loading {protocol} results: {e}")
            return None
    
    def generate_markdown_table(self, protocol: str, data: Dict) -> str:
        """Generate markdown comparison table."""
        if not data or "scenarios" not in data:
            return f"No data available for {protocol}"
        
        scenarios = data["scenarios"]
        
        # Header
        table = f"\n## Network Tax Analysis: {protocol.upper()}\n\n"
        table += f"**Experiment Date:** {data.get('timestamp', 'N/A')}\n"
        table += f"**Sensors:** {data.get('num_sensors', 'N/A')} | "
        table += f"**Duration:** {data.get('duration', 'N/A')}s\n\n"
        
        # Table
        table += "| Scenario | Deployment | Throughput (msg/s) | Latency p50 (ms) | Latency p95 (ms) | Loss (%) | Network Tax |\n"
        table += "|----------|------------|-------------------:|------------------:|------------------:|----------:|-------------|\n"
        
        for label in ["A", "B", "C"]:
            if label not in scenarios:
                continue
            
            s = scenarios[label]
            
            # Deployment type
            deployment_map = {
                "A": "Localhost",
                "B": "Distributed LAN",
                "C": "WAN Emulated"
            }
            deployment = deployment_map.get(label, "Unknown")
            
            # Metrics
            throughput = f"{s.get('throughput_msg_sec', 0):,.0f}"
            latency_p50 = f"{s.get('latency_p50_ms', 0):.2f}"
            latency_p95 = f"{s.get('latency_p95_ms', 0):.2f}"
            loss = f"{s.get('packet_loss_pct', 0):.2f}"
            
            # Network tax
            if "network_tax" in s:
                tax = s["network_tax"]
                throughput_deg = tax.get("throughput_degradation_pct", 0)
                latency_inc = tax.get("latency_increase_pct", 0)
                network_tax = f"-{throughput_deg:.1f}% / +{latency_inc:.1f}%"
            else:
                network_tax = "Baseline"
            
            table += f"| {label} | {deployment} | {throughput} | {latency_p50} | {latency_p95} | {loss} | {network_tax} |\n"
        
        # Insights
        table += "\n**Network Tax Interpretation:**\n"
        table += "- Format: `-X% throughput / +Y% latency`\n"
        table += "- Negative throughput = performance degradation\n"
        table += "- Positive latency = increased delay\n"
        
        return table
    
    def generate_latex_table(self, protocol: str, data: Dict) -> str:
        """Generate LaTeX table for paper."""
        if not data or "scenarios" not in data:
            return f"% No data available for {protocol}\n"
        
        scenarios = data["scenarios"]
        
        latex = "\\begin{table}[htbp]\n"
        latex += "\\centering\n"
        latex += f"\\caption{{Network Tax Analysis: {protocol.upper()}}}\n"
        latex += f"\\label{{tab:network_tax_{protocol}}}\n"
        latex += "\\begin{tabular}{lllrrrrr}\n"
        latex += "\\toprule\n"
        latex += "Scenario & Deployment & Throughput & Latency & Latency & Loss & \\multicolumn{2}{c}{Network Tax} \\\\\n"
        latex += " & Type & (msg/s) & p50 (ms) & p95 (ms) & (\\%) & Throughput & Latency \\\\\n"
        latex += "\\midrule\n"
        
        for label in ["A", "B", "C"]:
            if label not in scenarios:
                continue
            
            s = scenarios[label]
            
            deployment_map = {
                "A": "Localhost",
                "B": "Distributed LAN",
                "C": "WAN Emulated"
            }
            deployment = deployment_map.get(label, "Unknown")
            
            throughput = f"{s.get('throughput_msg_sec', 0):,.0f}"
            latency_p50 = f"{s.get('latency_p50_ms', 0):.2f}"
            latency_p95 = f"{s.get('latency_p95_ms', 0):.2f}"
            loss = f"{s.get('packet_loss_pct', 0):.2f}"
            
            if "network_tax" in s:
                tax = s["network_tax"]
                throughput_deg = f"-{tax.get('throughput_degradation_pct', 0):.1f}\\%"
                latency_inc = f"+{tax.get('latency_increase_pct', 0):.1f}\\%"
            else:
                throughput_deg = "---"
                latency_inc = "---"
            
            latex += f"{label} & {deployment} & {throughput} & {latency_p50} & {latency_p95} & {loss} & {throughput_deg} & {latency_inc} \\\\\n"
        
        latex += "\\bottomrule\n"
        latex += "\\end{tabular}\n"
        latex += "\\end{table}\n"
        
        return latex
    
    def generate_comparison_table(self, protocols: List[str], format: str = "markdown") -> str:
        """Generate cross-protocol comparison table."""
        all_data = {}
        for protocol in protocols:
            data = self.load_results(protocol)
            if data:
                all_data[protocol] = data
        
        if not all_data:
            return "No data available for any protocol"
        
        if format == "markdown":
            return self._generate_comparison_markdown(all_data)
        else:
            return self._generate_comparison_latex(all_data)
    
    def _generate_comparison_markdown(self, all_data: Dict) -> str:
        """Generate markdown cross-protocol comparison."""
        table = "\n## Cross-Protocol Network Tax Comparison\n\n"
        
        # Scenario A (Localhost)
        table += "### Scenario A: Localhost (Baseline)\n\n"
        table += "| Protocol | Throughput (msg/s) | Latency p50 (ms) | Latency p95 (ms) |\n"
        table += "|----------|-------------------:|------------------:|------------------:|\n"
        
        for protocol, data in sorted(all_data.items()):
            if "A" in data.get("scenarios", {}):
                s = data["scenarios"]["A"]
                throughput = f"{s.get('throughput_msg_sec', 0):,.0f}"
                latency_p50 = f"{s.get('latency_p50_ms', 0):.2f}"
                latency_p95 = f"{s.get('latency_p95_ms', 0):.2f}"
                table += f"| {protocol.upper()} | {throughput} | {latency_p50} | {latency_p95} |\n"
        
        # Scenario B (LAN)
        table += "\n### Scenario B: Distributed LAN (1ms latency)\n\n"
        table += "| Protocol | Throughput (msg/s) | Latency p50 (ms) | Network Tax |\n"
        table += "|----------|-------------------:|------------------:|-------------|\n"
        
        for protocol, data in sorted(all_data.items()):
            if "B" in data.get("scenarios", {}):
                s = data["scenarios"]["B"]
                throughput = f"{s.get('throughput_msg_sec', 0):,.0f}"
                latency_p50 = f"{s.get('latency_p50_ms', 0):.2f}"
                
                if "network_tax" in s:
                    tax = s["network_tax"]
                    network_tax = f"-{tax.get('throughput_degradation_pct', 0):.1f}% / +{tax.get('latency_increase_pct', 0):.1f}%"
                else:
                    network_tax = "N/A"
                
                table += f"| {protocol.upper()} | {throughput} | {latency_p50} | {network_tax} |\n"
        
        # Scenario C (WAN)
        table += "\n### Scenario C: WAN Emulated (150ms latency, 1% loss)\n\n"
        table += "| Protocol | Throughput (msg/s) | Latency p50 (ms) | Network Tax |\n"
        table += "|----------|-------------------:|------------------:|-------------|\n"
        
        for protocol, data in sorted(all_data.items()):
            if "C" in data.get("scenarios", {}):
                s = data["scenarios"]["C"]
                throughput = f"{s.get('throughput_msg_sec', 0):,.0f}"
                latency_p50 = f"{s.get('latency_p50_ms', 0):.2f}"
                
                if "network_tax" in s:
                    tax = s["network_tax"]
                    network_tax = f"-{tax.get('throughput_degradation_pct', 0):.1f}% / +{tax.get('latency_increase_pct', 0):.1f}%"
                else:
                    network_tax = "N/A"
                
                table += f"| {protocol.upper()} | {throughput} | {latency_p50} | {network_tax} |\n"
        
        # Key Insights
        table += "\n### Key Insights for Section 7.3\n\n"
        table += "1. **Baseline Performance (Localhost):** Shows maximum achievable throughput/minimum latency\n"
        table += "2. **LAN Degradation:** Moderate network tax due to 1ms RTT overhead\n"
        table += "3. **WAN Degradation:** Significant tax due to high latency and packet loss\n"
        table += "4. **Protocol Behavior:** \n"
        table += "   - CoAP: Should show retransmission behavior under packet loss\n"
        table += "   - UDP: Will drop packets, showing lower reliability\n"
        table += "   - MQTT: QoS guarantees should maintain delivery despite loss\n"
        table += "   - SRTP: Secure overhead should be consistent across scenarios\n"
        
        return table
    
    def _generate_comparison_latex(self, all_data: Dict) -> str:
        """Generate LaTeX cross-protocol comparison."""
        latex = "\\begin{table*}[htbp]\n"
        latex += "\\centering\n"
        latex += "\\caption{Network Tax Analysis Across Protocols and Deployment Scenarios}\n"
        latex += "\\label{tab:network_tax_comparison}\n"
        latex += "\\begin{tabular}{llrrrrr}\n"
        latex += "\\toprule\n"
        latex += "Protocol & Scenario & Throughput & Latency & Latency & \\multicolumn{2}{c}{Network Tax} \\\\\n"
        latex += " &  & (msg/s) & p50 (ms) & p95 (ms) & Throughput & Latency \\\\\n"
        latex += "\\midrule\n"
        
        for protocol, data in sorted(all_data.items()):
            scenarios = data.get("scenarios", {})
            
            for i, label in enumerate(["A", "B", "C"]):
                if label not in scenarios:
                    continue
                
                s = scenarios[label]
                
                scenario_names = {"A": "Localhost", "B": "LAN", "C": "WAN"}
                scenario_name = scenario_names.get(label, label)
                
                # Only show protocol name for first row
                proto_display = protocol.upper() if i == 0 else ""
                
                throughput = f"{s.get('throughput_msg_sec', 0):,.0f}"
                latency_p50 = f"{s.get('latency_p50_ms', 0):.2f}"
                latency_p95 = f"{s.get('latency_p95_ms', 0):.2f}"
                
                if "network_tax" in s:
                    tax = s["network_tax"]
                    throughput_deg = f"-{tax.get('throughput_degradation_pct', 0):.1f}\\%"
                    latency_inc = f"+{tax.get('latency_increase_pct', 0):.1f}\\%"
                else:
                    throughput_deg = "---"
                    latency_inc = "---"
                
                latex += f"{proto_display} & {scenario_name} & {throughput} & {latency_p50} & {latency_p95} & {throughput_deg} & {latency_inc} \\\\\n"
            
            if protocol != list(all_data.keys())[-1]:
                latex += "\\midrule\n"
        
        latex += "\\bottomrule\n"
        latex += "\\end{tabular}\n"
        latex += "\\end{table*}\n"
        
        return latex


def main():
    parser = argparse.ArgumentParser(
        description="Analyze network tax experiment results",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--protocol",
        choices=["mqtt", "coap", "custom_udp", "srtp"],
        help="Analyze specific protocol"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Analyze all protocols"
    )
    
    parser.add_argument(
        "--format",
        choices=["markdown", "latex"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    
    parser.add_argument(
        "--output",
        help="Save output to file"
    )
    
    parser.add_argument(
        "--results-dir",
        default="results/network_tax",
        help="Results directory (default: results/network_tax)"
    )
    
    args = parser.parse_args()
    
    if not args.protocol and not args.all:
        parser.error("Either --protocol or --all must be specified")
    
    analyzer = NetworkTaxAnalyzer(args.results_dir)
    
    if args.all:
        # Cross-protocol comparison
        protocols = ["mqtt", "coap", "custom_udp", "srtp"]
        output = analyzer.generate_comparison_table(protocols, args.format)
    else:
        # Single protocol analysis
        data = analyzer.load_results(args.protocol)
        if not data:
            print(f"No results found for {args.protocol}")
            return
        
        if args.format == "markdown":
            output = analyzer.generate_markdown_table(args.protocol, data)
        else:
            output = analyzer.generate_latex_table(args.protocol, data)
    
    # Output
    if args.output:
        Path(args.output).write_text(output)
        print(f"Results saved to: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
