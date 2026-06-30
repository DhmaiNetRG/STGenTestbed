#!/usr/bin/env python3
"""
Experiment 1 - Resource scaling of STGen's process-based node model.

This is protocol-agnostic: it measures the cost of *instantiating and holding*
N emulated sensor nodes, where each node is one independent OS process (the
custom_udp client binary), launched through STGen's own orchestrator.

For each node count it records:
  * Startup time  T(n): wall time to spawn the server + N client processes
                        (the artificial per-process settle has been removed,
                        so this reflects real fork/exec cost).
  * Memory  M(n):       summed Proportional Set Size (PSS) of the process tree.
                        PSS counts shared library pages once across identical
                        processes, so it is the honest per-node memory cost
                        (plain summed RSS double-counts shared pages).
  * Sys delta:          independent cross-check = drop in system-available RAM.
  * CPU:                average CPU of the node process tree while it runs.

Nodes generate at a low, realistic rate (default 1 Hz; the footprint is
rate-independent because memory is the process image, not the traffic).

Usage:  python3 run_scalability.py [n1 n2 ...]
        STGEN_RATE=1.0 STGEN_HOLD=4 python3 run_scalability.py 100 500 1000 2000
"""
import os
import sys
import csv
import json
import time
import signal
import statistics
from pathlib import Path

import numpy as np
import psutil

sys.path.insert(0, ".")
from stgen.orchestrator import Orchestrator

RATE_HZ = float(os.environ.get("STGEN_RATE", "1.0"))   # realistic per-node rate
HOLD = float(os.environ.get("STGEN_HOLD", "4"))        # seconds to hold nodes while measuring
SAFETY_GB = float(os.environ.get("STGEN_SAFETY", "0.8"))  # stop if free RAM drops below this
NODE_COUNTS = [int(a) for a in sys.argv[1:]] or [100, 250, 500, 1000, 2000]
TOTAL_RAM_GB = psutil.virtual_memory().total / 1e9


def tree_procs(root):
    procs = []
    try:
        procs = [root] + root.children(recursive=True)
    except psutil.Error:
        pass
    return procs


def tree_pss_gb(procs):
    """Summed PSS over the process tree (shared pages counted once)."""
    total = 0
    for p in procs:
        try:
            total += p.memory_full_info().pss
        except (psutil.Error, ValueError, FileNotFoundError):
            pass
    return total / 1e9


def tree_cpu_time(procs):
    t = 0.0
    for p in procs:
        try:
            ct = p.cpu_times()
            t += ct.user + ct.system
        except (psutil.Error, ValueError):
            pass
    return t


def run_one(n):
    me = psutil.Process()
    cfg = {
        "protocol": "custom_udp", "mode": "passive",
        "server_ip": "127.0.0.1", "server_port": 6000 + (n % 100),
        "num_clients": n, "duration": HOLD, "sensors": ["temp"],
        "rate_hz": RATE_HZ,
    }

    # --- baseline (let the machine settle first) ---
    time.sleep(1.0)
    base_avail = statistics.median(
        psutil.virtual_memory().available for _ in _ticks(3, 0.1))

    orch = Orchestrator("custom_udp", cfg)

    # --- startup: server bind (subtracted) + spawn N client processes ---
    t0 = time.perf_counter()
    orch.protocol.start_server()
    time.sleep(0.4)
    orch.protocol.start_clients(n)
    startup = time.perf_counter() - t0 - 0.4

    procs = tree_procs(me)
    n_live = max(0, len(procs) - 2)  # minus this python proc and the server

    # --- hold and measure peak memory + CPU while nodes run ---
    min_avail = base_avail
    cpu0 = tree_cpu_time(procs)
    w0 = time.perf_counter()
    peak_pss = 0.0
    t_end = time.perf_counter() + HOLD
    while time.perf_counter() < t_end:
        min_avail = min(min_avail, psutil.virtual_memory().available)
        peak_pss = max(peak_pss, tree_pss_gb(procs))
        time.sleep(0.25)
    w1 = time.perf_counter()
    cpu1 = tree_cpu_time(procs)
    cpu_pct = 100.0 * (cpu1 - cpu0) / (w1 - w0) if w1 > w0 else 0.0
    sys_delta_gb = max(0.0, (base_avail - min_avail) / 1e9)

    # --- teardown: fast bulk SIGKILL (the adapter's stop() sleeps 0.5 s PER
    #     process, which is O(N) minutes at scale). Kill the whole tree at once. ---
    victims = [p for p in tree_procs(me) if p.pid != me.pid]
    for p in victims:
        try:
            p.kill()
        except psutil.Error:
            pass
    psutil.wait_procs(victims, timeout=3)
    orch.protocol._alive = False
    time.sleep(0.5)

    pss_per_node_kb = (peak_pss * 1e6 / n) if n else 0.0
    return {
        "Nodes": n,
        "Live procs": n_live,
        "Startup (s)": round(startup, 2),
        "PSS (GB)": round(peak_pss, 3),
        "PSS/node (KB)": round(pss_per_node_kb, 1),
        "Sys delta (GB)": round(sys_delta_gb, 3),
        "CPU (%)": round(cpu_pct, 1),
        "Rate (Hz)": RATE_HZ,
    }


