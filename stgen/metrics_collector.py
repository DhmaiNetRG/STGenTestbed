##! @file metrics_collector.py
##! @brief Advanced Metrics Collection and Statistical Analysis
##! 
##! @details
##! Provides efficient real-time metrics collection with:
##! - Latency percentiles (p50, p75, p90, p95, p99)
##! - Throughput and packet loss calculation
##! - Histogram-based distributions
##! - Memory-efficient circular buffers
##! - Real-time aggregation
##!
##! @author STGen Development Team
##! @version 2.0
##! @date 2024

import logging
import time
from typing import Dict, List, Any, Optional
from collections import deque
from dataclasses import dataclass, asdict
import json

_LOG = logging.getLogger("metrics_collector")


@dataclass
class Percentile:
    ##! @struct Percentile
    ##! @brief Container for percentile latency values
    p50: float  ##! Median latency (50th percentile)
    p75: float  ##! 75th percentile
    p90: float  ##! 90th percentile
    p95: float  ##! 95th percentile (SLA threshold)
    p99: float  ##! 99th percentile (tail latency)
    
    def to_dict(self) -> Dict[str, float]:
        ##! @brief Convert to dictionary format
        ##! @return Dictionary representation of percentiles
        return asdict(self)


class HistogramBucket:
    """Efficient histogram with configurable buckets."""
    
    def __init__(self, min_val: float = 0, max_val: float = 1000, num_buckets: int = 100):
        """
        Initialize histogram.
        
        Args:
            min_val: Minimum value
            max_val: Maximum value
            num_buckets: Number of buckets
        """
        self.min_val = min_val
        self.max_val = max_val
        self.num_buckets = num_buckets
        self.buckets = [0] * num_buckets
        self.underflow = 0
        self.overflow = 0
        self.total_count = 0
        self.total_sum = 0.0
        
        self.bucket_width = (max_val - min_val) / num_buckets
    
    def add(self, value: float) -> None:
        """Add value to histogram."""
        self.total_count += 1
        self.total_sum += value
        
        if value < self.min_val:
            self.underflow += 1
            return
        
        if value >= self.max_val:
            self.overflow += 1
            return
        
        bucket_idx = int((value - self.min_val) / self.bucket_width)
        bucket_idx = min(bucket_idx, self.num_buckets - 1)
        self.buckets[bucket_idx] += 1
    
    def percentile(self, p: float) -> float:
        """
        Calculate percentile (0-100).
        
        Args:
            p: Percentile (0-100)
            
        Returns:
            Value at percentile
        """
        if self.total_count == 0:
            return 0.0
        
        target_count = (p / 100.0) * self.total_count
        cumulative = self.underflow
        
        for i, count in enumerate(self.buckets):
            cumulative += count
            if cumulative >= target_count:
                # Linear interpolation within bucket
                bucket_start = self.min_val + i * self.bucket_width
                bucket_end = bucket_start + self.bucket_width
                
                if count == 0:
                    return bucket_start
                
                bucket_fraction = (cumulative - target_count) / count
                return bucket_end - (bucket_fraction * self.bucket_width)
        
        return self.max_val
    
    def mean(self) -> float:
        """Calculate mean."""
        if self.total_count == 0:
            return 0.0
        return self.total_sum / self.total_count
    
    def stats(self) -> Dict[str, Any]:
        """Get histogram statistics."""
        return {
            "count": self.total_count,
            "sum": self.total_sum,
            "mean": self.mean(),
            "min": self.min_val,
            "max": self.max_val,
            "underflow": self.underflow,
            "overflow": self.overflow
        }


class StreamingPercentile:
    """Calculate percentiles on-the-fly with bounded memory (t-digest style)."""
    
    def __init__(self, buffer_size: int = 10000):
        """
        Initialize streaming percentile calculator.
        
        Args:
            buffer_size: Max samples to keep in memory
        """
        self.buffer = deque(maxlen=buffer_size)
        self.sorted_cache = None
        self.cache_valid = False
    
    def add(self, value: float) -> None:
        """Add sample."""
        self.buffer.append(value)
        self.cache_valid = False
    
    def _ensure_sorted(self) -> None:
        """Ensure sorted cache is valid."""
        if not self.cache_valid:
            self.sorted_cache = sorted(self.buffer)
            self.cache_valid = True
    
    def percentile(self, p: float) -> float:
        """
        Calculate percentile.
        
        Args:
            p: Percentile (0-100)
            
        Returns:
            Percentile value
        """
        if len(self.buffer) == 0:
            return 0.0
        
        self._ensure_sorted()
        idx = int((p / 100.0) * len(self.sorted_cache))
        idx = min(max(idx, 0), len(self.sorted_cache) - 1)
        return self.sorted_cache[idx]
    
    def percentiles(self, ps: List[float]) -> Dict[str, float]:
        """Calculate multiple percentiles efficiently."""
        result = {}
        for p in ps:
            result[f"p{int(p)}"] = self.percentile(p)
        return result


