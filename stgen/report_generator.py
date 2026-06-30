# stgen/report_generator.py
"""
Multi-format Report Generation with Visualizations
Generates HTML, Markdown, JSON, and CSV reports from test results.
"""

import json
import logging
import csv
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

_LOG = logging.getLogger("report_generator")


class ReportGenerator:
    """Generate multi-format reports from test results."""
    
    def __init__(self, results: Dict[str, Any], scenario_name: str = "Unnamed"):
        """
        Initialize report generator.
        
        Args:
            results: Test results dictionary
            scenario_name: Name of scenario tested
        """
        self.results = results
        self.scenario_name = scenario_name
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def generate_html_report(self, filepath: str) -> None:
        """Generate HTML report with embedded charts."""
        html_content = self._build_html()
        Path(filepath).write_text(html_content)
        _LOG.info("HTML report generated: %s", filepath)
    
    def generate_text_report(self, filepath: str) -> None:
        """Generate plain text report for console."""
        text_content = self._build_text()
        Path(filepath).write_text(text_content)
        _LOG.info("Text report generated: %s", filepath)
    
    def generate_markdown_report(self, filepath: str) -> None:
        """Generate Markdown report."""
        md_content = self._build_markdown()
        Path(filepath).write_text(md_content)
        _LOG.info("Markdown report generated: %s", filepath)
    
    def generate_json_report(self, filepath: str) -> None:
        """Generate JSON export."""
        json_data = {
            "metadata": {
                "timestamp": self.timestamp,
                "scenario": self.scenario_name,
                "version": "1.0"
            },
            "results": self.results
        }
        Path(filepath).write_text(json.dumps(json_data, indent=2))
        _LOG.info("JSON report generated: %s", filepath)
    
    def generate_csv_report(self, filepath: str) -> None:
        """Generate CSV export for Excel."""
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value"])
            
            for key, value in self.results.items():
                if isinstance(value, (int, float, str, bool)):
                    writer.writerow([key, value])
                elif isinstance(value, dict) and key == "latency_histogram":
                    for hkey, hval in value.items():
                        writer.writerow([f"latency_histogram.{hkey}", hval])
        
        _LOG.info("CSV report generated: %s", filepath)
    
    def _build_text(self) -> str:
        """Build plain text report."""
        lines = []
        lines.append("=" * 80)
        lines.append(f"STGen Test Report - {self.scenario_name}")
        lines.append(f"Generated: {self.timestamp}")
        lines.append("=" * 80)
        lines.append("")
        
        # Summary metrics
        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Duration: {self.results.get('duration_sec', 0):.2f}s")
        lines.append(f"Packets Sent: {self.results.get('sent', 0)}")
        lines.append(f"Packets Received: {self.results.get('recv', 0)}")
        lines.append(f"Packets Lost: {self.results.get('lost', 0)}")
        lines.append(f"Loss Rate: {self.results.get('loss', 0)*100:.2f}%")
        lines.append(f"Throughput: {self.results.get('throughput_msg_sec', 0):.1f} msg/s")
        lines.append(f"Errors: {self.results.get('errors', 0)}")
        lines.append("")
        
        # Latency metrics
        if self.results.get("p50_ms"):
            lines.append("LATENCY (ms)")
            lines.append("-" * 80)
            lines.append(f"P50: {self.results.get('p50_ms', 0):.2f}")
            lines.append(f"P75: {self.results.get('p75_ms', 0):.2f}")
            lines.append(f"P90: {self.results.get('p90_ms', 0):.2f}")
            lines.append(f"P95: {self.results.get('p95_ms', 0):.2f}")
            lines.append(f"P99: {self.results.get('p99_ms', 0):.2f}")
            lines.append("")
        
        # Error types
        if self.results.get("error_types"):
            lines.append("ERROR TYPES")
            lines.append("-" * 80)
            for err_type, count in self.results["error_types"].items():
                lines.append(f"{err_type}: {count}")
            lines.append("")
        
        lines.append("=" * 80)
        return "\n".join(lines)
    
    def _build_markdown(self) -> str:
        """Build Markdown report."""
        md = []
        md.append(f"# STGen Test Report: {self.scenario_name}\n")
        md.append(f"**Generated:** {self.timestamp}\n")
        
        md.append("## Summary\n")
        md.append(f"- **Duration:** {self.results.get('duration_sec', 0):.2f}s")
        md.append(f"- **Sent:** {self.results.get('sent', 0)}")
        md.append(f"- **Received:** {self.results.get('recv', 0)}")
        md.append(f"- **Lost:** {self.results.get('lost', 0)}")
        md.append(f"- **Loss Rate:** {self.results.get('loss', 0)*100:.2f}%")
        md.append(f"- **Throughput:** {self.results.get('throughput_msg_sec', 0):.1f} msg/s\n")
        
        if self.results.get("p50_ms"):
            md.append("## Latency Percentiles (ms)\n")
            md.append("| Percentile | Latency |")
            md.append("|------------|---------|")
            md.append(f"| P50 | {self.results.get('p50_ms', 0):.2f} |")
            md.append(f"| P75 | {self.results.get('p75_ms', 0):.2f} |")
            md.append(f"| P90 | {self.results.get('p90_ms', 0):.2f} |")
            md.append(f"| P95 | {self.results.get('p95_ms', 0):.2f} |")
            md.append(f"| P99 | {self.results.get('p99_ms', 0):.2f} |\n")
        
        if self.results.get("error_types"):
            md.append("## Errors\n")
            for err_type, count in self.results["error_types"].items():
                md.append(f"- **{err_type}:** {count}")
            md.append("")
        
        return "\n".join(md)
    
    def _build_html(self) -> str:
        """Build HTML report with charts."""
        sent = self.results.get("sent", 0)
        recv = self.results.get("recv", 0)
        loss_pct = self.results.get("loss", 0) * 100
        throughput = self.results.get("throughput_msg_sec", 0)
        lost = max(0, sent - recv)  # clamp — distributed mode can have recv > sent
        
        p50 = self.results.get("p50_ms", 0)
        p95 = self.results.get("p95_ms", 0)
        p99 = self.results.get("p99_ms", 0)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STGen Report - {self.scenario_name}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .header p {{
            font-size: 16px;
            opacity: 0.9;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            border-left: 4px solid #667eea;
        }}
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 8px;
        }}
        .metric-label {{
            font-size: 14px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }}
        .chart-title {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #333;
        }}
        canvas {{
            max-height: 400px;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>STGen Performance Report</h1>
            <p>Scenario: {self.scenario_name} | Generated: {self.timestamp}</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{sent}</div>
                <div class="metric-label">Packets Sent</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{recv}</div>
                <div class="metric-label">Packets Received</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{loss_pct:.2f}%</div>
                <div class="metric-label">Loss Rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{throughput:.1f}</div>
                <div class="metric-label">Msg/sec</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-container">
                <div class="chart-title">Latency Percentiles (ms)</div>
                <canvas id="latencyChart"></canvas>
            </div>
            <div class="chart-container">
                <div class="chart-title">Packet Distribution</div>
                <canvas id="packetChart"></canvas>
            </div>
        </div>
        
        <div class="footer">
            <p>STGen v1.0 | Protocol Benchmark Framework</p>
        </div>
    </div>
    
    <script>
        // Latency chart
        new Chart(document.getElementById('latencyChart'), {{
            type: 'bar',
            data: {{
                labels: ['P50', 'P95', 'P99'],
                datasets: [{{
                    label: 'Latency (ms)',
                    data: [{p50}, {p95}, {p99}],
                    backgroundColor: ['#667eea', '#764ba2', '#f093fb'],
                    borderRadius: 6
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});
        
        // Packet distribution chart
        new Chart(document.getElementById('packetChart'), {{
            type: 'doughnut',
            data: {{
                labels: ['Received', 'Lost'],
                datasets: [{{
                    data: [{recv}, {lost}],
                    backgroundColor: ['#667eea', '#e74c3c']
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom' }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
        return html