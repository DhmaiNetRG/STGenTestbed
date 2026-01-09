
#!/usr/bin/env python3
"""Generate publication-quality graphs from STGen test results."""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple
import re

try:
    import matplotlib.pyplot as plt
    import matplotlib
    import numpy as np
    # Use a professional style with readable text
    plt.style.use('seaborn-v0_8-paper')
    matplotlib.rcParams['font.size'] = 14
    matplotlib.rcParams['axes.labelsize'] = 16
    matplotlib.rcParams['axes.titlesize'] = 18
    matplotlib.rcParams['xtick.labelsize'] = 14
    matplotlib.rcParams['ytick.labelsize'] = 14
    matplotlib.rcParams['legend.fontsize'] = 13
    matplotlib.rcParams['figure.dpi'] = 300
    matplotlib.rcParams['font.weight'] = 'normal'
    matplotlib.rcParams['axes.labelweight'] = 'bold'
    matplotlib.rcParams['axes.titleweight'] = 'bold'
except ImportError:
    print("Error: matplotlib and numpy required")
    print("Install with: pip install matplotlib numpy")
    sys.exit(1)


def load_results(result_dir: str) -> Dict[str, Any]:
    """Load results from directory."""
    summary_file = Path(result_dir) / "summary.json"
    
    if not summary_file.exists():
        raise FileNotFoundError(f"No summary.json in {result_dir}")
    
    return json.loads(summary_file.read_text())


def load_latencies(result_dir: str) -> List[float]:
    """Load latency data from file."""
    lat_file = Path(result_dir) / "latencies.txt"
    
    if not lat_file.exists():
        return []
    
    latencies = []
    for line in lat_file.read_text().splitlines():
        try:
            latencies.append(float(line.strip()))
        except:
            pass
    
    return latencies


