#!/usr/bin/env python3
"""
Multi-sensor anomaly validation figure.

(a) Heatmap: ROC AUC across 7 sensor modalities x 6 attack families.
(b) Per-sensor ROC curves for bias_drift (the stealthy attack) with a zoom inset.
(c) Per-sensor mean AUC bar chart (mean separability per modality).
(d) Per-attack mean AUC bar chart with spatial/temporal grouping.

Reuses collect() and detector_scores() from run_anomaly_validation.py.
"""
import json
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from mpl_toolkits.axes_grid1.inset_locator import mark_inset
from pathlib import Path

sys.path.insert(0, ".")
from run_anomaly_validation import collect, detector_scores, SENSORS, ATTACKS
from stgen.anomaly_injector import get_invariants

# ---- IEEE-grade style --------------------------------------------------------
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 9.5,
    "axes.linewidth": 0.6,
    "axes.edgecolor": "#000000",
    "axes.labelcolor": "#000000",
    "axes.titlesize": 10,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.color": "#000000",
    "ytick.color": "#000000",
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "grid.linewidth": 0.4,
    "grid.color": "#cfcfcf",
    "legend.framealpha": 1.0,
    "legend.edgecolor": "#888888",
    "legend.fancybox": False,
    "legend.handlelength": 2.4,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "savefig.dpi": 600,
})

# 7 ordered, print-safe line colors sampled from a perceptual colormap
_cmap_lines = plt.cm.viridis(np.linspace(0.05, 0.88, len(SENSORS)))
SENSOR_COLORS = {s: _cmap_lines[i] for i, s in enumerate(SENSORS)}
SENSOR_STYLES = {
    "temp":     "-",
    "humidity": (0, (5, 1.5)),
    "light":    (0, (1, 1)),
    "voltage":  (0, (4, 1.5, 1, 1.5)),
    "pressure": (0, (6, 1.5, 1, 1.5, 1, 1.5)),
    "co2":      (0, (3, 1.5)),
    "sound":    "-",
}

SENSOR_LABELS = {
    "temp": "Temp", "humidity": "Humidity", "light": "Light",
    "voltage": "Voltage", "pressure": "Pressure", "co2": "CO$_2$", "sound": "Sound",
}
ATTACK_LABELS = {
    "fdi_spoof": "FDI Spoof", "bias_drift": "Bias Drift",
    "impossible_jump": "Impossible Jump", "variance_burst": "Variance Burst",
    "stuck_at": "Stuck-at", "replay": "Replay",
}
SPATIAL_ATTACKS = {"fdi_spoof", "bias_drift", "impossible_jump", "variance_burst"}

ACCENT = "#2166AC"   # spatial / primary accent
MUTED  = "#9E9E9E"   # temporal / secondary


def roc_curve(scores, labels):
    order = np.argsort(-scores)
    l = labels[order]
    P, N = l.sum(), (len(l) - l.sum())
    tpr = np.concatenate([[0.0], np.cumsum(l) / max(P, 1)])
    fpr = np.concatenate([[0.0], np.cumsum(1 - l) / max(N, 1)])
    auc = float(np.trapz(tpr, fpr))
    return fpr, tpr, auc


def clipped_xerr(mean, std, hi=1.0, lo=0.0):
    """Asymmetric error so the whisker never crosses the metric's [lo, hi] bound."""
    upper = min(std, hi - mean)
    lower = min(std, mean - lo)
    return np.array([[lower], [upper]])


# ---- Load precomputed results -----------------------------------------------
results_path = Path("results/anomaly_validation.json")
auc_matrix = {}
if results_path.exists():
    for r in json.loads(results_path.read_text()):
        if "error" not in r:
            auc_matrix[(r["sensor"], r["attack"])] = r["detector"]["roc_auc"]
else:
    for sensor in SENSORS:
        for atk in ATTACKS:
            try:
                sc, lb, _ = detector_scores(sensor, collect(sensor, atk))
                _, _, auc = roc_curve(sc, lb)
                auc_matrix[(sensor, atk)] = auc
            except Exception:
                auc_matrix[(sensor, atk)] = float("nan")

mat = np.array([[auc_matrix.get((s, a), np.nan) for s in SENSORS] for a in ATTACKS])