def _ticks(count, dt):
    for _ in range(count):
        yield
        time.sleep(dt)


def main():
    Path("results").mkdir(exist_ok=True)
    print(f"# Experiment 1: process-based resource scaling  "
          f"(rate={RATE_HZ} Hz, hold={HOLD}s, host RAM={TOTAL_RAM_GB:.1f} GB)", flush=True)
    rows = []
    for n in NODE_COUNTS:
        free = psutil.virtual_memory().available / 1e9
        if free < SAFETY_GB:
            print(f"[stop] only {free:.2f} GB free before {n} nodes (< {SAFETY_GB} GB safety)", flush=True)
            break
        print(f"running {n} nodes ...", flush=True)
        try:
            r = run_one(n)
        except Exception as e:
            print(f"  [fail] {n} nodes: {type(e).__name__}: {e}", flush=True)
            for p in tree_procs(psutil.Process()):
                if p.pid != os.getpid():
                    try:
                        p.kill()
                    except psutil.Error:
                        pass
            break
        rows.append(r)
        Path("results/scalability_results.json").write_text(json.dumps(rows, indent=2))
        print(f"  n={r['Nodes']:<5} live={r['Live procs']:<5} startup={r['Startup (s)']}s "
              f"PSS={r['PSS (GB)']}GB ({r['PSS/node (KB)']}KB/node) "
              f"sysdelta={r['Sys delta (GB)']}GB cpu={r['CPU (%)']}%", flush=True)
        time.sleep(2)

    if len(rows) >= 2:
        ns = np.array([r["Nodes"] for r in rows], float)
        pss = np.array([r["PSS (GB)"] for r in rows], float)
        tt = np.array([r["Startup (s)"] for r in rows], float)
        (mp, bp), r2p = _fit(ns, pss)
        (mt, bt), r2t = _fit(ns, tt)
        ceil_nodes = (TOTAL_RAM_GB - bp) / mp if mp > 0 else float("nan")
        print("\n# --- fits ---")
        print(f"PSS:     M(n) = {mp*1e6:.1f} KB/node * n + {bp*1e3:.0f} MB   (R^2={r2p:.4f})")
        print(f"Startup: T(n) = {mt*1e3:.3f} ms/node * n + {bt:.2f} s         (R^2={r2t:.4f})")
        print(f"Node ceiling on {TOTAL_RAM_GB:.0f} GB (process memory only): ~{ceil_nodes:,.0f} nodes")
        # write a CSV for the paper/plots
        with open("results/scalability_results.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)

    print("\n% LaTeX rows: Nodes & Startup(s) & PSS(GB) & PSS/node(KB) & CPU(%)")
    for r in rows:
        print(f"{r['Nodes']:,} & {r['Startup (s)']} & {r['PSS (GB)']} & "
              f"{r['PSS/node (KB)']} & {r['CPU (%)']} \\\\")


def _fit(x, y):
    m, b = np.polyfit(x, y, 1)
    yh = m * x + b
    r2 = 1 - np.sum((y - yh) ** 2) / np.sum((y - y.mean()) ** 2)
    return (m, b), r2


if __name__ == "__main__":
    main()
