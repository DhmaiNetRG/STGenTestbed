# # # stgen/sensor_generator.py
# # """
# # Multi-Sensor Traffic Stream Generator
# # Generates realistic IoT sensor data streams with varied timing patterns.
# # """

# # import random
# # import time
# # from typing import Generator, Tuple, Dict, Any


# # def generate_sensor_stream(cfg: Dict[str, Any]) -> Generator[Tuple[str, Dict[str, Any], float], None, None]:
# #     """
# #     Generate realistic sensor data stream.
    
# #     Args:
# #         cfg: Configuration with keys:
# #             - duration: Test duration in seconds
# #             - num_clients: Number of sensor clients
# #             - sensors: List of sensor types
    
# #     Yields:
# #         Tuple of (client_id, data_dict, timeout)
# #         where timeout is inter-packet delay
# #     """
# #     dur = cfg.get("duration", 30)
# #     num = cfg.get("num_clients", 4)
# #     sensors = cfg.get("sensors", ["temp", "gps", "device", "camera"])
    
# #     start = time.time()
# #     seq = 0
    
# #     # Initialize client states
# #     states = {}
# #     for i in range(num):
# #         cid = f"client_{i}"
# #         states[cid] = {
# #             "mean": random.uniform(-30, 50),      # Temperature baseline
# #             "motion": random.choice([0, 1]),       # Motion state
# #             "lat": 23.8 + random.uniform(-0.5, 0.5),  # GPS latitude
# #             "lon": 90.4 + random.uniform(-0.5, 0.5)   # GPS longitude
# #         }
    
# #     while time.time() - start < dur:
# #         for i in range(num):
# #             cid = f"client_{i}"
# #             seq += 1
# #             seq %= 65536  # Wrap at 16-bit boundary
            
# #             sensor = sensors[i % len(sensors)]
            
# #             # Generate sensor-specific data and timing
# #             if sensor == "temp":
# #                 # Temperature: Normal distribution with slow drift
# #                 val = round(random.normalvariate(states[cid]["mean"], 10), 1)
# #                 states[cid]["mean"] += random.uniform(-0.1, 0.1)  # Drift
# #                 data = f"{val} C"
# #                 to = 1.0  # 1 Hz
                
# #             elif sensor == "device":
# #                 # Binary device state (ON/OFF)
# #                 data = random.choice(["OFF", "ON"])
# #                 to = random.uniform(0.1, 5)  # Irregular
                
# #             elif sensor == "gps":
# #                 # GPS coordinates with random walk
# #                 states[cid]["lat"] += random.uniform(-0.001, 0.001)
# #                 states[cid]["lon"] += random.uniform(-0.001, 0.001)
# #                 data = f"[{states[cid]['lat']:.6f}, {states[cid]['lon']:.6f}]"
# #                 to = 5.0  # 0.2 Hz
                
# #             elif sensor == "camera":
# #                 # Motion detection camera (burst on motion)
# #                 if states[cid]["motion"]:
# #                     data = "MOTION_DETECTED"
# #                     to = 0.067  # ~15 fps during motion
                    
# #                     # Random motion end
# #                     if random.random() > 0.95:
# #                         states[cid]["motion"] = 0
# #                 else:
# #                     data = "NO_MOTION"
# #                     to = random.uniform(1, 10)  # Low rate when idle
                    
# #                     # Random motion start
# #                     if random.random() > 0.8:
# #                         states[cid]["motion"] = 1
            
# #             elif sensor == "humidity":
# #                 # Humidity sensor (correlated with temp)
# #                 base_hum = 50 + (states[cid]["mean"] - 20) * 0.5
# #                 val = round(random.normalvariate(base_hum, 5), 1)
# #                 data = f"{val}%"
# #                 to = 2.0  # 0.5 Hz
            
# #             elif sensor == "motion":
# #                 # PIR motion sensor (binary)
# #                 data = random.choice(["MOTION", "STILL"])
# #                 to = random.uniform(0.5, 3)
            
# #             else:
# #                 data = "UNKNOWN"
# #                 to = 1.0
            
# #             # Package sensor reading
# #             payload = {
# #                 "dev_id": f"{sensor}_{i}",
# #                 "ts": time.time(),
# #                 "seq_no": seq,
# #                 "sensor_data": data
# #             }
            