# ---- Figure layout -----------------------------------------------------------
fig = plt.figure(figsize=(7.16, 5.6))   # IEEE double-column width (~7.16 in)
gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.34,
                      left=0.085, right=0.97, top=0.93, bottom=0.085)
ax_heat = fig.add_subplot(gs[0, 0])
ax_roc  = fig.add_subplot(gs[0, 1])
ax_sens = fig.add_subplot(gs[1, 0])
ax_atk  = fig.add_subplot(gs[1, 1])

for ax in (ax_roc, ax_sens, ax_atk):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# ---- Panel (a): grayscale heatmap -------------------------------------------
norm = mcolors.Normalize(vmin=0.40, vmax=1.0)
im = ax_heat.imshow(mat, cmap="Greys", norm=norm, aspect="auto")

for i in range(len(ATTACKS)):
    for j in range(len(SENSORS)):
        v = mat[i, j]
        if not np.isnan(v):
            ax_heat.text(j, i, f"{v:.2f}", ha="center", va="center",
                         fontsize=6.8, weight="bold",
                         color="white" if v > 0.72 else "#111111")

ax_heat.set_xticks(range(len(SENSORS)))
ax_heat.set_yticks(range(len(ATTACKS)))
ax_heat.set_xticklabels([SENSOR_LABELS[s] for s in SENSORS], fontsize=7, rotation=35,
                        ha="right", rotation_mode="anchor")
ax_heat.set_yticklabels([ATTACK_LABELS[a] for a in ATTACKS], fontsize=7)
ax_heat.tick_params(length=0)
ax_heat.axhline(3.5, color="white", lw=2.2)
ax_heat.set_xticks(np.arange(len(SENSORS)) - 0.5, minor=True)
ax_heat.set_yticks(np.arange(len(ATTACKS)) - 0.5, minor=True)
ax_heat.grid(which="minor", color="white", linewidth=1.4)
ax_heat.tick_params(which="minor", length=0)
for s in ax_heat.spines.values():
    s.set_visible(False)

cbar = fig.colorbar(im, ax=ax_heat, shrink=0.82, pad=0.025, aspect=18)
cbar.set_label("ROC AUC", fontsize=7.5)
cbar.ax.tick_params(labelsize=6.5, length=2)
cbar.outline.set_linewidth(0.4)
ax_heat.set_title("(a) Per-modality separability (AUC)", fontsize=9, weight="bold")


# ---- Panel (b): ROC curves with zoom inset ----------------------------------
ax_roc.plot([0, 1], [0, 1], color="#bbbbbb", lw=0.7, ls=(0, (3, 3)), zorder=1)

roc_data = {}
for s in SENSORS:
    sc, lb, _ = detector_scores(s, collect(s, "bias_drift"))
    fpr, tpr, auc = roc_curve(sc, lb)
    roc_data[s] = (fpr, tpr, auc)
    # Label with the same rank-statistic AUC reported in the table/heatmap, so a
    # given cell shows one value everywhere (the curve shape is from fpr/tpr).
    auc_lbl = auc_matrix.get((s, "bias_drift"), auc)
    ax_roc.plot(fpr, tpr, color=SENSOR_COLORS[s], ls=SENSOR_STYLES[s], lw=1.6,
                zorder=3, label=f"{SENSOR_LABELS[s]} ({auc_lbl:.2f})")

ax_roc.set_xlim(0, 1)
ax_roc.set_ylim(0, 1.005)
ax_roc.set_xlabel("False Positive Rate", fontsize=8.5)
ax_roc.set_ylabel("True Positive Rate", fontsize=8.5)
ax_roc.tick_params(labelsize=7.5)
ax_roc.legend(loc="lower right", fontsize=6.0, frameon=True, ncol=1,
              handlelength=2.6, borderpad=0.4, labelspacing=0.3)
ax_roc.set_title("(b) Bias-drift ROC by modality", fontsize=9, weight="bold")

# zoom inset on the discriminating top-left region
axin = ax_roc.inset_axes([0.12, 0.14, 0.40, 0.44])
for s in SENSORS:
    fpr, tpr, _ = roc_data[s]
    axin.plot(fpr, tpr, color=SENSOR_COLORS[s], ls=SENSOR_STYLES[s], lw=1.4)
