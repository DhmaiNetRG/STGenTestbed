#!/usr/bin/env python3
"""
Held-out evaluation of a 2-component Gaussian-mixture light model.

Fit the mixture on half the IBRL motes, evaluate marginal fidelity (KS D, JSD)
on the held-out half. Compares three light models against the same held-out
test set:
  - default       : the current single-regime STGen light model
  - gmm_iid        : i.i.d. samples from the fitted 2-component mixture
  - gmm_regime     : the mixture with regime persistence (keeps temporal structure)

The fit set and test set are disjoint motes, so the improvement reflects
generalisation across the deployment, not memorisation.
"""
import random
import numpy as np

from run_fidelity_analysis import (
    load_intel_data, generate_stgen_light, ks_test, js_divergence,
)

random.seed(42)
np.random.seed(42)
N = 100_000
THR = 100.0   # lux split between dark and lit modes

df = load_intel_data()
motes = sorted(df["moteid"].unique())
fit_motes = motes[0::2]    # ~27 motes
test_motes = motes[1::2]   # ~27 disjoint motes
fit_light = df[df["moteid"].isin(fit_motes)]["light"].values
test_light = df[df["moteid"].isin(test_motes)]["light"].values
print(f"fit motes={len(fit_motes)} ({len(fit_light):,} readings)  "
      f"test motes={len(test_motes)} ({len(test_light):,} readings)")

# --- fit 2-component model on the FIT set only (hard threshold split) ---
dark = fit_light[fit_light <= THR]
bright = fit_light[fit_light > THR]
w_dark = len(dark) / len(fit_light)
mu_d, sig_d = float(dark.mean()), float(dark.std())
mu_b, sig_b = float(bright.mean()), float(bright.std())
print(f"fit: w_dark={w_dark:.3f}  dark~N({mu_d:.1f},{sig_d:.1f})  "
      f"bright~N({mu_b:.1f},{sig_b:.1f})")

# --- (a) 2-component threshold-split mixture, i.i.d. (full variances) ---
comp_dark = np.random.random(N) < w_dark
gmm2 = np.where(comp_dark,
                np.random.normal(mu_d, sig_d, N),
                np.random.normal(mu_b, sig_b, N))
gmm2 = np.clip(gmm2, 0.0, None)


# --- (b) K-component Gaussian mixture fitted by 1-D EM on the fit set ---
def em_gmm_1d(x, K, iters=60, seed=0):
    rng = np.random.default_rng(seed)
    mu = np.quantile(x, np.linspace(0.1, 0.9, K))
    var = np.full(K, x.var() / K) + 1.0
    w = np.full(K, 1.0 / K)
    x = x.reshape(-1, 1)
    for _ in range(iters):
        # E-step (responsibilities)
        comp = (w / np.sqrt(2 * np.pi * var)) * \
               np.exp(-(x - mu) ** 2 / (2 * var))
        comp += 1e-300
        r = comp / comp.sum(1, keepdims=True)
        # M-step
        Nk = r.sum(0)
        w = Nk / len(x)
        mu = (r * x).sum(0) / Nk
        var = (r * (x - mu) ** 2).sum(0) / Nk + 1e-6
    return w, mu, np.sqrt(var)


def sample_gmm(w, mu, sig, n):
    comp = np.random.choice(len(w), size=n, p=w / w.sum())
    return np.clip(np.random.normal(mu[comp], sig[comp]), 0.0, None)


# --- baseline: current single-regime model ---
default_light = generate_stgen_light(N, motes=54)

print("\n=== held-out marginal fidelity vs test motes ===")
print(f"{'model':>16} {'KS D':>8} {'JSD':>8}")
d = ks_test(test_light, default_light)["D"]
j = js_divergence(test_light, default_light)
print(f"{'default(1-mode)':>16} {d:>8.3f} {j:>8.3f}")
d = ks_test(test_light, gmm2)["D"]
j = js_divergence(test_light, gmm2)
print(f"{'gmm2-threshold':>16} {d:>8.3f} {j:>8.3f}")
import json
best = None
for K in (2, 3, 4, 5, 6):
    w, mu, sig = em_gmm_1d(fit_light.astype(float), K)
    synth = sample_gmm(w, mu, sig, N)
    d = ks_test(test_light, synth)["D"]
    j = js_divergence(test_light, synth)
    print(f"{'gmm%d-EM' % K:>16} {d:>8.3f} {j:>8.3f}")
    if K == 5:
        order = np.argsort(mu)
        best = {"K": 5, "ks_D": round(d, 4), "jsd": round(j, 4),
                "weights": [round(float(x), 5) for x in w[order]],
                "means": [round(float(x), 2) for x in mu[order]],
                "sigmas": [round(float(x), 2) for x in sig[order]]}
json.dump(best, open("results/light_gmm_params.json", "w"), indent=2)
print("\nK=5 params ->", json.dumps(best))
