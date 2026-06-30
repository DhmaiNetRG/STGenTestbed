"""
! @file sensor_generator.py
! @brief Multi-Sensor Traffic Stream Generator for IoT Testing
! 
! @details
! Generates realistic IoT sensor data streams with:
! - Multiple sensor types (temperature, humidity, GPS, motion, etc.)
! - Varied timing patterns and inter-packet delays
! - Realistic packet sizes and payloads
! - Configurable client counts and duration
!
! @author STGen Development Team
! @version 2.0
! @date 2024
"""

"""
Physically-Validated IoT Sensor Data Generator
Implements statistical models aligned with real-world sensor behavior.

Key Equations Documented:
1. Thermal Drift: Ornstein-Uhlenbeck process
2. PIR Dwell Time: Hardware-constrained triggering  
3. Accelerometer: Gaussian noise with MEMS NSD
4. Inter-Arrival Time: Weibull distribution
5. GPS: Velocity-constrained random walk
"""

import random
import math
import time
from typing import Dict, Any, Generator, Tuple


# =============================================================================
# Optional multi-modal (Gaussian-mixture) light profile
# =============================================================================
# The default single-regime light model (below) underfits the strongly bimodal
# Intel Berkeley light distribution (held-out KS D = 0.33). A 5-component
# Gaussian mixture, fitted by EM on the IBRL light data, reduces the held-out
# KS D to 0.065 (see run_light_gmm_eval.py). The components correspond to the
# illumination regimes: off, dim, ambient, lit, and bright/saturated.
# Opt in per sensor by setting state["light_model"] = "gmm". The mixture is
# venue-specific; these weights/means are calibrated to the IBRL deployment.
IBRL_LIGHT_GMM = {
    "weights": [0.139, 0.410, 0.209, 0.183, 0.059],
    "means":   [0.8,   96.82, 432.08, 996.44, 1847.36],
    "sigmas":  [1.0,   66.19, 183.42, 419.41, 5.0],   # degenerate sigmas floored
}


def _light_gmm_value(state: Dict[str, Any], gmm: Dict[str, Any] = IBRL_LIGHT_GMM,
                     mean_dwell: int = 40) -> float:
    """Sample a light value from a Gaussian mixture with regime persistence.

    A component is held for a geometrically-distributed dwell (mean ``mean_dwell``
    steps) so the stream keeps temporal structure rather than i.i.d. flicker.
    """
    if state.get("light_gmm_dwell", 0) <= 0:
        state["light_gmm_comp"] = random.choices(
            range(len(gmm["weights"])), weights=gmm["weights"])[0]
        state["light_gmm_dwell"] = max(1, int(random.expovariate(1.0 / mean_dwell)))
    state["light_gmm_dwell"] -= 1
    k = state["light_gmm_comp"]
    return max(0.0, random.gauss(gmm["means"][k], gmm["sigmas"][k]))


# =============================================================================
# EQUATION 1: Ornstein-Uhlenbeck Process for Temperature
# =============================================================================
# dT = θ(μ - T)dt + σdW
# 
# Where:
#   θ (theta) = mean reversion rate
#   μ (mu) = long-term mean temperature  
#   σ (sigma) = volatility
#   dW = Wiener process increment ~ N(0, dt)
#
# Calibrated from Intel Berkeley Lab data (1.88M samples, 54-mote deployment):
#   - Mean: 22.18°C
#   - Per-mote std ≈ 3.38°C
#   - Lag-1 ACF ≈ 0.9272 (not 0.998 as previously assumed)
#   - Humidity-temp correlation ≈ -0.6075
# =============================================================================

# =============================================================================
# EQUATION 1b: Generic Ornstein-Uhlenbeck (reusable for any modality)
# =============================================================================

def _ou_step(current: float, mean: float, theta: float, sigma: float,
             dt: float = 1.0, lo: float = None, hi: float = None) -> float:
    """Generic OU process step with optional clamping."""
    dW = random.gauss(0, 1) * math.sqrt(dt)
    val = current + theta * (mean - current) * dt + sigma * dW
    if lo is not None:
        val = max(lo, val)
    if hi is not None:
        val = min(hi, val)
    return val


