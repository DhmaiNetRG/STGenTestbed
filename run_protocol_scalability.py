#!/usr/bin/env python3
"""
Protocol scalability sweep.

For each protocol (custom_udp, mqtt, coap) and node count, runs the STGen
orchestrator in active mode on the loopback interface and records:
  - throughput (recv/s), loss, P50/P95/P99 end-to-end latency  (from summary.json)
  - peak resident memory of the run's process tree (sampled by this driver)

Loopback isolates framework + broker queuing from network transit, which is the
"does the orchestrator add queuing delay at scale" question. Repeats each point
and reports per-point raw values; aggregation (mean +/- std) is done at the end.
"""
import json
import time
import subprocess
import sys
import statistics
from pathlib import Path

import psutil

PROTOCOLS = ["custom_udp", "mqtt", "coap"]
NODE_COUNTS = [100, 250, 500]
DURATION = 10          # seconds of traffic per run
RATE_HZ = 10.0         # per-node publish rate
REPS = 3
PORT = {"custom_udp": 5000, "mqtt": 5000, "coap": 5683}
OUT = Path("results/protocol_scalability.json")


def peak_rss_tree(pid):
    """Return current RSS (MB) of process pid plus all its children."""
    try:
        p = psutil.Process(pid)
        procs = [p] + p.children(recursive=True)
        return sum(q.memory_info().rss for q in procs if q.is_running()) / 1e6
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0.0


def run_once(protocol, nodes):
    cfg = {
        "name": f"scal_{protocol}_{nodes}",
        "protocol": protocol,
        "mode": "active",
        "server_ip": "127.0.0.1",
        "server_port": PORT[protocol],
        "num_clients": nodes,
        "duration": DURATION,
        "sensors": ["temp"],
        "traffic_pattern": {"temp": {"rate_hz": RATE_HZ, "burst": False}},
    }
    cfg_path = Path(f"scal_{protocol}_{nodes}.json")
    cfg_path.write_text(json.dumps(cfg))

    t0 = time.perf_counter()
    proc = subprocess.Popen(
        [sys.executable, "-m", "stgen.main", str(cfg_path)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    peak_mb = 0.0
    deadline = t0 + DURATION + 170   # allow time for sequential client connect at 500 nodes
    while proc.poll() is None:
        peak_mb = max(peak_mb, peak_rss_tree(proc.pid))
        if time.perf_counter() > deadline:
            proc.kill()
            break
        time.sleep(0.1)
    wall = time.perf_counter() - t0
    cfg_path.unlink(missing_ok=True)

    # newest summary.json for this protocol+nodes
    cand = sorted(
        Path("results").glob(f"{protocol}_scal_{protocol}_{nodes}_*"),
        key=lambda d: d.stat().st_mtime,
    )
    if not cand:
        return None
    s = json.loads((cand[-1] / "summary.json").read_text())
    return {
        "protocol": protocol, "nodes": nodes,
        "sent": s.get("sent", 0), "recv": s.get("recv", 0),
        "loss_pct": round(s.get("loss", 0.0) * 100, 3),
        "lat_p50_ms": round(s.get("lat_p50_ms", 0.0), 3),
        "lat_p95_ms": round(s.get("lat_p95_ms", 0.0), 3),
        "lat_p99_ms": round(s.get("lat_p99_ms", 0.0), 3),
        "throughput_msg_s": round(s.get("recv", 0) / DURATION, 1),
        "peak_mem_mb": round(peak_mb, 1),
        "wall_s": round(wall, 1),
    }


def main():
    rows = []
    for nodes in NODE_COUNTS:
        avail = psutil.virtual_memory().available / 1e9
        if avail < 1.5:
            print(f"[skip] only {avail:.1f} GB available, stopping before {nodes} nodes")
            break
        for protocol in PROTOCOLS:
            for rep in range(REPS):
                r = run_once(protocol, nodes)
                if r:
                    r["rep"] = rep
                    rows.append(r)
                    print(f"{protocol:>10} n={nodes:<5} rep{rep}  "
                          f"loss={r['loss_pct']:>5}%  p95={r['lat_p95_ms']:>6} ms  "
                          f"p99={r['lat_p99_ms']:>6} ms  mem={r['peak_mem_mb']:>6} MB  "
                          f"recv={r['recv']}")
                else:
                    print(f"{protocol:>10} n={nodes:<5} rep{rep}  FAILED (no summary)")
                time.sleep(2)
    OUT.write_text(json.dumps(rows, indent=2))
    print(f"\nRaw rows -> {OUT}")

    # aggregate mean +/- std
    print("\n=== AGGREGATE (mean +/- std over reps) ===")
    print(f"{'proto':>10} {'nodes':>6} {'loss%':>12} {'p95 ms':>14} {'p99 ms':>14} {'mem MB':>12}")
    agg = {}
    for nodes in NODE_COUNTS:
        for protocol in PROTOCOLS:
            sub = [r for r in rows if r["protocol"] == protocol and r["nodes"] == nodes]
            if not sub:
                continue
            def ms(key):
                vals = [r[key] for r in sub]
                m = statistics.mean(vals)
                sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
                return m, sd
            lm, ls = ms("loss_pct"); p95m, p95s = ms("lat_p95_ms")
            p99m, p99s = ms("lat_p99_ms"); mm, msd = ms("peak_mem_mb")
            agg[(protocol, nodes)] = {
                "loss": (lm, ls), "p95": (p95m, p95s),
                "p99": (p99m, p99s), "mem": (mm, msd),
            }
            print(f"{protocol:>10} {nodes:>6} "
                  f"{lm:>6.2f}+/-{ls:<4.2f} {p95m:>7.2f}+/-{p95s:<5.2f} "
                  f"{p99m:>7.2f}+/-{p99s:<5.2f} {mm:>7.0f}+/-{msd:<4.0f}")
    Path("results/protocol_scalability_agg.json").write_text(
        json.dumps({f"{k[0]}_{k[1]}": v for k, v in agg.items()}, indent=2))


if __name__ == "__main__":
    main()
