#!/usr/bin/env python3
"""
Scientific validation of STGen's physically-grounded anomaly engine across all sensors.

For each sensor modality and attack family this script:
  1. Generates a labelled stream (normal + injected samples) from the SAME
     physically-validated generator used everywhere else in STGen.
  2. Separability  - two-sample Kolmogorov-Smirnov D and Mann-Whitney U between
     the normal and the injected value distributions (detector-independent).
  3. Physical-invariant violation rate - the fraction of injected samples that
     cross a named physical bound (absolute range / operating range / temporal
     step). The bounds are the SAME ones the injector used, so the anomaly is
     defined and measured against the validated physical model, not an arbitrary
     threshold.
  4. Detectability - a one-class residual detector whose normal model is the
     calibrated physical noise floor. We report ROC AUC (computed from the rank
     statistic, AUC = U / (n_pos n_neg), so no sklearn dependency), precision /
     recall / F1 at a 3-sigma operating point, and detection latency.
  5. Significance - Mann-Whitney p-value on detector scores (attack vs normal).

Output: results/anomaly_validation.json (full multi-sensor results) +
        summary tables on stdout (by-sensor, by-attack).

Usage:  python3 run_anomaly_validation.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, ".")
from stgen.sensor_generator import generate_sensor_stream
from stgen.anomaly_injector import (
    get_invariants, violates_range, violates_operating, violates_step, ATTACK_TYPES,
)

# All sensor modalities with calibrated physical invariants
SENSORS = ["temp", "humidity", "light", "voltage", "pressure", "co2", "sound"]
SENSOR = "temp"  # default modality for single-sensor scripts (e.g. generate_anomaly_figure.py)
NODES = 60
DURATION = 40
RATE_HZ = 2.0
FRACTION = 0.15
INTENSITY = 3.0
SEED = 7
THRESH_SIGMA = 3.0          # 3-sigma operating point for the detector
ATTACKS = ["fdi_spoof", "bias_drift", "impossible_jump", "variance_burst",
           "stuck_at", "replay"]


def make_cfg(sensor, attack):
    return {
        "protocol": "custom_udp", "mode": "active",
        "num_clients": NODES, "duration": DURATION, "sensors": [sensor],
        "seed": SEED,
        "traffic_pattern": {sensor: {"rate_hz": RATE_HZ, "burst": False}},
        "adversarial": {
            "enabled": True, "seed": SEED, "attack": attack,
            "fraction": FRACTION, "intensity": INTENSITY, "probability": 1.0,
            "start_s": 0.0, "stop_s": 1e9, "label_file": None,
        },
    }


def collect(sensor, attack):
    """Run one labelled stream; return per-device ordered (value, is_attack, t).

    Handles sensors with different field names (value, level, etc) by preferring
    "value" but falling back to the first numeric field (same as anomaly_injector).
    """
    by_dev = {}
    for _cid, data, _iv in generate_sensor_stream(make_cfg(sensor, attack)):
        lbl = data.get("label")
        if lbl is None:
            continue
        sensor_data = data.get("sensor_data", {})

        # Prefer "value" field, fall back to first numeric field
        v = None
        if isinstance(sensor_data.get("value"), (int, float)):
            v = sensor_data["value"]
        else:
            # Find first numeric field (handles "level" for sound, etc)
            for key, val in sensor_data.items():
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    v = val
                    break

        if not isinstance(v, (int, float)):
            continue
        by_dev.setdefault(data["dev_id"], []).append(
            (float(lbl["t"]), float(v), bool(lbl["is_attack"])))
    for dev in by_dev:
        by_dev[dev].sort(key=lambda r: r[0])
    return by_dev


def detector_scores(sensor, by_dev):
    """One-class residual score per sample. Normal model = physical noise floor.

    score = max( |x - mu_op| / noise_floor , |x - x_prev| / max_step ).
    Returns arrays (scores, labels, times) aligned by sample.
    """
    inv = get_invariants(sensor)
    op_lo, op_hi = inv["operating"]
    mu = 0.5 * (op_lo + op_hi)
    sigma = inv["noise"]
    max_step = inv["max_step"]

    scores, labels, times = [], [], []
    for series in by_dev.values():
        prev = None
        for t, v, is_atk in series:
            z_val = abs(v - mu) / sigma
            z_step = abs(v - prev) / max_step if prev is not None else 0.0
            scores.append(max(z_val, z_step))
            labels.append(1 if is_atk else 0)
            times.append(t)
            prev = v
    return np.array(scores), np.array(labels), np.array(times)


def auc_rank(pos, neg):
    """ROC AUC via the Mann-Whitney rank statistic: AUC = U / (n_pos n_neg)."""
    if len(pos) == 0 or len(neg) == 0:
        return float("nan"), float("nan")
    res = stats.mannwhitneyu(pos, neg, alternative="greater")
    return res.statistic / (len(pos) * len(neg)), float(res.pvalue)


def evaluate(sensor, attack):
    by_dev = collect(sensor, attack)
    scores, labels, times = detector_scores(sensor, by_dev)
    pos, neg = scores[labels == 1], scores[labels == 0]
    n_pos, n_neg = int(len(pos)), int(len(neg))
    if n_pos == 0:
        return {"sensor": sensor, "attack": attack, "error": "no attack samples generated"}

    # --- value-distribution separability (detector independent) ---
    inv = get_invariants(sensor)
    op_lo, op_hi = inv["operating"]
    mu = 0.5 * (op_lo + op_hi)
    # reconstruct injected vs normal values from scores' inverse is awkward;
    # recompute directly from by_dev for clarity:
    inj_vals = [v for s in by_dev.values() for (_t, v, a) in s if a]
    nrm_vals = [v for s in by_dev.values() for (_t, v, a) in s if not a]
    ks_d, ks_p = stats.ks_2samp(inj_vals, nrm_vals)

    # --- physical-invariant violation rate over injected samples ---
    viol = 0
    for s in by_dev.values():
        prev = None
        for _t, v, a in s:
            if a and (violates_range(sensor, v) or violates_operating(sensor, v)
                      or violates_step(sensor, v, prev)):
                viol += 1
            prev = v
    viol_rate = viol / n_pos

    # --- detector metrics ---
    auc, auc_p = auc_rank(pos, neg)
    thr = THRESH_SIGMA
    tp = int(np.sum(pos > thr)); fn = n_pos - tp
    fp = int(np.sum(neg > thr)); tn = n_neg - fp
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    # detection latency: first detected attack sample relative to first attack sample
    atk_times = sorted(t for s in by_dev.values() for (t, v, a) in s if a)
    det_times = sorted(t for s in by_dev.values() for (t, v, a) in s
                       if a and max(abs(v - mu) / inv["noise"], 0) > thr)
    det_latency = (det_times[0] - atk_times[0]) if det_times and atk_times else None

    mw = stats.mannwhitneyu(pos, neg, alternative="two-sided")
    return {
        "sensor": sensor, "attack": attack, "n_attack": n_pos, "n_normal": n_neg,
        "separability": {"ks_D": round(float(ks_d), 4), "ks_p": float(ks_p)},
        "physical_violation_rate": round(viol_rate, 4),
        "detector": {
            "roc_auc": round(float(auc), 4),
            "precision_3sigma": round(precision, 4),
            "recall_3sigma": round(recall, 4),
            "f1_3sigma": round(f1, 4),
            "detection_latency_s": None if det_latency is None else round(det_latency, 3),
        },
        "significance": {"mannwhitney_U": float(mw.statistic),
                         "p_value": float(mw.pvalue)},
    }


def main():
    Path("results").mkdir(exist_ok=True)

    # Run validation across all sensor modalities and attack families
    all_results = []
    for sensor in SENSORS:
        for attack in ATTACKS:
            result = evaluate(sensor, attack)
            all_results.append(result)

    Path("results/anomaly_validation.json").write_text(json.dumps(all_results, indent=2))

    # Print summary tables
    print(f"\n{'='*120}")
    print(f"Anomaly Validation: Multi-Sensor Analysis (nodes={NODES}, duration={DURATION}s, seed={SEED})")
    print(f"{'='*120}\n")

    # Table 1: By Sensor (rows=sensors, show mean metrics across attacks)
    print("TABLE 1: Separability Summary (averaged across all attack families per sensor)")
    print(f"{'sensor':<12}{'mean_AUC':>10}{'mean_F1':>10}{'mean_viol%':>12}{'attacks':>8}")
    print("-" * 60)
    for sensor in SENSORS:
        sensor_rows = [r for r in all_results if r.get("sensor") == sensor and "error" not in r]
        if sensor_rows:
            mean_auc = np.mean([r["detector"]["roc_auc"] for r in sensor_rows])
            mean_f1 = np.mean([r["detector"]["f1_3sigma"] for r in sensor_rows])
            mean_viol = np.mean([r["physical_violation_rate"] for r in sensor_rows])
            print(f"{sensor:<12}{mean_auc:>10.3f}{mean_f1:>10.3f}{100*mean_viol:>12.1f}{len(sensor_rows):>8}")

    # Table 2: Full detail (all sensor x attack combinations)
    print(f"\n{'='*150}")
    print("TABLE 2: Detailed Results (all sensor × attack combinations)")
    print(f"{'sensor':<10}{'attack':<16}{'n_atk':>6}{'KS_D':>8}{'viol%':>8}{'AUC':>7}{'prec':>7}{'rec':>7}{'F1':>7}{'p':>10}")
    print("-" * 150)
    for r in all_results:
        if "error" in r:
            print(f"{r['sensor']:<10}{r['attack']:<16}  {r['error']}")
            continue
        d = r["detector"]
        print(f"{r['sensor']:<10}{r['attack']:<16}{r['n_attack']:>6}{r['separability']['ks_D']:>8.3f}"
              f"{100*r['physical_violation_rate']:>8.1f}{d['roc_auc']:>7.3f}"
              f"{d['precision_3sigma']:>7.2f}{d['recall_3sigma']:>7.2f}"
              f"{d['f1_3sigma']:>7.2f}{r['significance']['p_value']:>10.1e}")

    # Table 3: Hardest vs Easiest attacks across all sensors
    print(f"\n{'='*80}")
    print("TABLE 3: Attack Separability Ranking (mean AUC across all sensors)")
    attack_aucs = {}
    for atk in ATTACKS:
        atk_rows = [r for r in all_results if r.get("attack") == atk and "error" not in r]
        if atk_rows:
            attack_aucs[atk] = np.mean([r["detector"]["roc_auc"] for r in atk_rows])

    for atk in sorted(attack_aucs.keys(), key=lambda a: attack_aucs[a], reverse=True):
        print(f"  {atk:<20} AUC {attack_aucs[atk]:>6.3f}")

    print(f"\nwrote results/anomaly_validation.json ({len(all_results)} sensor×attack results)")


if __name__ == "__main__":
    main()