# =============================================================================
# EQUATION 2: PIR Hardware Dwell Time
# =============================================================================
# Constraint: t_trigger(n+1) - t_trigger(n) ≥ T_dwell + T_blocking
# For HC-SR501: T_dwell ≈ 3s, T_blocking ≈ 2.5s
# =============================================================================

T_DWELL = 3.0
T_BLOCKING = 2.5
MIN_PIR_INTERVAL = T_DWELL + T_BLOCKING


# =============================================================================
# EQUATION 3: MEMS Accelerometer Noise
# =============================================================================
# σ_noise = NSD × √(BW × 1.6)
# For MPU-6050: NSD = 400 μg/√Hz, BW = 260 Hz
# =============================================================================

ACCEL_NSD = 0.004  # m/s²/√Hz
ACCEL_BW = 260     # Hz
ACCEL_RMS_NOISE = ACCEL_NSD * math.sqrt(ACCEL_BW * 1.6)  # ≈ 0.08 m/s²

# Intel Mica2Dot traces are sampled approximately every 31s.
# OU parameters below are calibrated per Intel sample step, so in real-time
# streaming we scale elapsed wall-clock seconds by this reference interval.
INTEL_REFERENCE_STEP_SEC = 31.0


# =============================================================================
# EQUATION 4: Weibull Inter-Arrival Time
# =============================================================================
# t = λ × (-ln(U))^(1/k), where U ~ Uniform(0,1)
# k ≈ 0.8 for bursty IoT traffic
# =============================================================================

def _weibull_iat(k: float = 0.8, scale: float = 2.0) -> float:
    """Generate Weibull-distributed inter-arrival time."""
    u = max(random.random(), 1e-10)
    return scale * ((-math.log(u)) ** (1.0 / k))


def _normalize_ou_dt(elapsed_sec: float,
                     reference_sec: float = INTEL_REFERENCE_STEP_SEC,
                     min_dt: float = 1e-3,
                     max_dt: float = 10.0) -> float:
    """Convert elapsed wall-clock time to OU step units.

    Returns dt in "Intel-sample steps" where dt=1.0 corresponds to 31 seconds.
    """
    dt = elapsed_sec / reference_sec
    return max(min_dt, min(max_dt, dt))


def _scale_step_probability(p_step: float, dt_steps: float) -> float:
    """Scale per-step transition probability for non-unit dt.

    If p_step is defined for dt=1, then over dt_steps the equivalent is:
      p_eff = 1 - (1 - p_step) ** dt_steps
    """
    p_step = max(0.0, min(1.0, p_step))
    return 1.0 - ((1.0 - p_step) ** max(dt_steps, 0.0))


# =============================================================================
# EQUATION 5: Haversine Distance for GPS
# =============================================================================
# d = 2R × arcsin(√(sin²(Δφ/2) + cos(φ1)cos(φ2)sin²(Δλ/2)))
# =============================================================================

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two GPS points."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.asin(math.sqrt(a))


# =============================================================================
# SENSOR VALUE GENERATORS
# =============================================================================

