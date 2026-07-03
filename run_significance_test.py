#!/usr/bin/env python3
"""
Statistical significance of the per-message latency difference between MQTT and
CoAP, measured on the loopback interface with a large message sample.

For each protocol the orchestrator is driven in active mode; every delivered
message contributes one end-to-end latency sample (orchestrator metrics["lat"]).
We then run a two-sided Mann-Whitney U test on the two latency distributions,
report bootstrap 95% confidence intervals on each median, and the rank-biserial
effect size. NetEm congestion needs sudo and is not used here; this isolates the
protocol-stack latency ordering of Section 6.2 (custom UDP < MQTT < CoAP).

Output: results/significance_test.json  + a summary on stdout.
"""
import os
import sys
import json
import time
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, ".")
from stgen.orchestrator import Orchestrator
from stgen.sensor_generator import generate_sensor_stream

NODES = int(os.environ.get("STGEN_SIG_NODES", "50"))
DURATION = int(os.environ.get("STGEN_SIG_DUR", "15"))
RATE_HZ = 10.0
PORT = {"mqtt": 1883, "coap": 5683}


def collect_latencies(proto):
    cfg = {
        "protocol": proto, "mode": "active", "server_ip": "127.0.0.1",
        "server_port": PORT[proto], "num_clients": NODES, "duration": DURATION,
        "sensors": ["temp"],
        "traffic_pattern": {"temp": {"rate_hz": RATE_HZ, "burst": False}},
    }
    orch = Orchestrator(proto, cfg)
    orch.protocol.start_server()
    time.sleep(0.6)
    orch.protocol.start_clients(NODES)
    time.sleep(0.4)
    lat = []
    t_end = time.perf_counter() + DURATION
    for cid, payload, _to in generate_sensor_stream(cfg):
        if time.perf_counter() > t_end:
            break
        t0 = time.perf_counter()
        try:
            ok, t_srv = orch.protocol.send_data(cid, payload)
        except Exception:
            continue
        if ok and t_srv and t_srv > t0:
            lat.append((t_srv - t0) * 1000.0)
    try:
        orch.protocol.stop()
    except Exception:
        pass
    return np.asarray(lat, float)


def boot_ci_median(x, iters=3000, seed=0):
    rng = np.random.default_rng(seed)
    meds = [np.median(rng.choice(x, size=len(x), replace=True)) for _ in range(iters)]
    return float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def main():
    Path("results").mkdir(exist_ok=True)
    data = {}
    for proto in ("mqtt", "coap"):
        print(f"running {proto} ...", flush=True)
        x = collect_latencies(proto)
        data[proto] = x
        print(f"  {proto}: n={len(x)}  median={np.median(x):.3f} ms  "
              f"mean={x.mean():.3f}  p95={np.percentile(x,95):.3f}", flush=True)
        time.sleep(1)

    m, c = data["mqtt"], data["coap"]
    if len(m) < 100 or len(c) < 100:
        print(f"\n[warn] small sample (mqtt={len(m)}, coap={len(c)}); test may be underpowered")

    U, p = stats.mannwhitneyu(m, c, alternative="two-sided")
    rbc = 1.0 - (2.0 * U) / (len(m) * len(c))   # rank-biserial effect size
    m_ci = boot_ci_median(m)
    c_ci = boot_ci_median(c)

    out = {
        "config": {"nodes": NODES, "duration_s": DURATION, "rate_hz": RATE_HZ,
                   "interface": "loopback", "impairment": "none"},
        "mqtt": {"n": int(len(m)), "median_ms": float(np.median(m)),
                 "mean_ms": float(m.mean()), "p95_ms": float(np.percentile(m, 95)),
                 "median_ci95": m_ci},
        "coap": {"n": int(len(c)), "median_ms": float(np.median(c)),
                 "mean_ms": float(c.mean()), "p95_ms": float(np.percentile(c, 95)),
                 "median_ci95": c_ci},
        "mann_whitney_U": float(U), "p_value": float(p),
        "rank_biserial": float(rbc),
    }
    Path("results/significance_test.json").write_text(json.dumps(out, indent=2))

    print("\n=== Mann-Whitney U (two-sided), MQTT vs CoAP per-message latency ===")
    print(f"MQTT : n={out['mqtt']['n']:6d}  median={out['mqtt']['median_ms']:.3f} ms "
          f"(95% CI {m_ci[0]:.3f}-{m_ci[1]:.3f})")
    print(f"CoAP : n={out['coap']['n']:6d}  median={out['coap']['median_ms']:.3f} ms "
          f"(95% CI {c_ci[0]:.3f}-{c_ci[1]:.3f})")
    print(f"U={U:.0f}  p={p:.3e}  rank-biserial={rbc:.3f}")
    print("wrote results/significance_test.json")


if __name__ == "__main__":
    main()