# #             yield (cid, payload, to)
            
# #             # Break if duration exceeded
# #             if time.time() - start >= dur:
# #                 return



# # stgen/sensor_generator.py
# """
# Sensor data generator for IoT testing.
# Generates realistic sensor readings based on sensor type.
# """

# import random
# import time
# from typing import Dict, Any, Generator, Tuple


# def generate_sensor_value(sensor_type: str) -> Dict[str, Any]:
#     """
#     Generate realistic sensor data based on type.
    
#     Args:
#         sensor_type: Type of sensor (temp, humidity, motion, etc.)
    
#     Returns:
#         Dictionary with sensor-specific data
#     """
#     if sensor_type == "temp" or sensor_type == "temperature":
#         return {
#             "value": round(random.uniform(15.0, 35.0), 2),
#             "unit": "C"
#         }
    
#     elif sensor_type == "humidity":
#         return {
#             "value": round(random.uniform(30.0, 80.0), 2),
#             "unit": "%"
#         }
    
#     elif sensor_type == "motion" or sensor_type == "pir":
#         return {
#             "detected": random.choice([True, False]),
#             "confidence": round(random.uniform(0.5, 1.0), 2)
#         }
    
#     elif sensor_type == "light" or sensor_type == "lux":
#         return {
#             "value": round(random.uniform(0, 1000), 2),
#             "unit": "lux"
#         }
    
#     elif sensor_type == "pressure":
#         return {
#             "value": round(random.uniform(980, 1040), 2),
#             "unit": "hPa"
#         }
    
#     elif sensor_type == "gps" or sensor_type == "location":
#         return {
#             "latitude": round(random.uniform(-90, 90), 6),
#             "longitude": round(random.uniform(-180, 180), 6),
#             "altitude": round(random.uniform(0, 500), 2)
#         }
    
#     elif sensor_type == "accelerometer" or sensor_type == "accel":
#         return {
#             "x": round(random.uniform(-10, 10), 3),
#             "y": round(random.uniform(-10, 10), 3),
#             "z": round(random.uniform(-10, 10), 3),
#             "unit": "m/s²"
#         }
    
#     elif sensor_type == "gyroscope" or sensor_type == "gyro":
#         return {
#             "x": round(random.uniform(-250, 250), 2),
#             "y": round(random.uniform(-250, 250), 2),
#             "z": round(random.uniform(-250, 250), 2),
#             "unit": "°/s"
#         }
    
#     elif sensor_type == "camera" or sensor_type == "image":
#         return {
#             "resolution": "1920x1080",
#             "format": "JPEG",
#             "size_kb": random.randint(50, 500)
#         }
    
#     elif sensor_type == "sound" or sensor_type == "audio":
#         return {
#             "level": round(random.uniform(30, 90), 2),
#             "unit": "dB"
#         }
    
#     elif sensor_type == "vibration":
#         return {
#             "frequency": round(random.uniform(10, 100), 2),
#             "amplitude": round(random.uniform(0, 10), 2),
#             "unit": "Hz"
#         }
    
#     elif sensor_type == "co2":
#         return {
#             "value": round(random.uniform(400, 1000), 2),
#             "unit": "ppm"
#         }
    
#     elif sensor_type == "voltage":
#         return {
#             "value": round(random.uniform(3.0, 5.0), 2),
#             "unit": "V"
#         }
    
#     else:
#         # Generic fallback for unknown sensor types
#         return {
#             "value": round(random.uniform(0, 100), 2),
#             "type": sensor_type,
#             "unit": "generic"
#         }


# # def generate_sensor_stream(cfg: Dict[str, Any]) -> Generator[Tuple[str, Dict, float], None, None]:
# #     """
# #     Generate a stream of sensor readings.
    
# #     Args:
# #         cfg: Configuration dictionary with:
# #             - num_clients: Number of sensor devices
# #             - duration: Test duration in seconds
# #             - sensors: List of sensor types
    
# #     Yields:
# #         Tuple of (client_id, data_dict, sleep_interval)
# #     """
# #     num_clients = cfg.get("num_clients", 4)
# #     duration = cfg.get("duration", 30)
# #     sensor_types = cfg.get("sensors", ["temp", "humidity", "motion"])
    