def generate_sensor_value(sensor_type: str, state: dict = None) -> Dict[str, Any]:
    """
    Generate realistic sensor data based on type.
    
    Args:
        sensor_type: Type of sensor
        state: Optional state dict for temporal correlation
    
    Returns:
        Dictionary with sensor-specific data
    """
    if sensor_type in ["temp", "temperature", "humidity"]:
        if state and "temp_current" in state:
            # Check if we've already updated the MVOU SDE for this timestamp
            current_time = time.time()
            last_update = state.get("last_mvou_update", 0)

            # Only step the SDE forward if time has passed (atomic T+H update)
            if current_time - last_update > 0.001:
                elapsed = (current_time - last_update) if last_update > 0 else INTEL_REFERENCE_STEP_SEC
                dt = _normalize_ou_dt(elapsed)
                rho = -0.38  # Tuned: structural coupling + Cholesky ≈ -0.43

                # Independent Wiener increments
                dW1 = random.gauss(0, math.sqrt(dt))
                dW2 = random.gauss(0, math.sqrt(dt))

                # Correlated increments via Cholesky decomposition
                dZ_T = dW1
                dZ_H = rho * dW1 + math.sqrt(1 - rho**2) * dW2

                # Regime switching (HVAC/sunlight shifts)
                if random.random() < _scale_step_probability(0.001, dt):
                    state["temp_mean"] += random.gauss(0, 4)
                    state["temp_mean"] = max(15, min(40, state["temp_mean"]))

                mu_T = state.get("temp_mean", 22)
                mu_H = 53.8 - 0.64 * mu_T

                # Step temperature SDE
                state["temp_current"] += state.get("ou_theta", 0.002) * (mu_T - state["temp_current"]) * dt + state.get("ou_sigma", 0.15) * dZ_T

                # Step humidity SDE with STRONG correlation to temperature
                # Intel shows r=-0.6075: humidity = 53.8 - 0.64*temp
                # Use proportional drift to maintain correlation
                hum_drift = 0.05 * (mu_H - state["hum_current"]) * dt
                state["hum_current"] = max(0.0, min(100.0, state["hum_current"] + hum_drift + 0.15 * dZ_H))

                state["last_mvou_update"] = current_time

            # Return the requested sensor type
            if sensor_type in ["temp", "temperature"]:
                return {"value": round(state["temp_current"], 2), "unit": "C"}
            else:
                return {"value": round(state["hum_current"], 2), "unit": "%"}
        else:
            # Fallback for stateless calls
            if sensor_type in ["temp", "temperature"]:
                return {"value": round(random.gauss(22, 3), 2), "unit": "C"}
            return {"value": round(random.gauss(40, 6), 2), "unit": "%"}
    
    elif sensor_type in ["motion", "pir"]:
        current_time = time.time()
        if state:
            time_since = current_time - state.get("pir_last_trigger", 0)
            
            if state.get("pir_state", False):
                # In triggered state
                if time_since >= T_DWELL:
                    state["pir_state"] = False
                    return {"detected": False, "state": "blocking"}
                return {"detected": True, "state": "dwell"}
            else:
                # Can trigger only if past minimum interval
                if time_since >= MIN_PIR_INTERVAL and random.random() < 0.3:
                    state["pir_state"] = True
                    state["pir_last_trigger"] = current_time
                    return {"detected": True, "state": "triggered"}
                return {"detected": False, "state": "idle"}
        else:
            return {"detected": random.choice([True, False]), "confidence": round(random.uniform(0.5, 1.0), 2)}
    
    elif sensor_type in ["light", "lux"]:
        if state:
            # Opt-in multi-modal profile: 5-component Gaussian mixture fitted to
            # the IBRL deployment (held-out KS D = 0.065 vs 0.33 for the default).
            if state.get("light_model") == "gmm":
                return {"value": round(_light_gmm_value(state), 2), "unit": "lux"}
            # Default single-regime bimodal OU: switches between dark/bright.
            # Calibrated from Intel data: dark μ≈28, bright μ≈639
            if "light_current" not in state:
                state["light_current"] = random.choice([28.0, 639.0])
                state["light_regime"] = state["light_current"] > 300

            current_time = time.time()
            last_light_update = state.get("last_light_update", 0)
            elapsed = (current_time - last_light_update) if last_light_update > 0 else INTEL_REFERENCE_STEP_SEC
            dt = _normalize_ou_dt(elapsed)
            
            # Regime switching (~2% dark→bright, ~1.2% bright→dark per step)
            if state["light_regime"]:
                if random.random() < _scale_step_probability(0.012, dt):
                    state["light_regime"] = False
                target = 639.0
                sigma_l = 80.0
            else:
                if random.random() < _scale_step_probability(0.02, dt):
                    state["light_regime"] = True
                target = 28.0
                sigma_l = 5.0
            
            state["light_current"] = _ou_step(
                state["light_current"], target,
                theta=0.01, sigma=sigma_l, dt=dt,
                lo=0, hi=100000
            )
            state["last_light_update"] = current_time
            return {"value": round(state["light_current"], 2), "unit": "lux"}
        return {"value": round(random.uniform(0, 1000), 2), "unit": "lux"}
    
    elif sensor_type == "pressure":
        return {"value": round(random.gauss(1013, 10), 2), "unit": "hPa"}
    
    elif sensor_type in ["gps", "location"]:
        if state:
            # Velocity-constrained movement
            v_max = state.get("gps_vmax", 2.0)  # m/s (walking default)
            current_time = time.time()
            last_gps_update = state.get("last_gps_update", 0)
            dt_sec = (current_time - last_gps_update) if last_gps_update > 0 else 1.0
            dt_sec = max(0.05, min(5.0, dt_sec))
            max_delta = (v_max * dt_sec) / 111000  # degrees
            
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0, 1)
            
            state["gps_lat"] = state.get("gps_lat", 23.8) + max_delta * speed * math.cos(angle)
            state["gps_lon"] = state.get("gps_lon", 90.4) + max_delta * speed * math.sin(angle)
            state["last_gps_update"] = current_time
            
            return {
                "latitude": round(state["gps_lat"], 6),
                "longitude": round(state["gps_lon"], 6),
                "velocity_mps": round(v_max * speed, 2)
            }
        return {
            "latitude": round(random.uniform(-90, 90), 6),
            "longitude": round(random.uniform(-180, 180), 6),
            "altitude": round(random.uniform(0, 500), 2)
        }
    
    elif sensor_type in ["accelerometer", "accel"]:
        # MEMS noise model (Equation 3)
        return {
            "x": round(random.gauss(0, ACCEL_RMS_NOISE), 4),
            "y": round(random.gauss(0, ACCEL_RMS_NOISE), 4),
            "z": round(random.gauss(9.81, ACCEL_RMS_NOISE), 4),
            "unit": "m/s²"
        }
    
    elif sensor_type in ["gyroscope", "gyro"]:
        return {
            "x": round(random.gauss(0, 0.5), 2),
            "y": round(random.gauss(0, 0.5), 2),
            "z": round(random.gauss(0, 0.5), 2),
            "unit": "°/s"
        }
    
    elif sensor_type in ["camera", "image"]:
        return {"resolution": "1920x1080", "format": "JPEG", "size_kb": random.randint(50, 500)}
    
    elif sensor_type in ["sound", "audio"]:
        return {"value": round(random.gauss(50, 15), 2), "unit": "dB"}
    
    elif sensor_type == "vibration":
        return {"frequency": round(random.uniform(10, 100), 2), "amplitude": round(random.uniform(0, 10), 2), "unit": "Hz"}
    
    elif sensor_type == "co2":
        return {"value": round(random.gauss(600, 100), 2), "unit": "ppm"}
    
    elif sensor_type == "voltage":
        if state:
            # OU process for voltage with slow discharge drift
            # Calibrated: Mica2Dot Li-ion μ≈2.56V, σ≈0.12V
            if "volt_current" not in state:
                state["volt_current"] = state.get("volt_mean", 2.56)
            
            # Slow downward drift (battery discharge)
            state["volt_mean"] = state.get("volt_mean", 2.56) - 0.00001
            
            state["volt_current"] = _ou_step(
                state["volt_current"],
                state.get("volt_mean", 2.56),
                theta=0.001,
                sigma=0.005,
                lo=1.5, hi=3.5
            )
            return {"value": round(state["volt_current"], 2), "unit": "V"}
        return {"value": round(random.gauss(2.56, 0.12), 2), "unit": "V"}
    
    else:
        return {"value": round(random.uniform(0, 100), 2), "type": sensor_type, "unit": "generic"}