axin.set_xlim(0.0, 0.20)
axin.set_ylim(0.78, 1.005)
axin.set_xticks([0.0, 0.1, 0.2])
axin.set_yticks([0.8, 0.9, 1.0])
axin.tick_params(labelsize=5.5, length=2)
axin.grid(True, lw=0.3, color="#dddddd")
for sp in axin.spines.values():
    sp.set_linewidth(0.5)
mark_inset(ax_roc, axin, loc1=2, loc2=4, fc="none", ec="#999999", lw=0.6)


# ---- helper for clean horizontal bars ---------------------------------------
def hbar_panel(ax, items, means, stds, colors, title, xlabel):
    for i, (m, sd, c) in enumerate(zip(means, stds, colors)):
        ax.barh(i, m, xerr=clipped_xerr(m, sd), capsize=2.5,
                color=c, edgecolor="#1a1a1a", linewidth=0.5, zorder=2,
                error_kw={"elinewidth": 0.7, "capthick": 0.7, "color": "#1a1a1a"})
        ax.text(0.018, i, f"{m:.3f}", va="center", ha="left",
                fontsize=7, weight="bold",
                color="white" if _luminance(c) < 0.6 else "#111111")
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels(items, fontsize=7.5)
    ax.set_xlabel(xlabel, fontsize=8.5)
    ax.set_xlim(0, 1.04)
    ax.set_xticks(np.arange(0, 1.01, 0.2))
    ax.tick_params(labelsize=7.5)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=9, weight="bold")
    ax.grid(True, axis="x", alpha=0.5, linestyle=":", linewidth=0.4)
    ax.set_axisbelow(True)


def _luminance(c):
    r, g, b = mcolors.to_rgb(c)
    return 0.299 * r + 0.587 * g + 0.114 * b


# ---- Panel (c): mean AUC by sensor ------------------------------------------
s_means = {s: np.nanmean([auc_matrix.get((s, a), np.nan) for a in ATTACKS]) for s in SENSORS}
s_stds  = {s: np.nanstd([auc_matrix.get((s, a), np.nan) for a in ATTACKS]) for s in SENSORS}
order_s = sorted(SENSORS, key=lambda s: s_means[s], reverse=True)
# single-hue gradient (dark = best) for an ordered, cohesive look
grad = plt.cm.Blues(np.linspace(0.85, 0.40, len(order_s)))
hbar_panel(ax_sens,
           [SENSOR_LABELS[s] for s in order_s],
           [s_means[s] for s in order_s],
           [s_stds[s] for s in order_s],
           grad,
           "(c) Mean AUC by modality",
           "Mean AUC over 6 attacks ($\\pm\\sigma$)")


# ---- Panel (d): mean AUC by attack, spatial vs temporal ---------------------
a_means = {a: np.nanmean([auc_matrix.get((s, a), np.nan) for s in SENSORS]) for a in ATTACKS}
a_stds  = {a: np.nanstd([auc_matrix.get((s, a), np.nan) for s in SENSORS]) for a in ATTACKS}
order_a = sorted(ATTACKS, key=lambda a: a_means[a], reverse=True)
colors_a = [ACCENT if a in SPATIAL_ATTACKS else MUTED for a in order_a]
hbar_panel(ax_atk,
           [ATTACK_LABELS[a] for a in order_a],
           [a_means[a] for a in order_a],
           [a_stds[a] for a in order_a],
           colors_a,
           "(d) Attack separability ranking",
           "Mean AUC over 7 modalities ($\\pm\\sigma$)")

# spatial/temporal divider + bracket labels
spatial_count = sum(1 for a in order_a if a in SPATIAL_ATTACKS)
ax_atk.axhline(spatial_count - 0.5, color="#555555", lw=0.7, ls=(0, (4, 3)))
ax_atk.annotate("spatial", xy=(0.985, (spatial_count - 1) / 2.0),
                xycoords=("axes fraction", "data"), fontsize=6.8, style="italic",
                color=ACCENT, ha="right", va="center", weight="bold")
ax_atk.annotate("temporal", xy=(0.985, spatial_count + (len(order_a) - spatial_count - 1) / 2.0),
                xycoords=("axes fraction", "data"), fontsize=6.8, style="italic",
                color="#666666", ha="right", va="center", weight="bold")


fig.savefig("images/anomaly_validation.png", bbox_inches="tight")
fig.savefig("images/anomaly_validation.eps", bbox_inches="tight")
plt.close(fig)
print("wrote images/anomaly_validation.eps and .png")
