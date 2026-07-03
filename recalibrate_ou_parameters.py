#!/usr/bin/env python3
##! @file recalibrate_ou_parameters.py
##! @brief Recalibrate Ornstein-Uhlenbeck process parameters based on Intel data
##!
##! @details
##! Analyzes Intel Berkeley dataset to extract optimal OU parameters
##! that match real temperature dynamics.
##!
##! @author STGen Development Team
##! @version 1.0
##! @date 2024

import sys
import numpy as np
import pandas as pd
import math
from pathlib import Path
from scipy import stats

def analyze_intel_temperatures(filepath: str, limit: int = None) -> dict:
    """Analyze Intel dataset to extract OU parameters."""
    
    print("[*] Loading Intel dataset...")
    
    df = pd.read_csv(
        filepath,
        sep=r'\s+',
        header=None,
        names=['timestamp', 'mote_id', 'field', 'temp', 'humidity', 'light', 'voltage'],
        nrows=limit,
        dtype={'mote_id': int, 'temp': float, 'humidity': float, 'light': float, 'voltage': float},
        on_bad_lines='skip'
    )
    
    # Clean data
    df = df.dropna(subset=['temp', 'humidity'])
    df = df[(df['temp'] >= 10) & (df['temp'] <= 40)]
    df = df[(df['humidity'] >= 0) & (df['humidity'] <= 100)]
    
    print(f"[*] Loaded {len(df):,} valid records")
    
    # Extract temperatures
    temps = df['temp'].values
    hums = df['humidity'].values
    
    # Compute statistics
    mean_temp = np.mean(temps)
    std_temp = np.std(temps)
    
    # ACF at lag 1
    acf_lag1 = np.corrcoef(temps[:-1], temps[1:])[0, 1]
    
    # Humidity-temperature correlation
    corr_hum_temp = np.corrcoef(hums, temps)[0, 1]
    
    # Derive OU parameters
    # For OU process: ACF(1) = exp(-theta * dt)
    # If dt = 1 (normalized), then theta = -ln(ACF(1))
    theta_derived = -math.log(max(acf_lag1, 0.001))  # Avoid log(0)
    
    # For OU: stationary variance = sigma^2 / (2*theta)
    # Therefore: sigma = sqrt(2 * theta * variance)
    variance = std_temp ** 2
    sigma_derived = math.sqrt(2 * theta_derived * variance)
    
    results = {
        'mean': mean_temp,
        'std': std_temp,
        'acf_lag1': acf_lag1,
        'hum_temp_corr': corr_hum_temp,
        'theta': theta_derived,
        'sigma': sigma_derived,
        'variance': variance,
        'n_samples': len(temps)
    }
    
    return results


def print_calibration_report(params: dict):
    """Print calibration report for updating sensor_generator.py."""
    
    print("\n" + "="*70)
    print("CALIBRATION REPORT FOR OU PROCESS")
    print("="*70 + "\n")
    
    print(f"Based on {params['n_samples']:,} Intel Berkeley samples:\n")
    
    print("CURRENT TEMPERATURE STATISTICS:")
    print(f"  Mean:                  {params['mean']:.2f}°C")
    print(f"  Standard Deviation:    {params['std']:.2f}°C")
    print(f"  ACF(1):                {params['acf_lag1']:.4f}")
    print(f"  Humidity-Temp Corr:    {params['hum_temp_corr']:.4f}\n")
    
    print("RECOMMENDED OU PARAMETERS:")
    print(f"  theta (mean reversion): {params['theta']:.6f}")
    print(f"    (was: 0.002000)")
    print(f"    Interpretation: 1/{params['theta']:.1f} ≈ {1/params['theta']:.0f} time constants to mean\n")
    
    print(f"  sigma (volatility):     {params['sigma']:.6f}")
    print(f"    (was: 0.150000)")
    print(f"    Expected steady-state std: {params['sigma'] / math.sqrt(2*params['theta']):.3f}°C\n")
    
    print("CODE TO UPDATE sensor_generator.py:")
    print("-"*70)
    print(f"""
# Lines 672-680 (in generate_sensor_stream):
states[i] = {{
    "temp_mean": temp_mean,
    "temp_current": temp_mean + random.gauss(0, 1),
    "ou_theta": {params['theta']:.6f},    # UPDATED: was 0.002
    "ou_sigma": {params['sigma']:.6f},    # UPDATED: was 0.15
    ...
}}
    """.strip())
    
    print("\n" + "-"*70)
    print("VALIDATION TARGETS:")
    print(f"  ✓ ACF(1) should be ≈ {params['acf_lag1']:.4f} (exp(-{params['theta']:.6f}))")
    print(f"  ✓ Steady-state std should be ≈ {params['std']:.2f}°C")
    print(f"  ✓ Humidity-temp correlation should be ≈ {params['hum_temp_corr']:.4f}")


if __name__ == "__main__":
    intel_file = "Intel_dataset/data.txt"
    
    if not Path(intel_file).exists():
        print(f"Error: {intel_file} not found")
        sys.exit(1)
    
    params = analyze_intel_temperatures(intel_file)
    print_calibration_report(params)
    
    # Save to JSON
    import json
    with open("results/ou_calibration.json", "w") as f:
        json.dump({k: float(v) if isinstance(v, (int, float, np.number)) else v 
                   for k, v in params.items()}, f, indent=2)
    
    print("\n[+] Calibration parameters saved to results/ou_calibration.json")