# #     # Ensure sensor_types is a list
# #     if isinstance(sensor_types, str):
# #         sensor_types = [sensor_types]
    
# #     # Calculate rate
# #     msgs_per_sec = cfg.get("rate", 1.0)  # messages per second per client
# #     interval = 1.0 / msgs_per_sec if msgs_per_sec > 0 else 1.0
    
# #     start_time = time.time()
# #     seq_no = 0

# #     total_messages_to_send = num_clients * 50
# #     # Generate device assignments
# #     devices = []
# #     for i in range(num_clients):
# #         sensor_type = sensor_types[i % len(sensor_types)]
# #         devices.append({
# #             "id": i,
# #             "type": sensor_type,
# #             "dev_id": f"{sensor_type}_{i}"
# #         })


    
# #     # Generate data stream
# #     # while (time.time() - start_time) < duration:
# #     #     for device in devices:
# #     #         seq_no += 1
            
# #     #         # Generate sensor reading
# #     #         sensor_data = generate_sensor_value(device["type"])
            
# #     #         # Create data packet
# #     #         data = {
# #     #             "dev_id": device["dev_id"],
# #     #             "ts": time.time(),
# #     #             "seq_no": seq_no,
# #     #             "sensor_data": sensor_data
# #     #         }
            
# #     #         client_id = f"client_{device['id']}"
            
# #     #         yield (client_id, data, interval)
    
# #     # # Final log
# #     # elapsed = time.time() - start_time
# #     # print(f"\nSensor stream complete: {seq_no} messages in {elapsed:.1f}s")
# #     while seq_no < total_messages_to_send:  # <--- CHANGED
# #         for device in devices:
# #             if seq_no >= total_messages_to_send: # <--- ADDED
# #                 break
                
# #             seq_no += 1
# #             # ... (rest of loop) ...
# #             yield (client_id, data, interval)
            
# #         if seq_no >= total_messages_to_send: # <--- ADDED
# #             break
            
# #     # Final log
# #     elapsed = time.time() - start_time
# #     print(f"\nSensor stream complete: {seq_no} messages in {elapsed:.1f}s")
# def generate_sensor_stream(cfg: Dict[str, Any]) -> Generator[Tuple[str, Dict, float], None, None]:
#     """
#     Generate a stream of sensor readings.
    
#     Args:
#         cfg: Configuration dictionary with:
#             - num_clients: Number of sensor devices
#             - duration: Test duration in seconds (NOW USED AS A TIMEOUT)
#             - sensors: List of sensor types
#             - packets_per_client: (NEW) Number of packets each client should send
#     """
#     num_clients = cfg.get("num_clients", 4)
#     duration_timeout = cfg.get("duration", 300) # Use duration as a safety timeout
#     sensor_types = cfg.get("sensors", ["temp", "humidity", "motion"])
    
#     # --- THIS IS THE NEW, CRITICAL LOGIC ---
#     # We will send 50 packets per client.
#     # For your 100-client scenario, this will be 5000 packets.
#     # This creates a FAIR test.
#     packets_per_client = cfg.get("packets_per_client", 50)
#     total_messages_to_send = num_clients * packets_per_client
#     # --- END NEW LOGIC ---

#     if isinstance(sensor_types, str):
#         sensor_types = [sensor_types]
    
#     msgs_per_sec = cfg.get("rate", 1.0)
#     interval = 1.0 / msgs_per_sec if msgs_per_sec > 0 else 1.0
    
#     start_time = time.time()
#     seq_no = 0
    
#     devices = []
#     for i in range(num_clients):
#         sensor_type = sensor_types[i % len(sensor_types)]
#         devices.append({
#             "id": i,
#             "type": sensor_type,
#             "dev_id": f"{sensor_type}_{i}"
#         })
    
#     # Generate data stream
#     # --- LOOP IS NOW BASED ON PACKET COUNT, NOT DURATION ---
#     while seq_no < total_messages_to_send:
        
#         # Safety timeout
#         if (time.time() - start_time) > duration_timeout:
#              print(f"\nSensor stream TIMED OUT after {duration_timeout}s")
#              break
             
#         for device in devices:
#             if seq_no >= total_messages_to_send:
#                 break
                
#             seq_no += 1
            
#             sensor_data = generate_sensor_value(device["type"])
            