def find_protocol_results(results_dir: Path, protocols: List[str] = None) -> Dict[str, Path]:
    """Find latest results for each protocol."""
    if protocols is None:
        protocols = ["mqtt", "coap", "my_udp"]
    
    protocol_dirs = {}
    
    for protocol in protocols:
        # Find all directories for this protocol
        dirs = sorted(results_dir.glob(f"{protocol}_*"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if dirs:
            protocol_dirs[protocol] = dirs[0]  # Most recent
    
    return protocol_dirs


def plot_latency_comparison(protocol_results: Dict[str, Dict], output_file: str) -> None:
    """Generate bar chart comparing latency metrics - optimized for single column."""
    protocols = list(protocol_results.keys())
    metrics = ['lat_avg_ms', 'lat_p50_ms', 'lat_p95_ms']
    metric_labels = ['Average', 'Median (p50)', '95th Percentile']
    
    x = np.arange(len(protocols))
    width = 0.25
    
    # Single column width: 3.5 inches, taller for readability
    fig, ax = plt.subplots(figsize=(3.5, 4.5))
    
    colors = ['#3498db', '#2ecc71', '#e74c3c']
    
    for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
        values = [protocol_results[p].get(metric, 0) for p in protocols]
        ax.bar(x + i * width, values, width, label=label, color=colors[i], alpha=0.8, edgecolor='black', linewidth=0.5)
    
    ax.set_ylabel('Latency (ms)', fontsize=11, fontweight='bold')
    ax.set_xlabel('Protocol', fontsize=11, fontweight='bold')
    ax.set_title('Protocol Latency Comparison', fontsize=12, fontweight='bold', pad=10)
    ax.set_xticks(x + width)
    ax.set_xticklabels([p.upper() for p in protocols], fontsize=10, fontweight='bold')
    
    # Improve tick labels
    ax.tick_params(axis='y', labelsize=10)
    ax.tick_params(axis='x', labelsize=10)
    
    # Legend with smaller font, positioned to avoid overlap
    ax.legend(fontsize=8, framealpha=0.9, loc='best')
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    
    # Tighter layout with more padding
    plt.tight_layout(pad=0.5)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def plot_throughput_comparison(protocol_results: Dict[str, Dict], duration: int, output_file: str) -> None:
    """Generate bar chart comparing message throughput."""
    protocols = list(protocol_results.keys())
    
    sent = [protocol_results[p].get('sent', 0) for p in protocols]
    recv = [protocol_results[p].get('recv', 0) for p in protocols]
    throughput = [s / duration for s in sent]  # Messages per second
    
    x = np.arange(len(protocols))
    width = 0.35
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    # Messages sent/received
    ax1.bar(x - width/2, sent, width, label='Sent', color='#3498db', alpha=0.8)
    ax1.bar(x + width/2, recv, width, label='Received', color='#2ecc71', alpha=0.8)
    ax1.set_ylabel('Message Count')
    ax1.set_xlabel('Protocol')
    ax1.set_title('Message Delivery')
    ax1.set_xticks(x)
    ax1.set_xticklabels([p.upper() for p in protocols], fontsize=15)
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Throughput
    ax2.bar(x, throughput, color='#9b59b6', alpha=0.8)
    ax2.set_ylabel('Throughput (msg/s)')
    ax2.set_xlabel('Protocol')
    ax2.set_title('Message Throughput')
    ax2.set_xticks(x)
    ax2.set_xticklabels([p.upper() for p in protocols], fontsize=15)
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def plot_latency_cdf(protocol_dirs: Dict[str, Path], output_file: str) -> None:
    """Generate CDF plot for latency distribution."""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    colors = {'mqtt': '#3498db', 'coap': '#2ecc71', 'my_udp': '#e74c3c'}
    
    for protocol, result_dir in protocol_dirs.items():
        latencies = load_latencies(result_dir)
        
        if not latencies:
            print(f"Warning: No latency data for {protocol}")
            continue
        
        latencies_sorted = np.sort(latencies)
        cdf = np.arange(1, len(latencies_sorted) + 1) / len(latencies_sorted)
        
        ax.plot(latencies_sorted, cdf, label=protocol.upper(), 
                color=colors.get(protocol, '#34495e'), linewidth=2.5)
    
    ax.set_xlabel('Latency (ms)')
    ax.set_ylabel('Cumulative Probability')
    ax.set_title('Latency CDF Comparison')
    ax.legend()
    ax.grid(alpha=0.3, linestyle='--')
    ax.set_xlim(left=0)
    ax.set_ylim([0, 1])
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def plot_latency_boxplot(protocol_dirs: Dict[str, Path], output_file: str) -> None:
    """Generate boxplot for latency distribution."""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    data = []
    labels = []
    
    for protocol, result_dir in sorted(protocol_dirs.items()):
        latencies = load_latencies(result_dir)
        
        if latencies:
            data.append(latencies)
            labels.append(protocol.upper())
    
    if not data:
        print("Warning: No latency data available")
        return
    
    bp = ax.boxplot(data, labels=labels, patch_artist=True, 
                    showmeans=True, meanline=True)
    
    # Color the boxes
    colors = ['#3498db', '#2ecc71', '#e74c3c']
    for patch, color in zip(bp['boxes'], colors[:len(data)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    
    # Make box plot labels larger
    ax.tick_params(axis='x', labelsize=15)
    
    ax.set_ylabel('Latency (ms)')
    ax.set_xlabel('Protocol')
    ax.set_title('Latency Distribution')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def plot_reliability_metrics(protocol_results: Dict[str, Dict], output_file: str) -> None:
    """Generate reliability comparison (loss rate, errors)."""
    protocols = list(protocol_results.keys())
    
    loss_rates = [protocol_results[p].get('loss', 0) * 100 for p in protocols]  # Convert to %
    error_counts = [protocol_results[p].get('errors', 0) for p in protocols]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    x = np.arange(len(protocols))
    
    # Packet loss
    ax1.bar(x, loss_rates, color='#e74c3c', alpha=0.8)
    ax1.set_ylabel('Packet Loss (%)')
    ax1.set_xlabel('Protocol')
    ax1.set_title('Packet Loss Rate')
    ax1.set_xticks(x)
    ax1.set_xticklabels([p.upper() for p in protocols], fontsize=15)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    ax1.set_ylim([0, max(loss_rates) * 1.2 if max(loss_rates) > 0 else 1])
    
    # Error count
    ax2.bar(x, error_counts, color='#f39c12', alpha=0.8)
    ax2.set_ylabel('Error Count')
    ax2.set_xlabel('Protocol')
    ax2.set_title('Protocol Errors')
    ax2.set_xticks(x)
    ax2.set_xticklabels([p.upper() for p in protocols], fontsize=15)
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def generate_all_graphs(results_dir: Path, output_dir: Path, protocols: List[str] = None, duration: int = 15):
    """Generate all publication graphs."""
    print(f"\n📊 Generating graphs from {results_dir}...")
    
    # Find protocol results
    protocol_dirs = find_protocol_results(results_dir, protocols)
    
    if not protocol_dirs:
        print("Error: No protocol results found")
        return
    
    print(f"Found results for: {', '.join(protocol_dirs.keys())}")
    
    # Load summaries
    protocol_results = {}
    for protocol, result_dir in protocol_dirs.items():
        try:
            protocol_results[protocol] = load_results(str(result_dir))
        except Exception as e:
            print(f"Warning: Could not load {protocol}: {e}")
    
    if not protocol_results:
        print("Error: Could not load any results")
        return
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate graphs
    try:
        plot_latency_comparison(protocol_results, str(output_dir / "latency_comparison.pdf"))
    except Exception as e:
        print(f"Error creating latency comparison: {e}")
    
    try:
        plot_throughput_comparison(protocol_results, duration, str(output_dir / "throughput_comparison.pdf"))
    except Exception as e:
        print(f"Error creating throughput comparison: {e}")
    
    try:
        plot_latency_cdf(protocol_dirs, str(output_dir / "latency_cdf.pdf"))
    except Exception as e:
        print(f"Error creating CDF: {e}")
    
    try:
        plot_latency_boxplot(protocol_dirs, str(output_dir / "latency_boxplot.pdf"))
    except Exception as e:
        print(f"Error creating boxplot: {e}")
    
    try:
        plot_reliability_metrics(protocol_results, str(output_dir / "reliability_comparison.pdf"))
    except Exception as e:
        print(f"Error creating reliability comparison: {e}")
    
    print(f"\n✅ All graphs saved to {output_dir}/")


def main():
    parser = argparse.ArgumentParser(description="Generate graphs from STGen results")
    parser.add_argument("--results", "-r", type=str, default="results",
                       help="Results directory (default: results)")
    parser.add_argument("--output", "-o", type=str, default="paper/figures",
                       help="Output directory (default: paper/figures)")
    parser.add_argument("--protocols", "-p", type=str, default=None,
                       help="Comma-separated protocol list (default: mqtt,coap,my_udp)")
    parser.add_argument("--duration", "-d", type=int, default=15,
                       help="Test duration for throughput calculation (default: 15s)")
    
    args = parser.parse_args()
    
    results_dir = Path(args.results)
    output_dir = Path(args.output)
    
    protocols = None
    if args.protocols:
        protocols = [p.strip() for p in args.protocols.split(',')]
    
    if not results_dir.exists():
        print(f"Error: Results directory not found: {results_dir}")
        sys.exit(1)
    
    generate_all_graphs(results_dir, output_dir, protocols, args.duration)


if __name__ == "__main__":
    main()
    fig, axes = plt.subplots