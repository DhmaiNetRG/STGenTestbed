#!/usr/bin/env python3
"""
Multi-sensor heatmap: ROC AUC across all sensor modalities and attack families.

Shows the robustness of the framework across 6 physical sensor types and 6 attack
families. Demonstrates that physical-invariant-based anomaly injection and detection
generalizes beyond a single modality.
"""
import json
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, ".")

# Load results
results = json.loads(open("results/anomaly_validation.json").read())

# Dynamically extract unique sensors and attacks (in order)
sensors_set = set()
attacks_set = set()
for r in results:
    if "error" not in r:
        sensors_set.add(r.get("sensor"))
        attacks_set.add(r.get("attack"))

sensors = sorted(list(sensors_set))  # Alphabetical order
attacks = ["fdi_spoof", "bias_drift", "impossible_jump", "variance_burst", "stuck_at", "replay"]

# Build AUC matrix: rows=attacks, cols=sensors
auc_matrix = np.zeros((len(attacks), len(sensors)))
for i, atk in enumerate(attacks):
    for j, sensor in enumerate(sensors):
        match = next((r for r in results if r.get("sensor") == sensor
                      and r.get("attack") == atk and "error" not in r), None)
        if match:
            auc_matrix[i, j] = match["detector"]["roc_auc"]
        else:
            auc_matrix[i, j] = np.nan

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "mathtext.fontset": "dejavuserif",
    "font.size": 9.5,
    "axes.linewidth": 0.8,
})

fig, ax = plt.subplots(figsize=(9, 4.5))

# Heatmap with white-blue colormap
im = ax.imshow(auc_matrix, cmap="Blues", aspect="auto", vmin=0.4, vmax=1.05)

# Add text annotations
for i in range(len(attacks)):
    for j in range(len(sensors)):
        val = auc_matrix[i, j]
        if not np.isnan(val):
            text_color = "white" if val < 0.7 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                   color=text_color, fontsize=8.5, weight="bold")

# Labels and title
ax.set_xticks(range(len(sensors)))
ax.set_yticks(range(len(attacks)))
ax.set_xticklabels(sensors, fontsize=9)
ax.set_yticklabels(attacks, fontsize=9)
ax.set_xlabel("Sensor Modality", fontsize=10, weight="bold")
ax.set_ylabel("Attack Family", fontsize=10, weight="bold")
ax.set_title(f"Multi-Sensor Robustness: ROC AUC across {len(sensors)} modalities × {len(attacks)} attacks",
             fontsize=10, weight="bold", pad=15)

# Colorbar
cbar = plt.colorbar(im, ax=ax, label="ROC AUC", shrink=0.8)
cbar.set_label("ROC AUC", fontsize=9)

# Grid
ax.set_xticks(np.arange(len(sensors)) - 0.5, minor=True)
ax.set_yticks(np.arange(len(attacks)) - 0.5, minor=True)
ax.grid(which="minor", color="#cccccc", linestyle="-", linewidth=0.8)

fig.tight_layout()
for ext in ("eps", "png"):
    fig.savefig(f"images/multisensor_robustness.{ext}", dpi=600, bbox_inches="tight")
plt.close(fig)

print("wrote images/multisensor_robustness.eps and .png")

# Also print a summary
print("\nMulti-sensor AUC matrix:")
print(f"{'Attack':<18}", end="")
for s in sensors:
    print(f"{s:>9}", end="")
print()
print("-" * 80)
for i, atk in enumerate(attacks):
    print(f"{atk:<18}", end="")
    for j in range(len(sensors)):
        if not np.isnan(auc_matrix[i, j]):
            print(f"{auc_matrix[i, j]:>9.3f}", end="")
        else:
            print(f"{'N/A':>9}", end="")
    print()

print(f"\nMean AUC by sensor:")
for j, sensor in enumerate(sensors):
    col = auc_matrix[:, j]
    mean_auc = np.nanmean(col)
    print(f"  {sensor:<12} {mean_auc:>6.3f}")
