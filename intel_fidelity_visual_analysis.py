#!/usr/bin/env python3
"""
Intel Berkeley Dataset Fidelity Analysis: Visual Overlay & Quantitative Metrics
================================================================================

Creates:
1. Time-series plots overlaying physical Intel sensor traces with STGen synthetic traces
2. Quantitative error metrics (RMSE, MAE)
3. Statistical distribution testing (Kolmogorov-Smirnov two-sample test)
4. Trend line and variance comparison

Output:
  - results/fidelity/visual_overlay_*.png    [Time-series comparison plots]
  - results/fidelity/metrics_summary.csv     [Quantitative results table]
  - Console summary with K-S test results
"""

import os
import sys
import math
import random
import json
from pathlib import Path
from typing import Tuple, Dict, List
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from scipy import stats as sp_stats
from scipy.ndimage import uniform_filter1d

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from stgen.sensor_generator import _ou_step

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
INTEL_DATA = PROJECT_ROOT / "Intel_dataset" / "data.txt"
OUTPUT_DIR = PROJECT_ROOT / "results" / "fidelity"
SEED = 42

# Intel sensor ranges
INTEL_TEMP_RANGE = (-10, 60)     # °C
INTEL_HUM_RANGE = (0, 100)       # %
INTEL_LIGHT_RANGE = (0, 100000)  # lux
INTEL_VOLT_RANGE = (1.5, 3.5)    # V

# Visualization parameters
N_STGEN_SAMPLES = 100_000        # Total synthetic samples to generate
N_STGEN_MOTES = 54               # Match Intel deployment
TIME_WINDOW_SAMPLES = 1000       # Number of consecutive samples to plot in overlay
TREND_WINDOW = 50                # Window size for trend line smoothing
ALPHA_PHYSICAL = 0.7             # Opacity for physical trace
ALPHA_SYNTHETIC = 0.6            # Opacity for synthetic trace
DPI = 150