#             data = {
#                 "dev_id": device["dev_id"],
#                 "ts": time.time(),
#                 "seq_no": seq_no,
#                 "sensor_data": sensor_data
#             }
            
#             client_id = f"client_{device['id']}"
            
#             yield (client_id, data, interval)

#         if seq_no >= total_messages_to_send:
#             break
    
#     # Final log
#     elapsed = time.time() - start_time
#     print(f"\nSensor stream complete: {seq_no} messages in {elapsed:.1f}s")

# def generate_burst_stream(cfg: Dict[str, Any]) -> Generator[Tuple[str, Dict, float], None, None]:
#     """
#     Generate bursty sensor traffic (for stress testing).
#     Alternates between high and low activity periods.
#     """
#     num_clients = cfg.get("num_clients", 4)
#     duration = cfg.get("duration", 30)
#     sensor_types = cfg.get("sensors", ["temp", "humidity"])
    
#     burst_rate = cfg.get("burst_rate", 10)  # msgs/sec during burst
#     idle_rate = cfg.get("idle_rate", 0.1)   # msgs/sec during idle
#     burst_duration = cfg.get("burst_duration", 5)  # seconds
#     idle_duration = cfg.get("idle_duration", 10)   # seconds
    
#     start_time = time.time()
#     seq_no = 0
#     in_burst = True
#     phase_start = start_time
    
#     devices = []
#     for i in range(num_clients):
#         sensor_type = sensor_types[i % len(sensor_types)]
#         devices.append({
#             "id": i,
#             "type": sensor_type,
#             "dev_id": f"{sensor_type}_{i}"
#         })
    
#     while (time.time() - start_time) < duration:
#         # Switch phases
#         phase_elapsed = time.time() - phase_start
#         if in_burst and phase_elapsed > burst_duration:
#             in_burst = False
#             phase_start = time.time()
#         elif not in_burst and phase_elapsed > idle_duration:
#             in_burst = True
#             phase_start = time.time()
        
#         # Set rate based on phase
#         rate = burst_rate if in_burst else idle_rate
#         interval = 1.0 / (rate * num_clients)
        
#         for device in devices:
#             seq_no += 1
#             sensor_data = generate_sensor_value(device["type"])
            
#             data = {
#                 "dev_id": device["dev_id"],
#                 "ts": time.time(),
#                 "seq_no": seq_no,
#                 "sensor_data": sensor_data
#             }
            
#             client_id = f"client_{device['id']}"
#             yield (client_id, data, interval)


# # For backward compatibility
# def parse_sensor_types(sensor_str: str) -> list:
#     """
#     Parse sensor type string into list.
#     Supports both simple format ("temp,humidity") and distribution format ("temp:40,humidity:30").
    
#     Args:
#         sensor_str: Comma-separated sensor types
    
#     Returns:
#         List of sensor type names
#     """
#     if not sensor_str:
#         return ["temp", "humidity", "motion"]
    
#     sensors = []
#     for item in sensor_str.split(","):
#         # Handle distribution format (temp:40)
#         if ":" in item:
#             sensor_type = item.split(":")[0].strip()
#         else:
#             sensor_type = item.strip()
        
#         if sensor_type and sensor_type not in sensors:
#             sensors.append(sensor_type)
    
#     return sensors



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
# EQUATION 1: Ornstein-Uhlenbeck Process for Temperature
# =============================================================================
# dT = θ(μ - T)dt + σdW
# 
# Where:
#   θ (theta) = mean reversion rate
#   μ (mu) = long-term mean temperature  
#   σ (sigma) = volatility
#   dW = Wiener process increment ~ N(0, dt)
# =============================================================================

