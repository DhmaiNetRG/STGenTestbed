#!/usr/bin/env python3
"""
Single-machine scalability sweep using the CoAP protocol (active mode).

For each node count, instantiates the STGen orchestrator with the CoAP adapter,
times server+client startup, drives the sensor stream while sampling resident
memory and CPU, and records per-message round-trip latency. Unlike the custom
UDP client (one OS process per node), the CoAP adapter uses asynchronous
clients, so its per-node memory footprint is much smaller.

Outputs results/coap_scalability_results.json and a LaTeX table on stdout.
"""
import sys
import time
import json
import threading
import statistics
from pathlib import Path

import numpy as np
import psutil

sys.path.insert(0, ".")
from stgen.orchestrator import Orchestrator
from stgen.sensor_generator import generate_sensor_stream

import os
DURATION = int(os.environ.get("STGEN_DUR", "5"))   # seconds of offered traffic per run
RATE_HZ = 10.0
NODE_COUNTS = [int(a) for a in sys.argv[1:]] or [100, 250, 500, 1000, 2000]


def monitor(proc, stop, out):
    peak_mem = 0.0
    peak_cpu = 0.0
    proc.cpu_percent(None)
    while not stop.is_set():
        try:
            peak_mem = max(peak_mem, proc.memory_info().rss / 1e9)
            peak_cpu = max(peak_cpu, proc.cpu_percent(None))
        except psutil.Error:
            break
        time.sleep(0.1)
    out["mem"] = peak_mem
    out["cpu"] = peak_cpu


def run_one(n):
    cfg = {
        "protocol": "coap", "mode": "active", "server_ip": "127.0.0.1",
        "server_port": 5683, "num_clients": n, "duration": DURATION,
        "sensors": ["temp"],
        "traffic_pattern": {"temp": {"rate_hz": RATE_HZ, "burst": False}},
    }
    orch = Orchestrator("coap", cfg)
    proc = psutil.Process()

    # startup = server bind + client init (subtract the fixed 0.5 s bind wait)
    t0 = time.perf_counter()
    orch.protocol.start_server()
    time.sleep(0.5)
    orch.protocol.start_clients(n)
    startup = time.perf_counter() - t0 - 0.5
    # node footprint = RSS right after the n clients exist, before traffic buffers grow
    node_mb = proc.memory_info().rss / 1e6

    stop = threading.Event()
    res = {}
    mon = threading.Thread(target=monitor, args=(proc, stop, res))
    mon.start()

    lat = []
    sent = 0
    t_send = time.perf_counter()
    for cid, payload, _to in generate_sensor_stream(cfg):
        ts = time.perf_counter()
        try:
            orch.protocol.send_data(cid, payload)
        except Exception:
            pass
        lat.append((time.perf_counter() - ts) * 1000.0)
        sent += 1
    elapsed = time.perf_counter() - t_send
    time.sleep(0.3)

    stop.set()
    mon.join()
    recv = getattr(orch.protocol, "_recv_count", sent)
    try:
        orch.protocol.stop()
    except Exception:
        pass

    p95 = float(np.percentile(lat, 95)) if lat else 0.0
    return {
        "Nodes": n,
        "Startup (s)": round(startup, 2),
        "Memory (MB)": round(node_mb, 1),          # node footprint (after start_clients)
        "Peak Memory (MB)": round(res.get("mem", 0.0) * 1e3, 1),
        "CPU Peak (%)": int(res.get("cpu", 0.0)),
        "Throughput (msg/s)": int(recv / elapsed) if elapsed > 0 else 0,
        "Delivery (%)": round(100.0 * recv / sent, 1) if sent else 0.0,
        "Lat P95 (ms)": round(p95, 2),
        "sent": sent, "recv": recv,
    }


def main():
    Path("results").mkdir(exist_ok=True)
    rows = []
    for n in NODE_COUNTS:
        avail = psutil.virtual_memory().available / 1e9
        if avail < 1.0:
            print(f"[stop] only {avail:.1f} GB free before {n} nodes")
            break
        print(f"running CoAP at {n} nodes ...", flush=True)
        r = run_one(n)
        rows.append(r)
        Path("results/coap_scalability_results.json").write_text(json.dumps(rows, indent=2))
        print(f"  n={r['Nodes']:<5} startup={r['Startup (s)']}s node_mem={r['Memory (MB)']}MB "
              f"peak={r['Peak Memory (MB)']}MB cpu={r['CPU Peak (%)']}% thr={r['Throughput (msg/s)']}/s "
              f"deliv={r['Delivery (%)']}% p95={r['Lat P95 (ms)']}ms", flush=True)
        time.sleep(2)

    print("\n% --- LaTeX table rows (Nodes & Startup & NodeMem(MB) & CPU & Thr & Delivery & P95) ---")
    for r in rows:
        print(f"{r['Nodes']} & {r['Startup (s)']} & {r['Memory (MB)']} & {r['CPU Peak (%)']} & "
              f"{r['Throughput (msg/s)']:,} & {r['Delivery (%)']} & {r['Lat P95 (ms)']} \\\\")


if __name__ == "__main__":
    main()