random.seed(SEED)
np.random.seed(SEED)

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_intel_data() -> pd.DataFrame:
    """Parse Intel Berkeley Lab dataset into a DataFrame."""
    print("[Loading] Intel Berkeley Lab dataset …")
    cols = ["date", "time", "epoch", "moteid",
            "temperature", "humidity", "light", "voltage"]
    rows = []
    skipped = 0
    
    with open(INTEL_DATA, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 8:
                skipped += 1
                continue
            try:
                row = {
                    "date": parts[0],
                    "time": parts[1],
                    "epoch": int(parts[2]),
                    "moteid": int(parts[3]),
                    "temperature": float(parts[4]),
                    "humidity": float(parts[5]),
                    "light": float(parts[6]),
                    "voltage": float(parts[7]),
                }
                rows.append(row)
            except (ValueError, IndexError):
                skipped += 1
    
    df = pd.DataFrame(rows)
    print(f"    Loaded {len(df):,} readings ({skipped:,} malformed rows)")
    
    # Filter implausible values
    n_before = len(df)
    df = df[
        df["temperature"].between(*INTEL_TEMP_RANGE) &
        df["humidity"].between(*INTEL_HUM_RANGE) &
        df["light"].between(*INTEL_LIGHT_RANGE) &
        df["voltage"].between(*INTEL_VOLT_RANGE)
    ].copy()
    print(f"    After filter: {len(df):,} readings ({n_before - len(df):,} removed)")
    return df


# ---------------------------------------------------------------------------
# STGen Synthetic Trace Generation
# ---------------------------------------------------------------------------

def generate_mvou_temp_hum(n: int, motes: int = 54) -> Tuple[np.ndarray, np.ndarray]:
    """Multivariate Ornstein-Uhlenbeck for Temperature & Humidity."""
    dt = 1.0
    theta_T, sigma_T = 0.002, 0.15
    theta_H, sigma_H = 0.001, 0.20
    rho = -0.38  # Temp-Humidity correlation

    T_vals = np.zeros(n)
    H_vals = np.zeros(n)
    per_mote = n // motes

    for m in range(motes):
        start = m * per_mote
        end = min(start + per_mote, n)
        steps = end - start

        # Mote-specific baselines
        mu_T = random.gauss(22.2, 1.0)
        mu_T = max(18, min(30, mu_T))
        mu_H = 53.8 - 0.64 * mu_T

        current_T = mu_T + random.gauss(0, 1)
        current_H = mu_H + random.gauss(0, 3)

        dW1 = np.random.normal(0, math.sqrt(dt), steps)
        dW2 = np.random.normal(0, math.sqrt(dt), steps)
        dZ_T = dW1
        dZ_H = rho * dW1 + math.sqrt(1 - rho**2) * dW2

        for i in range(steps):
            # Occasional regime shifts (HVAC/Sunlight)
            if random.random() < 0.001:
                mu_T += random.gauss(0, 4)
                mu_T = max(15, min(40, mu_T))
                mu_H = 53.8 - 0.64 * mu_T

            current_T += theta_T * (mu_T - current_T) * dt + sigma_T * dZ_T[i]
            current_H += theta_H * (mu_H - current_H) * dt + sigma_H * dZ_H[i]
            current_H = max(0.0, min(100.0, current_H))

            T_vals[start + i] = current_T
            H_vals[start + i] = current_H

    return T_vals, H_vals


def generate_stgen_light(n: int, motes: int = 54) -> np.ndarray:
    """Light: bimodal OU with regime switching (dark vs bright)."""
    per_mote = n // motes
    vals = np.zeros(n)
    
    for m in range(motes):
        start = m * per_mote
        end = start + per_mote
        bright = random.random() > 0.375
        current = 639.0 if bright else 28.0
        
        for i in range(start, min(end, n)):
            if bright:
                if random.random() < 0.012:
                    bright = False
                target, sigma_l = 639.0, 80.0
            else:
                if random.random() < 0.02:
                    bright = True
                target, sigma_l = 28.0, 5.0
            
            current = _ou_step(current, target, theta=0.01, sigma=sigma_l,
                               lo=0, hi=100000)
            vals[i] = current
    
    return vals


def generate_stgen_voltage(n: int, motes: int = 54) -> np.ndarray:
    """Voltage: OU process with slow discharge drift."""
    per_mote = n // motes
    vals = np.zeros(n)
    
    for m in range(motes):
        start = m * per_mote
        end = start + per_mote
        v_mean = random.gauss(2.56, 0.08)
        current = v_mean
        
        for i in range(start, min(end, n)):
            v_mean -= 0.00001  # slow discharge
            current = _ou_step(current, v_mean, theta=0.001, sigma=0.005,
                               lo=1.5, hi=3.5)
            vals[i] = current
    
    return vals


# ---------------------------------------------------------------------------
# Quantitative Metrics
# ---------------------------------------------------------------------------

def compute_rmse(real: np.ndarray, synth: np.ndarray) -> float:
    """Root Mean Square Error."""
    if len(real) != len(synth):
        n = min(len(real), len(synth))
        real, synth = real[:n], synth[:n]
    return float(np.sqrt(np.mean((real - synth) ** 2)))


def compute_mae(real: np.ndarray, synth: np.ndarray) -> float:
    """Mean Absolute Error."""
    if len(real) != len(synth):
        n = min(len(real), len(synth))
        real, synth = real[:n], synth[:n]
    return float(np.mean(np.abs(real - synth)))


def compute_ks_test(real: np.ndarray, synth: np.ndarray) -> Dict[str, float]:
    """Two-sample Kolmogorov-Smirnov test.
    
    Tests if two samples come from the same distribution.
    Returns D-statistic and p-value.
    """
    d, p = sp_stats.ks_2samp(real, synth)
    return {"D_statistic": float(d), "p_value": float(p)}


def compute_moments(arr: np.ndarray) -> Dict[str, float]:
    """Compute mean, std, skewness, kurtosis."""
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=1)),
        "skew": float(sp_stats.skew(arr)),
        "kurtosis": float(sp_stats.kurtosis(arr)),
    }