def _ou_temperature(current: float, mean: float, dt: float = 1.0) -> float:
    """Ornstein-Uhlenbeck temperature update."""
    theta = 0.1
    sigma = 0.5
    dW = random.gauss(0, 1) * math.sqrt(dt)
    dT = theta * (mean - current) * dt + sigma * dW
    
    # Constrain rate of change (max 0.5°C/min)
    max_rate = 0.5 / 60
    dT = max(-max_rate * dt, min(max_rate * dt, dT))
    
    return current + dT


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
    if sensor_type in ["temp", "temperature"]:
        if state and "temp_current" in state:
            state["temp_current"] = _ou_temperature(
                state["temp_current"], 
                state.get("temp_mean", 22)
            )
            val = state["temp_current"]
        else:
            val = random.gauss(22, 3)
        return {"value": round(val, 2), "unit": "C"}
    
    elif sensor_type == "humidity":
        if state and "temp_current" in state:
            # Humidity inversely correlated with temperature
            base = 60 - (state["temp_current"] - 20) * 1.5
            val = base + random.gauss(0, 3)
        else:
            val = random.gauss(50, 10)
        return {"value": round(max(0, min(100, val)), 2), "unit": "%"}
    
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
        return {"value": round(random.uniform(0, 1000), 2), "unit": "lux"}
    
    elif sensor_type == "pressure":
        return {"value": round(random.gauss(1013, 10), 2), "unit": "hPa"}
    
    elif sensor_type in ["gps", "location"]:
        if state:
            # Velocity-constrained movement
            v_max = state.get("gps_vmax", 2.0)  # m/s (walking default)
            dt = 1.0
            max_delta = (v_max * dt) / 111000  # degrees
            
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0, 1)
            
            state["gps_lat"] = state.get("gps_lat", 23.8) + max_delta * speed * math.cos(angle)
            state["gps_lon"] = state.get("gps_lon", 90.4) + max_delta * speed * math.sin(angle)
            
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
        return {"level": round(random.gauss(50, 15), 2), "unit": "dB"}
    
    elif sensor_type == "vibration":
        return {"frequency": round(random.uniform(10, 100), 2), "amplitude": round(random.uniform(0, 10), 2), "unit": "Hz"}
    
    elif sensor_type == "co2":
        return {"value": round(random.gauss(600, 100), 2), "unit": "ppm"}
    
    elif sensor_type == "voltage":
        return {"value": round(random.gauss(3.7, 0.2), 2), "unit": "V"}
    
    else:
        return {"value": round(random.uniform(0, 100), 2), "type": sensor_type, "unit": "generic"}


# =============================================================================
# MAIN STREAM GENERATOR (Compatible with main.py)
# =============================================================================

def generate_sensor_stream(cfg: Dict[str, Any]) -> Generator[Tuple[str, Dict, float], None, None]:
    """
    Generate a stream of sensor readings with physical validation.
    
    Implements:
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
    packets_per_client = cfg.get("packets_per_client", 50)
    
    # Weibull parameters for inter-arrival time
    weibull_k = cfg.get("weibull_k", 0.8)      # k < 1 = bursty
    weibull_scale = cfg.get("weibull_scale", 2.0)
    use_weibull = cfg.get("use_weibull_iat", True)
    
    if isinstance(sensor_types, str):
        sensor_types = [sensor_types]
    
    total_messages = num_clients * packets_per_client
    
    # Fallback rate if not using Weibull
    msgs_per_sec = cfg.get("rate", 1.0)
    fixed_interval = 1.0 / msgs_per_sec if msgs_per_sec > 0 else 1.0
    
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
        states[i] = {
            "temp_mean": random.uniform(18, 28),
            "temp_current": random.uniform(20, 25),
            "pir_last_trigger": 0,
            "pir_state": False,
            "gps_lat": 23.8 + random.uniform(-0.5, 0.5),
            "gps_lon": 90.4 + random.uniform(-0.5, 0.5),
            "gps_vmax": random.choice([1.5, 5.0, 15.0])  # walk/cycle/drive
        }
    
    # Generate data stream
    while seq_no < total_messages:
        # Safety timeout
        if (time.time() - start_time) > duration_timeout:
            print(f"\nSensor stream TIMED OUT after {duration_timeout}s")
            break
        
        for device in devices:
            if seq_no >= total_messages:
                break
            
            seq_no += 1
            
            # Generate sensor data with state
            sensor_data = generate_sensor_value(device["type"], states[device["id"]])
            
            # Calculate inter-arrival time
            if use_weibull:
                interval = _weibull_iat(k=weibull_k, scale=weibull_scale)
            else:
                interval = fixed_interval
            
            data = {
                "dev_id": device["dev_id"],
                "ts": time.time(),
                "seq_no": seq_no,
                "sensor_data": sensor_data
            }
            
            client_id = f"client_{device['id']}"
            yield (client_id, data, interval)
        
        if seq_no >= total_messages:
            break
    
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