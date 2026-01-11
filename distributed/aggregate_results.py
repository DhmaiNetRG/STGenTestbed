#!/usr/bin/env python3
"""
Aggregate results from multiple distributed nodes.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
import statistics

def aggregate_results(result_dirs: List[Path]) -> Dict[str, Any]:
    """Combine results from multiple nodes."""
    
    all_results = []
    total_sent = 0
    total_recv = 0
    all_latencies = []
    
    for result_dir in result_dirs:
        summary_file = result_dir / "summary.json"
        if not summary_file.exists():
            continue
        
        data = json.loads(summary_file.read_text())
        all_results.append(data)
        
        total_sent += data.get("sent", 0)
        total_recv += data.get("recv", 0)
        
        # Load latencies
        lat_file = result_dir / "latencies.txt"
        if lat_file.exists():
            lats = [float(x) for x in lat_file.read_text().splitlines()]
            all_latencies.extend(lats)
    
    # Compute aggregate statistics
    all_latencies.sort()
    
    aggregate = {
        "num_nodes": len(all_results),
        "total_sent": total_sent,
        "total_recv": total_recv,
        "loss": 1.0 - (total_recv / max(total_sent, 1)),
        "per_node_results": all_results
    }
    
    if all_latencies:
        aggregate.update({
            "lat_avg_ms": statistics.mean(all_latencies),
            "lat_median_ms": statistics.median(all_latencies),
            "lat_p95_ms": all_latencies[int(len(all_latencies) * 0.95)],
            "lat_p99_ms": all_latencies[int(len(all_latencies) * 0.99)],
            "lat_min_ms": min(all_latencies),
            "lat_max_ms": max(all_latencies)
        })
    
    return aggregate

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Aggregate distributed results")
    parser.add_argument("result_dirs", nargs="+", help="Result directories from each node")
    parser.add_argument("--output", default="aggregate_results.json")
    
    args = parser.parse_args()
    
    result_dirs = [Path(d) for d in args.result_dirs]
    aggregate = aggregate_results(result_dirs)
    
    # Save
    Path(args.output).write_text(json.dumps(aggregate, indent=2))
    
    # Print summary
    print("\n" + "=" * 70)
    print("DISTRIBUTED DEPLOYMENT SUMMARY")
    print("=" * 70)
    print(f"Nodes: {aggregate['num_nodes']}")
    print(f"Total Sent: {aggregate['total_sent']}")
    print(f"Total Received: {aggregate['total_recv']}")
    print(f"Packet Loss: {aggregate['loss']*100:.2f}%")
    
    if "lat_avg_ms" in aggregate:
        print(f"\nLatency:")
        print(f"  Average: {aggregate['lat_avg_ms']:.2f}ms")
        print(f"  Median:  {aggregate['lat_median_ms']:.2f}ms")
        print(f"  P95:     {aggregate['lat_p95_ms']:.2f}ms")
        print(f"  P99:     {aggregate['lat_p99_ms']:.2f}ms")
    
    print(f"\nFull report saved to: {args.output}")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()