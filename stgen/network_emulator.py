##! @file network_emulator.py
##! @brief Network Condition Emulation Module (Cross-Platform)
##! 
##! @details
##! Provides realistic network condition emulation:
##! - Linux: tc (NetEm) - full support
##! - macOS: pfctl + dummynet - latency/loss/jitter
##! - Windows: experimental (NetLimiter optional)
##! Supports:
##! - Latency simulation (constant + jitter)
##! - Packet loss injection
##! - Bandwidth throttling (Linux only)
##! - JSON profile-based configuration
##!
##! @author STGen Development Team
##! @version 3.0 (Cross-Platform)
##! @date 2024

import subprocess
import logging
import json
import platform
from pathlib import Path
from typing import Dict, Any, Optional

from stgen.network_emulator_platform import (
    PlatformNetworkEmulator,
    NetworkConditions,
    get_platform_info
)

_LOG = logging.getLogger("network_emulator")


class NetworkEmulator:
    ##! @class NetworkEmulator
    ##! @brief Apply realistic network conditions from profiles (Cross-Platform)
    ##! @details
    ##! Uses platform-specific backends:
    ##! - Linux: tc/netem (full support)
    ##! - macOS: pfctl/dummynet (latency, jitter, loss)
    ##! - Windows: limited (NetLimiter optional)
    
    def __init__(self, interface: str = "eth0"):
        ##! @brief Initialize network emulator
        ##! @param interface Network interface name (default: eth0)
        self.interface = interface
        self.backend = None
        self.enabled = False
        self.profile_name = None
        self._init_backend(interface)
    
    def _init_backend(self, interface: str):
        """Initialize platform-specific backend."""
        try:
            self.backend = PlatformNetworkEmulator.create(interface)
            system = platform.system()
            
            # Log platform capabilities on first init
            info = get_platform_info()
            capabilities = info["capabilities"]
            _LOG.info(f"Network emulator: {system} ({capabilities.get('method', 'Unknown')})")
            
            if system == "Windows" and not all(v == "✓" for v in [
                capabilities.get("latency"),
                capabilities.get("jitter"),
                capabilities.get("loss")
            ]):
                _LOG.warning("Windows has limited network emulation. Consider running on Linux/macOS "
                           "for full fidelity or install NetLimiter 4+ for advanced features.")
        except RuntimeError as e:
            _LOG.error(f"Backend initialization failed: {e}")
            self.backend = None
    
    @classmethod
    def from_profile(cls, profile_path: str, interface: str = "eth0"):
        ##! @brief Load network conditions from profile file
        ##! @param profile_path Path to JSON profile
        ##! @param interface Network interface to apply to
        ##! @return NetworkEmulator instance configured with profile
        emulator = cls(interface)
        
        if not emulator.backend:
            _LOG.warning("Network emulator backend unavailable")
            return emulator
        
        profile = json.loads(Path(profile_path).read_text())
        
        success = emulator.apply_conditions(
            latency_ms=profile.get("latency_ms", 0),
            jitter_ms=profile.get("jitter_ms", 0),
            loss_pct=profile.get("loss_percent", 0),
            bandwidth_kbps=profile.get("bandwidth_kbps", 0)
        )
        
        emulator.profile_name = profile.get("name", "Unknown")
        
        # Log results AFTER apply_conditions completes
        if success and emulator.enabled:
            _LOG.info(f"✓ Applied profile: {emulator.profile_name} "
                     f"(latency={profile.get('latency_ms', 0)}ms, "
                     f"loss={profile.get('loss_percent', 0):.1f}%, "
                     f"bw={profile.get('bandwidth_kbps', 0)}kbps)")
        else:
            _LOG.warning(
                f"⚠ Profile '{emulator.profile_name}' could not be fully applied. "
                f"Test will run with reduced network emulation.\n"
                f"  Platform: {platform.system()}\n"
                f"  Required: {get_platform_info()['capabilities'].get('requires', 'unknown')}"
            )
        
        return emulator
    
    def apply_conditions(self, latency_ms: int = 0, jitter_ms: int = 0,
                        loss_pct: float = 0, bandwidth_kbps: int = 0) -> bool:
        """
        Apply network conditions using platform-specific backend.
        
        Args:
            latency_ms: Constant latency in milliseconds
            jitter_ms: Jitter range (±ms)
            loss_pct: Packet loss percentage (0-100)
            bandwidth_kbps: Bandwidth limit in kbps (0=unlimited)
        
        Returns:
            True if conditions were successfully applied, False otherwise
        """
        if not self.backend:
            _LOG.error("No network emulator backend available")
            return False
        
        conditions = NetworkConditions(
            latency_ms=latency_ms,
            jitter_ms=jitter_ms,
            loss_pct=loss_pct,
            bandwidth_kbps=bandwidth_kbps
        )
        
        success = self.backend.apply(conditions)
        self.enabled = success and self.backend.enabled
        
        if success:
            _LOG.debug(f"Network conditions applied: latency={latency_ms}ms±{jitter_ms}ms, "
                      f"loss={loss_pct}%, bw={bandwidth_kbps}kbps")
        else:
            _LOG.warning(f"Failed to apply network conditions on {platform.system()}")
        
        return success
    
    def clear(self) -> bool:
        """Remove network emulation."""
        if not self.backend:
            return False
        
        success = self.backend.reset()
        self.enabled = False
        
        if success:
            _LOG.info("Network emulation cleared")
        else:
            _LOG.warning("Failed to clear network emulation")
        
        return success
    
    def get_status(self) -> Dict[str, Any]:
        """Get current emulation status."""
        if not self.backend:
            return {"status": "unavailable"}
        
        return self.backend.get_status()