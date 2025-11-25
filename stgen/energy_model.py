# stgen/energy_model.py
"""
Energy consumption modeling for battery-powered IoT devices.
"""

import logging
from typing import Dict, Any

_LOG = logging.getLogger("energy_model")

class EnergyModel:
    """Estimate energy consumption based on traffic patterns."""
    
    # --------------------------------------------------------------------
    # --- PHYSICAL DEVICE ASSUMPTIONS (CRITICAL: TUNE THESE) ---
    # --------------------------------------------------------------------
    
    # Power draw in milliwatts (mW) for each state.
    # These are EXAMPLES for a low-power device (e.g., LoRaWAN)
    POWER_PROFILES = {
        "tx": 50,      # mW during transmission
        "rx": 30,      # mW during reception (listen window)
        "idle": 0.5,   # mW during idle (CPU on, radio off)
        "sleep": 0.01  # mW during deep sleep
    }

    # Time-on-air and processing time in seconds (s).
    # These are EXAMPLES. You MUST adjust them for your scenario.
    TIME_PER_TX_S = 0.150   # 150ms Time-on-Air
    TIME_PER_RX_S = 0.100   # 100ms listen window for ACK
    TIME_IDLE_PER_EVENT_S = 0.5 # 500ms for sensor read + processing
    
    # Battery configuration
    BATTERY_MAH = 2000 # 2000 mAh
    VOLTAGE = 3.3      # 3.3V
    # --------------------------------------------------------------------


    def estimate_battery_life(self, 
                             traffic_pattern: Dict[str, Any], 
                             sim_results: Dict[str, Any], 
                             duration_s: int) -> float:
        """
        Estimate battery lifetime in days based on traffic and simulation results.
        
        Args:
            traffic_pattern: The "traffic_pattern" dict from the scenario JSON.
            sim_results: The 'summary.json' dict from the orchestrator.
            duration_s: The total duration of the test in seconds.
            
        Returns:
            Estimated battery lifetime in days.
        """
        
        total_events_per_day = 0
        
        # --- MODIFIED LOGIC ---
        # 1. Prioritize ACTUAL sent packets from the simulation
        packets_sent_in_test = sim_results.get("sent", 0)
        
        if packets_sent_in_test > 0 and duration_s > 0:
            # Calculate events/day based on real test performance
            rate_hz = packets_sent_in_test / duration_s
            total_events_per_day = rate_hz * 3600 * 24
            _LOG.info(f"Model: Calculating based on *actual* sim results ({packets_sent_in_test} packets in {duration_s}s)")
            
        # 2. Fallback to traffic_pattern if 'sent' is 0
        elif traffic_pattern:
            _LOG.warning("No packets sent in sim, falling back to 'traffic_pattern' estimate.")
            for sensor, config in traffic_pattern.items():
                rate_hz = config.get("rate_hz", 0)
                events_per_day = rate_hz * 3600 * 24
                total_events_per_day += events_per_day
        # --- END MODIFIED LOGIC ---
        
        if total_events_per_day == 0:
            _LOG.warning("No traffic events found, cannot estimate battery life.")
            return float('inf')
            
        _LOG.info(f"Model: Calculating for {total_events_per_day:.2f} events/day.")

        # --- (Rest of the function is the same) ---
        
        # 2. Calculate total time (in seconds) spent PER DAY in each state
        total_time_tx_s = total_events_per_day * self.TIME_PER_TX_S
        total_time_rx_s = total_events_per_day * self.TIME_PER_RX_S
        total_time_idle_s = total_events_per_day * self.TIME_IDLE_PER_EVENT_S
        
        total_awake_time_s = total_time_tx_s + total_time_rx_s + total_time_idle_s
        total_seconds_in_day = 24 * 3600
        total_sleep_time_s = total_seconds_in_day - total_awake_time_s
        
        if total_sleep_time_s < 0:
            total_sleep_time_s = 0
            total_time_idle_s = total_seconds_in_day - total_time_tx_s - total_time_rx_s
            
        # 3. Convert time (sec) to energy (mWh)
        energy_tx_mwh = self.POWER_PROFILES["tx"] * (total_time_tx_s / 3600)
        energy_rx_mwh = self.POWER_PROFILES["rx"] * (total_time_rx_s / 3600)
        energy_idle_mwh = self.POWER_PROFILES["idle"] * (total_time_idle_s / 3600)
        energy_sleep_mwh = self.POWER_PROFILES["sleep"] * (total_sleep_time_s / 3600)
        
        total_energy_per_day_mwh = energy_tx_mwh + energy_rx_mwh + energy_idle_mwh + energy_sleep_mwh
        
        if total_energy_per_day_mwh == 0:
            return float('inf')
            
        _LOG.info(f"Model: Daily energy use: {total_energy_per_day_mwh:.4f} mWh")

        # 4. Calculate total battery capacity (mWh)
        total_battery_capacity_mwh = self.BATTERY_MAH * self.VOLTAGE
        
        # 5. Calculate final lifetime
        estimated_lifetime_days = total_battery_capacity_mwh / total_energy_per_day_mwh
        
        return estimated_lifetime_days