# =============================================================================
# MAIN STREAM GENERATOR (Compatible with main.py)
# =============================================================================

def generate_sensor_stream(cfg: Dict[str, Any]) -> Generator[Tuple[str, Dict, float], None, None]:
    """
    Generate a stream of sensor readings with physical validation.
    
    Implements:
    - Parse traffic_pattern for rate configuration
    - Ornstein-Uhlenbeck temperature (temporal correlation)
    - PIR dwell time constraints (hardware limits)
    - MEMS accelerometer noise model
    - Weibull inter-arrival times (bursty traffic)
    - Velocity-constrained GPS
    
    Args:
        cfg: Configuration dictionary with:
            - num_clients: Number of sensor devices
            - duration: Test duration in seconds (timeout)
            - sensors: List of sensor types
            - packets_per_client: Packets each client sends
            - weibull_k: Shape parameter for IAT (default 0.8)
            - weibull_scale: Scale parameter for IAT (default 2.0)
    
    Yields:
        Tuple of (client_id, data_dict, sleep_interval)
    """
    num_clients = cfg.get("num_clients", 4)
    duration_timeout = cfg.get("duration", 300)
    sensor_types = cfg.get("sensors", ["temp", "humidity", "motion"])
    
    # Weibull parameters for inter-arrival time
    weibull_k = cfg.get("weibull_k", 0.8)      # k < 1 = bursty
    weibull_scale = cfg.get("weibull_scale", 2.0)
    use_weibull = cfg.get("use_weibull_iat", False) # Default to False for steady comparisons

    # Optional deterministic seeding for reproducible streams / labelled datasets.
    # Only seeds when explicitly requested, so default runs keep their behaviour.
    seed = cfg.get("seed")
    if seed is not None:
        random.seed(seed)

    # Optional adversarial / anomaly injection (data-plane false-data injection).
    # When no "adversarial" block is present this stays None and the stream is
    # byte-identical to the non-adversarial path.
    anomaly = None
    adv = cfg.get("adversarial")
    if adv and adv.get("enabled", True):
        try:
            from .anomaly_injector import AnomalyInjector
            anomaly = AnomalyInjector(adv, num_clients=num_clients)
        except Exception as _exc:  # never let injection break normal generation
            anomaly = None

    if isinstance(sensor_types, str):
        sensor_types = [sensor_types]
    
    # Determine Rate per Client (Hz)
    # Use the MINIMUM rate across all sensors so the stream lasts at least
    # duration_timeout seconds. Using the first (or fastest) rate would cause
    # the stream to exhaust total_messages far too early.
    traffic_pattern = cfg.get("traffic_pattern", {})
    rates_in_pattern = [
        float(p["rate_hz"])
        for p in traffic_pattern.values()
        if isinstance(p, dict) and "rate_hz" in p
    ]

    if rates_in_pattern:
        per_client_rate = min(rates_in_pattern)  # slowest sensor drives the budget
    else:
        per_client_rate = float(cfg.get("rate", 1.0))
        
    # Calculate Total Messages
    # Use duration if provided to calculate total messages, otherwise fallback to packets_per_client
    if cfg.get("duration"):
        total_messages = int(duration_timeout * per_client_rate * num_clients)
        # Add buffer to ensure we cover limits
        total_messages = int(total_messages * 1.1)
    else:
        packets_per_client = cfg.get("packets_per_client", 50)
        total_messages = num_clients * packets_per_client
    
    # Calculate Global Interval 
    # Logic: ORCHESTRATOR SLEEPS AFTER EACH YIELD.
    # To achieve N * R messages per second total, we must sleep 1 / (N*R) s
    if per_client_rate > 0:
        global_rate = per_client_rate * num_clients
        fixed_interval = 1.0 / global_rate
    else:
        fixed_interval = 1.0

    start_time = time.time()
    seq_no = 0
    
    # Initialize device states for temporal correlation
    devices = []
    states = {}
    for i in range(num_clients):
        sensor_type = sensor_types[i % len(sensor_types)]
        dev_id = f"{sensor_type}_{i}"
        devices.append({"id": i, "type": sensor_type, "dev_id": dev_id})
        
        # Initialize state for this device
        # Temperature: per-mote mean drawn from N(22.2, 1.0) matching Intel
        # Range of real mote means: 20.0 – 24.5°C
        temp_mean = random.gauss(22.2, 1.0)
        temp_mean = max(18, min(30, temp_mean))
        states[i] = {
            "temp_mean": temp_mean,
            "temp_current": temp_mean + random.gauss(0, 1),
            "ou_theta": 0.075541,     # RECALIBRATED: was 0.002, ACF(1) ≈ 0.9272
            "ou_sigma": 1.312685,     # RECALIBRATED: was 0.15, std ≈ 3.38°C
            "hum_current": 53.8 - 0.64 * temp_mean + random.gauss(0, 3),
            "last_mvou_update": 0.0,
            "volt_mean": random.gauss(2.56, 0.08),
            "volt_current": random.gauss(2.56, 0.08),
            "pir_last_trigger": 0,
            "pir_state": False,
            "gps_lat": 23.8 + random.uniform(-0.5, 0.5),
            "gps_lon": 90.4 + random.uniform(-0.5, 0.5),
            "last_gps_update": 0.0,
            "last_light_update": 0.0,
            "gps_vmax": random.choice([1.5, 5.0, 15.0])  # walk/cycle/drive
        }
    
    # Generate data stream
    # Round-robin selection of devices (fair scheduling)
    # Using endless generator logic usually, but here bound by total_messages or time
    
    while seq_no < total_messages:
        # Safety timeout
        if (time.time() - start_time) > duration_timeout:
            # print(f"\nSensor stream TIMED OUT after {duration_timeout}s")
            break
        
        # In each pass, we pick ONE device to send, then sleep
        # We rotate through devices
        
        device_idx = seq_no % num_clients
        device = devices[device_idx]
        
        seq_no += 1
        
        # Generate sensor data with state
        sensor_data = generate_sensor_value(device["type"], states[device["id"]])

        # Optional adversarial perturbation (false-data injection). Adds a
        # ground-truth "label" only when injection is active.
        gt_label = None
        if anomaly is not None:
            sensor_data, gt_label = anomaly.maybe_inject(
                device["id"], device["dev_id"], device["type"],
                sensor_data, time.time() - start_time, seq_no)

        # Calculate inter-arrival time
        if use_weibull:
            # Note: Weibull scaling needs to adapt to global rate too if used
            interval = _weibull_iat(k=weibull_k, scale=fixed_interval)
        else:
            interval = fixed_interval

        data = {
            "dev_id": device["dev_id"],
            "ts": time.time(),
            "seq_no": seq_no, # Global sequence
            "client_seq": (seq_no // num_clients) + 1, # Per-client sequence approximation
            "sensor_data": sensor_data
        }
        if gt_label is not None:
            data["label"] = gt_label

        client_id = f"client_{device['id']}"
        yield (client_id, data, interval)

    if anomaly is not None:
        anomaly.close()
    elapsed = time.time() - start_time
    print(f"\nSensor stream complete: {seq_no} messages in {elapsed:.1f}s")


def generate_burst_stream(cfg: Dict[str, Any]) -> Generator[Tuple[str, Dict, float], None, None]:
    """Generate bursty sensor traffic for stress testing."""
    num_clients = cfg.get("num_clients", 4)
    duration = cfg.get("duration", 30)
    sensor_types = cfg.get("sensors", ["temp", "humidity"])
    
    burst_rate = cfg.get("burst_rate", 10)
    idle_rate = cfg.get("idle_rate", 0.1)
    burst_duration = cfg.get("burst_duration", 5)
    idle_duration = cfg.get("idle_duration", 10)
    
    start_time = time.time()
    seq_no = 0
    in_burst = True
    phase_start = start_time
    
    if isinstance(sensor_types, str):
        sensor_types = [sensor_types]
    
    devices = []
    for i in range(num_clients):
        sensor_type = sensor_types[i % len(sensor_types)]
        devices.append({"id": i, "type": sensor_type, "dev_id": f"{sensor_type}_{i}"})
    
    while (time.time() - start_time) < duration:
        phase_elapsed = time.time() - phase_start
        if in_burst and phase_elapsed > burst_duration:
            in_burst = False
            phase_start = time.time()
        elif not in_burst and phase_elapsed > idle_duration:
            in_burst = True
            phase_start = time.time()
        
        rate = burst_rate if in_burst else idle_rate
        interval = 1.0 / (rate * num_clients)
        
        for device in devices:
            seq_no += 1
            sensor_data = generate_sensor_value(device["type"])
            
            data = {
                "dev_id": device["dev_id"],
                "ts": time.time(),
                "seq_no": seq_no,
                "sensor_data": sensor_data
            }
            
            yield (f"client_{device['id']}", data, interval)


def parse_sensor_types(sensor_str: str) -> list:
    """Parse sensor type string into list."""
    if not sensor_str:
        return ["temp", "humidity", "motion"]
    
    sensors = []
    for item in sensor_str.split(","):
        if ":" in item:
            sensor_type = item.split(":")[0].strip()
        else:
            sensor_type = item.strip()
        
        if sensor_type and sensor_type not in sensors:
            sensors.append(sensor_type)
    
    return sensors