def compute_trend_variance(series: np.ndarray, window: int = TREND_WINDOW) -> Tuple[np.ndarray, np.ndarray]:
    """Compute trend line (moving average) and residual variance."""
    if len(series) < window:
        return series, np.zeros_like(series)
    
    trend = uniform_filter1d(series, size=window, mode='nearest')
    residuals = series - trend
    return trend, np.abs(residuals)


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def plot_time_series_overlay(physical: np.ndarray, synthetic: np.ndarray,
                             modality: str, unit: str, n_samples: int = TIME_WINDOW_SAMPLES):
    """Create time-series overlay plot with trend lines."""
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), dpi=DPI)
    
    # 1. Find the safe maximum index by checking the length of BOTH arrays
    max_safe_len = min(len(physical), len(synthetic))
    
    # 2. Calculate the start index within safe bounds
    if max_safe_len > n_samples:
        start_idx = np.random.randint(0, max_safe_len - n_samples)
        phys_window = physical[start_idx : start_idx + n_samples]
        synth_window = synthetic[start_idx : start_idx + n_samples]
    else:
        phys_window = physical[:max_safe_len]
        synth_window = synthetic[:max_safe_len]
        
    time_indices = np.arange(len(phys_window))
    
    # --- Top panel: Full traces with trend lines ---
    ax1 = axes[0]
    ax1.plot(time_indices, phys_window, 'C0-', linewidth=1.5, alpha=ALPHA_PHYSICAL,
             label='Intel Physical Trace')
    ax1.plot(time_indices, synth_window, 'C1--', linewidth=1.5, alpha=ALPHA_SYNTHETIC,
             label='STGen Synthetic Trace')
    
    # Add trend lines
    phys_trend, _ = compute_trend_variance(phys_window, TREND_WINDOW)
    synth_trend, _ = compute_trend_variance(synth_window, TREND_WINDOW)
    ax1.plot(time_indices, phys_trend, 'C0-', linewidth=2.5, alpha=0.9,
             label='Physical Trend')
    ax1.plot(time_indices, synth_trend, 'C1-', linewidth=2.5, alpha=0.9,
             label='Synthetic Trend')
    
    ax1.set_xlabel('Sample Index (time)', fontsize=11, fontweight='bold')
    ax1.set_ylabel(f'{modality} ({unit})', fontsize=11, fontweight='bold')
    ax1.set_title(f'Time-Series Overlay: {modality} - Physical vs Synthetic', 
                  fontsize=12, fontweight='bold', pad=10)
    ax1.legend(loc='best', fontsize=10, framealpha=0.95)
    ax1.grid(True, alpha=0.3, linestyle='--')
    
    # --- Bottom panel: Zoomed-in view (first 200 samples) ---
    ax2 = axes[1]
    zoom_n = min(200, len(time_indices))
    zoom_idx = time_indices[:zoom_n]
    zoom_phys = phys_window[:zoom_n]
    zoom_synth = synth_window[:zoom_n]
    
    ax2.plot(zoom_idx, zoom_phys, 'C0o-', linewidth=2, markersize=4, alpha=ALPHA_PHYSICAL,
             label='Intel Physical Trace')
    ax2.plot(zoom_idx, zoom_synth, 'C1s--', linewidth=2, markersize=4, alpha=ALPHA_SYNTHETIC,
             label='STGen Synthetic Trace')
    
    ax2.fill_between(zoom_idx, zoom_phys, zoom_synth, alpha=0.15, color='gray',
                     label='Discrepancy Region')
    
    ax2.set_xlabel('Sample Index (time)', fontsize=11, fontweight='bold')
    ax2.set_ylabel(f'{modality} ({unit})', fontsize=11, fontweight='bold')
    ax2.set_title(f'Zoomed View (First {zoom_n} Samples)', fontsize=11, fontweight='bold', pad=10)
    ax2.legend(loc='best', fontsize=10, framealpha=0.95)
    ax2.grid(True, alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    outpath = OUTPUT_DIR / f"visual_overlay_{modality.lower()}.png"
    plt.savefig(outpath, dpi=DPI, bbox_inches='tight')
    print(f"    Saved: {outpath}")
    plt.close()


def plot_distribution_comparison(physical: np.ndarray, synthetic: np.ndarray,
                                 modality: str, unit: str):
    """Create histogram + Q-Q plot for distribution comparison."""
    
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), dpi=DPI)
    
    # --- Histogram ---
    ax1 = axes[0]
    lo, hi = np.percentile(np.concatenate([physical, synthetic]), [1, 99])
    bins = np.linspace(lo, hi, 60)
    
    ax1.hist(physical, bins=bins, alpha=0.6, label='Intel Physical', color='C0', edgecolor='black', linewidth=0.5)
    ax1.hist(synthetic, bins=bins, alpha=0.6, label='STGen Synthetic', color='C1', edgecolor='black', linewidth=0.5)
    ax1.set_xlabel(f'{modality} ({unit})', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    ax1.set_title('Distribution Comparison (Histogram)', fontsize=11, fontweight='bold')
    ax1.legend(fontsize=10, framealpha=0.95)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # --- Q-Q Plot ---
    ax2 = axes[1]
    quantiles = np.linspace(0, 1, 100)
    phys_quantiles = np.quantile(physical, quantiles)
    synth_quantiles = np.quantile(synthetic, quantiles)
    
    ax2.plot(phys_quantiles, synth_quantiles, 'o-', markersize=4, alpha=0.7, color='C2', linewidth=1.5)
    
    # Diagonal reference line
    lim_min = min(phys_quantiles.min(), synth_quantiles.min())
    lim_max = max(phys_quantiles.max(), synth_quantiles.max())
    ax2.plot([lim_min, lim_max], [lim_min, lim_max], 'k--', linewidth=2, alpha=0.5, label='Perfect Agreement')
    
    ax2.set_xlabel(f'Intel Physical Quantiles ({unit})', fontsize=11, fontweight='bold')
    ax2.set_ylabel(f'STGen Synthetic Quantiles ({unit})', fontsize=11, fontweight='bold')
    ax2.set_title('Q-Q Plot (Distribution Agreement)', fontsize=11, fontweight='bold')
    ax2.legend(fontsize=10, framealpha=0.95)
    ax2.grid(True, alpha=0.3)
    ax2.set_aspect('equal', adjustable='box')
    
    plt.tight_layout()
    outpath = OUTPUT_DIR / f"distribution_{modality.lower()}.png"
    plt.savefig(outpath, dpi=DPI, bbox_inches='tight')
    print(f"    Saved: {outpath}")
    plt.close()


def plot_error_analysis(physical: np.ndarray, synthetic: np.ndarray,
                        modality: str, unit: str):
    """Create error distribution plot."""
    
    if len(physical) != len(synthetic):
        n = min(len(physical), len(synthetic))
        physical, synthetic = physical[:n], synthetic[:n]
    
    errors = physical - synthetic
    abs_errors = np.abs(errors)
    
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), dpi=DPI)
    
    # --- Signed Error Distribution ---
    ax1 = axes[0]
    ax1.hist(errors, bins=60, alpha=0.7, color='C3', edgecolor='black', linewidth=0.5)
    ax1.axvline(np.mean(errors), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(errors):.4f}')
    ax1.axvline(np.median(errors), color='orange', linestyle='--', linewidth=2, label=f'Median: {np.median(errors):.4f}')
    ax1.set_xlabel(f'Error: Intel - STGen ({unit})', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    ax1.set_title('Signed Error Distribution', fontsize=11, fontweight='bold')
    ax1.legend(fontsize=10, framealpha=0.95)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # --- Absolute Error Timeline ---
    ax2 = axes[1]
    sample_idx = np.arange(min(len(abs_errors), 5000))
    ax2.plot(sample_idx, abs_errors[:5000], 'C3-', alpha=0.6, linewidth=1)
    ax2.axhline(np.mean(abs_errors), color='red', linestyle='--', linewidth=2, label=f'MAE: {np.mean(abs_errors):.4f}')
    ax2.fill_between(sample_idx, 0, abs_errors[:5000], alpha=0.2, color='C3')
    ax2.set_xlabel('Sample Index (time)', fontsize=11, fontweight='bold')
    ax2.set_ylabel(f'Absolute Error ({unit})', fontsize=11, fontweight='bold')
    ax2.set_title('Absolute Error Over Time', fontsize=11, fontweight='bold')
    ax2.legend(fontsize=10, framealpha=0.95)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    outpath = OUTPUT_DIR / f"error_analysis_{modality.lower()}.png"
    plt.savefig(outpath, dpi=DPI, bbox_inches='tight')
    print(f"    Saved: {outpath}")
    plt.close()


# ---------------------------------------------------------------------------
# Main Analysis
# ---------------------------------------------------------------------------

def main():
    """Run complete fidelity analysis pipeline."""
    
    print("\n" + "="*80)
    print("Intel Berkeley Dataset Fidelity Analysis: Visual + Quantitative")
    print("="*80 + "\n")
    
    # Load Intel data
    intel_df = load_intel_data()
    
    # Extract per-modality data
    print("\n[Extracting] Modality-specific traces from Intel data …")
    intel_temp = intel_df["temperature"].values
    intel_hum = intel_df["humidity"].values
    intel_light = intel_df["light"].values
    intel_volt = intel_df["voltage"].values
    
    # Generate STGen synthetic traces
    print("\n[Generating] STGen synthetic traces …")
    print("    Temperature & Humidity (MVOU)…")
    stgen_temp, stgen_hum = generate_mvou_temp_hum(N_STGEN_SAMPLES, N_STGEN_MOTES)
    
    print("    Light (bimodal OU)…")
    stgen_light = generate_stgen_light(N_STGEN_SAMPLES, N_STGEN_MOTES)
    
    print("    Voltage (OU with drift)…")
    stgen_volt = generate_stgen_voltage(N_STGEN_SAMPLES, N_STGEN_MOTES)
    
    # Prepare results table
    results = []
    
    # ========================================================================
    # TEMPERATURE ANALYSIS
    # ========================================================================
    print("\n" + "-"*80)
    print("TEMPERATURE ANALYSIS")
    print("-"*80)
    
    rmse_temp = compute_rmse(intel_temp, stgen_temp)
    mae_temp = compute_mae(intel_temp, stgen_temp)
    ks_temp = compute_ks_test(intel_temp, stgen_temp)
    
    print(f"\n  RMSE:           {rmse_temp:.6f} °C")
    print(f"  MAE:            {mae_temp:.6f} °C")
    print(f"  K-S D-statistic: {ks_temp['D_statistic']:.6f}")
    print(f"  K-S p-value:     {ks_temp['p_value']:.6f}")
    
    print("\n  Physical (Intel) moments:")
    intel_temp_stats = compute_moments(intel_temp)
    for k, v in intel_temp_stats.items():
        print(f"    {k:12s}: {v:10.6f}")
    
    print("\n  Synthetic (STGen) moments:")
    stgen_temp_stats = compute_moments(stgen_temp)
    for k, v in stgen_temp_stats.items():
        print(f"    {k:12s}: {v:10.6f}")
    
    results.append({
        "Modality": "Temperature",
        "Unit": "°C",
        "RMSE": rmse_temp,
        "MAE": mae_temp,
        "KS_D": ks_temp['D_statistic'],
        "KS_p": ks_temp['p_value'],
        "Intel_Mean": intel_temp_stats['mean'],
        "Intel_Std": intel_temp_stats['std'],
        "STGen_Mean": stgen_temp_stats['mean'],
        "STGen_Std": stgen_temp_stats['std'],
    })
    
    plot_time_series_overlay(intel_temp, stgen_temp, "Temperature", "°C")
    plot_distribution_comparison(intel_temp, stgen_temp, "Temperature", "°C")
    plot_error_analysis(intel_temp, stgen_temp, "Temperature", "°C")
    
    # ========================================================================
    # HUMIDITY ANALYSIS
    # ========================================================================
    print("\n" + "-"*80)
    print("HUMIDITY ANALYSIS")
    print("-"*80)
    
    rmse_hum = compute_rmse(intel_hum, stgen_hum)
    mae_hum = compute_mae(intel_hum, stgen_hum)
    ks_hum = compute_ks_test(intel_hum, stgen_hum)
    
    print(f"\n  RMSE:           {rmse_hum:.6f} %")
    print(f"  MAE:            {mae_hum:.6f} %")
    print(f"  K-S D-statistic: {ks_hum['D_statistic']:.6f}")
    print(f"  K-S p-value:     {ks_hum['p_value']:.6f}")
    
    print("\n  Physical (Intel) moments:")
    intel_hum_stats = compute_moments(intel_hum)
    for k, v in intel_hum_stats.items():
        print(f"    {k:12s}: {v:10.6f}")
    
    print("\n  Synthetic (STGen) moments:")
    stgen_hum_stats = compute_moments(stgen_hum)
    for k, v in stgen_hum_stats.items():
        print(f"    {k:12s}: {v:10.6f}")
    
    results.append({
        "Modality": "Humidity",
        "Unit": "%",
        "RMSE": rmse_hum,
        "MAE": mae_hum,
        "KS_D": ks_hum['D_statistic'],
        "KS_p": ks_hum['p_value'],
        "Intel_Mean": intel_hum_stats['mean'],
        "Intel_Std": intel_hum_stats['std'],
        "STGen_Mean": stgen_hum_stats['mean'],
        "STGen_Std": stgen_hum_stats['std'],
    })
    
    plot_time_series_overlay(intel_hum, stgen_hum, "Humidity", "%")
    plot_distribution_comparison(intel_hum, stgen_hum, "Humidity", "%")
    plot_error_analysis(intel_hum, stgen_hum, "Humidity", "%")
    
    # ========================================================================
    # LIGHT ANALYSIS
    # ========================================================================
    print("\n" + "-"*80)
    print("LIGHT ANALYSIS")
    print("-"*80)
    
    rmse_light = compute_rmse(intel_light, stgen_light)
    mae_light = compute_mae(intel_light, stgen_light)
    ks_light = compute_ks_test(intel_light, stgen_light)
    
    print(f"\n  RMSE:           {rmse_light:.6f} lux")
    print(f"  MAE:            {mae_light:.6f} lux")
    print(f"  K-S D-statistic: {ks_light['D_statistic']:.6f}")
    print(f"  K-S p-value:     {ks_light['p_value']:.6f}")
    
    print("\n  Physical (Intel) moments:")
    intel_light_stats = compute_moments(intel_light)
    for k, v in intel_light_stats.items():
        print(f"    {k:12s}: {v:10.6f}")
    
    print("\n  Synthetic (STGen) moments:")
    stgen_light_stats = compute_moments(stgen_light)
    for k, v in stgen_light_stats.items():
        print(f"    {k:12s}: {v:10.6f}")
    
    results.append({
        "Modality": "Light",
        "Unit": "lux",
        "RMSE": rmse_light,
        "MAE": mae_light,
        "KS_D": ks_light['D_statistic'],
        "KS_p": ks_light['p_value'],
        "Intel_Mean": intel_light_stats['mean'],
        "Intel_Std": intel_light_stats['std'],
        "STGen_Mean": stgen_light_stats['mean'],
        "STGen_Std": stgen_light_stats['std'],
    })
    
    plot_time_series_overlay(intel_light, stgen_light, "Light", "lux")
    plot_distribution_comparison(intel_light, stgen_light, "Light", "lux")
    plot_error_analysis(intel_light, stgen_light, "Light", "lux")
    
    # ========================================================================
    # VOLTAGE ANALYSIS
    # ========================================================================
    print("\n" + "-"*80)
    print("VOLTAGE ANALYSIS")
    print("-"*80)
    
    rmse_volt = compute_rmse(intel_volt, stgen_volt)
    mae_volt = compute_mae(intel_volt, stgen_volt)
    ks_volt = compute_ks_test(intel_volt, stgen_volt)
    
    print(f"\n  RMSE:           {rmse_volt:.6f} V")
    print(f"  MAE:            {mae_volt:.6f} V")
    print(f"  K-S D-statistic: {ks_volt['D_statistic']:.6f}")
    print(f"  K-S p-value:     {ks_volt['p_value']:.6f}")
    
    print("\n  Physical (Intel) moments:")
    intel_volt_stats = compute_moments(intel_volt)
    for k, v in intel_volt_stats.items():
        print(f"    {k:12s}: {v:10.6f}")
    
    print("\n  Synthetic (STGen) moments:")
    stgen_volt_stats = compute_moments(stgen_volt)
    for k, v in stgen_volt_stats.items():
        print(f"    {k:12s}: {v:10.6f}")
    
    results.append({
        "Modality": "Voltage",
        "Unit": "V",
        "RMSE": rmse_volt,
        "MAE": mae_volt,
        "KS_D": ks_volt['D_statistic'],
        "KS_p": ks_volt['p_value'],
        "Intel_Mean": intel_volt_stats['mean'],
        "Intel_Std": intel_volt_stats['std'],
        "STGen_Mean": stgen_volt_stats['mean'],
        "STGen_Std": stgen_volt_stats['std'],
    })
    
    plot_time_series_overlay(intel_volt, stgen_volt, "Voltage", "V")
    plot_distribution_comparison(intel_volt, stgen_volt, "Voltage", "V")
    plot_error_analysis(intel_volt, stgen_volt, "Voltage", "V")
    
    # ========================================================================
    # Summary Report
    # ========================================================================
    print("\n" + "="*80)
    print("SUMMARY TABLE")
    print("="*80)
    
    results_df = pd.DataFrame(results)
    print("\n" + results_df.to_string(index=False))
    
    # Save CSV
    csv_path = OUTPUT_DIR / "metrics_summary.csv"
    results_df.to_csv(csv_path, index=False)
    print(f"\n  Metrics saved: {csv_path}")
    
    # K-S Test Interpretation
    print("\n" + "-"*80)
    print("K-S TEST INTERPRETATION")
    print("-"*80)
    print("\nKolmogorov-Smirnov two-sample test compares empirical CDFs.")
    print("  p-value > 0.05: Distributions likely drawn from same source ✓")
    print("  p-value ≤ 0.05: Distributions significantly different")
    print()
    
    for idx, row in results_df.iterrows():
        mod = row["Modality"]
        p_val = row["KS_p"]
        d_stat = row["KS_D"]
        status = "✓ PASS" if p_val > 0.05 else "✗ FAIL"
        print(f"  {mod:12s}  D={d_stat:.6f}  p={p_val:.6f}  {status}")
    
    print("\n" + "="*80)
    print("Analysis complete! Check results/fidelity/ for plots and metrics.")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()