class MetricsCollector:
    """Efficient metrics collection for protocol testing."""
    
    def __init__(self, max_samples: int = 100000):
        """
        Initialize metrics collector.
        
        Args:
            max_samples: Maximum samples to keep in memory
        """
        self.max_samples = max_samples
        
        # Latency tracking
        self.latencies = StreamingPercentile(max_samples)
        self.latency_histogram = HistogramBucket(min_val=0, max_val=1000, num_buckets=100)
        
        # Throughput
        self.packets_sent = 0
        self.packets_recv = 0
        self.packets_lost = 0
        
        # Errors
        self.errors: List[str] = []
        self.error_types: Dict[str, int] = {}
        
        # Timing
        self.start_time = time.time()
        self.end_time = None
        
        # Per-client metrics
        self.client_stats: Dict[str, Dict[str, Any]] = {}
        
        _LOG.info("MetricsCollector initialized (max_samples=%d)", max_samples)
    
    def record_latency(self, latency_ms: float, client_id: str = None) -> None:
        """
        Record a latency sample.
        
        Args:
            latency_ms: Latency in milliseconds
            client_id: Optional client identifier
        """
        # Global tracking
        self.latencies.add(latency_ms)
        self.latency_histogram.add(latency_ms)
        
        # Per-client tracking
        if client_id:
            if client_id not in self.client_stats:
                self.client_stats[client_id] = {
                    "latencies": [],
                    "count": 0,
                    "errors": 0
                }
            self.client_stats[client_id]["latencies"].append(latency_ms)
            self.client_stats[client_id]["count"] += 1
    
    def record_send(self) -> None:
        """Record packet sent."""
        self.packets_sent += 1
    
    def record_recv(self) -> None:
        """Record packet received."""
        self.packets_recv += 1
    
    def record_loss(self, count: int = 1) -> None:
        """Record packet loss."""
        self.packets_lost += count
    
    def record_error(self, error_type: str, message: str = "") -> None:
        """
        Record an error.
        
        Args:
            error_type: Type of error
            message: Error message
        """
        self.errors.append(f"{error_type}: {message}")
        self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
    
    def finalize(self) -> None:
        """Finalize collection (call after test completes)."""
        self.end_time = time.time()
    
    def get_latency_percentiles(self) -> Dict[str, float]:
        """Get latency percentiles."""
        return {
            "p50_ms": self.latencies.percentile(50),
            "p75_ms": self.latencies.percentile(75),
            "p90_ms": self.latencies.percentile(90),
            "p95_ms": self.latencies.percentile(95),
            "p99_ms": self.latencies.percentile(99),
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get complete metrics summary."""
        duration = (self.end_time or time.time()) - self.start_time
        loss_rate = 1.0 - (self.packets_recv / max(self.packets_sent, 1))
        
        summary = {
            "duration_sec": duration,
            "sent": self.packets_sent,
            "recv": self.packets_recv,
            "lost": self.packets_lost,
            "loss": loss_rate,
            "throughput_msg_sec": self.packets_recv / max(duration, 1),
            "errors": len(self.errors),
            "error_types": self.error_types,
        }
        
        # Add latency stats
        summary.update(self.get_latency_percentiles())
        
        # Add histogram stats
        summary["latency_histogram"] = self.latency_histogram.stats()
        
        return summary
    
    def get_client_summary(self, client_id: str) -> Dict[str, Any]:
        """Get per-client metrics."""
        if client_id not in self.client_stats:
            return {}
        
        stats = self.client_stats[client_id]
        lats = sorted(stats["latencies"]) if stats["latencies"] else []
        
        result = {
            "client_id": client_id,
            "packet_count": stats["count"],
            "error_count": stats["errors"]
        }
        
        if lats:
            result.update({
                "lat_min_ms": lats[0],
                "lat_max_ms": lats[-1],
                "lat_avg_ms": sum(lats) / len(lats),
                "lat_p50_ms": lats[len(lats) // 2],
                "lat_p95_ms": lats[int(len(lats) * 0.95)],
            })
        
        return result
    
    def export_results(self, filepath: str) -> None:
        """
        Export metrics to JSON.
        
        Args:
            filepath: Output file path
        """
        summary = self.get_summary()
        
        # Add per-client summaries
        summary["client_summaries"] = [
            self.get_client_summary(cid) 
            for cid in sorted(self.client_stats.keys())
        ]
        
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        
        _LOG.info("Metrics exported to %s", filepath)
    
    def print_summary(self) -> None:
        """Print metrics summary to console."""
        summary = self.get_summary()
        
        print("\n" + "=" * 70)
        print("METRICS SUMMARY")
        print("=" * 70)
        print(f"Duration: {summary['duration_sec']:.2f}s")
        print(f"Sent: {summary['sent']}, Received: {summary['recv']}, "
              f"Lost: {summary['lost']} ({summary['loss']*100:.2f}%)")
        print(f"Throughput: {summary['throughput_msg_sec']:.1f} msg/s")
        print(f"Errors: {summary['errors']}")
        
        if summary.get("p50_ms"):
            print(f"\nLatency:")
            print(f"  P50: {summary['p50_ms']:.2f}ms")
            print(f"  P95: {summary['p95_ms']:.2f}ms")
            print(f"  P99: {summary['p99_ms']:.2f}ms")
        
        if summary.get("error_types"):
            print(f"\nError Types: {summary['error_types']}")
        
        print("=" * 70 + "\n")