"""
Platform-agnostic network emulation abstraction.
Routes to platform-specific implementations (Linux tc, macOS pfctl, Windows NetLimiter).
"""

import os
import sys
import json
import platform
import logging
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

_LOG = logging.getLogger("network_emulator_platform")


@dataclass
class NetworkConditions:
    """Immutable network condition specification."""
    latency_ms: int = 0
    jitter_ms: int = 0
    loss_pct: float = 0.0
    bandwidth_kbps: int = 0


class NetworkEmulatorBackend:
    """Abstract base for platform-specific implementations."""
    
    def __init__(self, interface: str):
        self.interface = interface
        self.enabled = False
        self.conditions: Optional[NetworkConditions] = None
    
    def apply(self, conditions: NetworkConditions) -> bool:
        """Apply network conditions. Return True on success."""
        raise NotImplementedError
    
    def reset(self) -> bool:
        """Remove all network conditions."""
        raise NotImplementedError
    
    def get_status(self) -> dict:
        """Get current emulation status."""
        return {
            "backend": self.__class__.__name__,
            "interface": self.interface,
            "enabled": self.enabled,
            "conditions": self.conditions.__dict__ if self.conditions else None
        }


class LinuxTcBackend(NetworkEmulatorBackend):
    """Linux tc (NetEm) implementation."""
    
    def apply(self, conditions: NetworkConditions) -> bool:
        """Apply using Linux tc command."""
        if not self._check_sudo():
            _LOG.warning("tc requires sudo on Linux")
            return False
        
        try:
            # Clear existing rules
            subprocess.run(
                ["sudo", "tc", "qdisc", "del", "dev", self.interface, "root"],
                stderr=subprocess.DEVNULL, check=False
            )
            
            if all(getattr(conditions, k) == 0 for k in ['latency_ms', 'jitter_ms', 'loss_pct', 'bandwidth_kbps']):
                self.enabled = False
                return True
            
            # Build tc command
            cmd = ["sudo", "tc", "qdisc", "add", "dev", self.interface, "root", "netem"]
            
            if conditions.latency_ms > 0:
                cmd.extend(["delay", f"{conditions.latency_ms}ms"])
                if conditions.jitter_ms > 0:
                    cmd.extend([f"{conditions.jitter_ms}ms"])
            
            if conditions.loss_pct > 0:
                cmd.extend(["loss", f"{min(100, conditions.loss_pct)}%"])
            
            # Bandwidth limiting (if needed)
            if conditions.bandwidth_kbps > 0:
                subprocess.run(
                    ["sudo", "tc", "qdisc", "del", "dev", self.interface, "root"],
                    stderr=subprocess.DEVNULL, check=False
                )
                kbps = conditions.bandwidth_kbps
                # Convert kbps to rate string (e.g., "1000kbit")
                rate_str = f"{kbps}kbit"
                subprocess.run(
                    ["sudo", "tc", "qdisc", "add", "dev", self.interface, "root", "tbf", 
                     "rate", rate_str, "burst", "32kbit", "latency", "400ms"],
                    check=True
                )
            else:
                subprocess.run(cmd, check=True)
            
            self.enabled = True
            self.conditions = conditions
            return True
        except subprocess.CalledProcessError as e:
            _LOG.error(f"tc command failed: {e}")
            return False
    
    def reset(self) -> bool:
        """Remove tc rules."""
        try:
            subprocess.run(
                ["sudo", "tc", "qdisc", "del", "dev", self.interface, "root"],
                stderr=subprocess.DEVNULL, check=False
            )
            self.enabled = False
            self.conditions = None
            return True
        except Exception as e:
            _LOG.error(f"Failed to reset tc: {e}")
            return False
    
    @staticmethod
    def _check_sudo() -> bool:
        """Check if sudo is available."""
        try:
            subprocess.run(["sudo", "-n", "true"], stderr=subprocess.DEVNULL, timeout=1)
            return True
        except:
            return False


class macOSPfctlBackend(NetworkEmulatorBackend):
    """macOS pfctl (packet filter) implementation."""
    
    PF_CONF_PATH = "/etc/pf.conf"
    PF_ANCHOR_NAME = "stgen"
    
    def apply(self, conditions: NetworkConditions) -> bool:
        """Apply using macOS pfctl."""
        if not self._check_sudo():
            _LOG.warning("pfctl requires sudo on macOS")
            return False
        
        try:
            # macOS pfctl does not support latency/jitter directly in the same way as Linux tc
            # We use dummynet for that
            if conditions.latency_ms > 0 or conditions.jitter_ms > 0:
                return self._apply_dummynet(conditions)
            elif conditions.loss_pct > 0:
                return self._apply_pfctl_loss(conditions)
            else:
                self.enabled = False
                return True
        except Exception as e:
            _LOG.error(f"pfctl backend failed: {e}")
            return False
    
    def _apply_dummynet(self, conditions: NetworkConditions) -> bool:
        """Apply latency/jitter using dummynet."""
        try:
            # Create dummynet pipe
            pipe_num = 1
            bandwidth = 10000  # 10Gbps (unlimited for latency testing)
            
            cmd = f"ipfw pipe {pipe_num} config"
            if conditions.latency_ms > 0:
                cmd += f" delay {conditions.latency_ms}ms"
            if conditions.jitter_ms > 0:
                cmd += f" jitter {conditions.jitter_ms}ms"
            if conditions.loss_pct > 0:
                cmd += f" plr {conditions.loss_pct / 100.0}"
            
            subprocess.run(["sudo", "ipfw", "pipe", str(pipe_num), "delete"],
                          stderr=subprocess.DEVNULL, check=False)
            
            parts = cmd.split()
            subprocess.run(["sudo"] + parts, check=True)
            
            # Route traffic through pipe
            subprocess.run(["sudo", "ipfw", "add", "1000", "pipe", str(pipe_num), "all"],
                          check=True)
            
            self.enabled = True
            self.conditions = conditions
            return True
        except subprocess.CalledProcessError as e:
            _LOG.error(f"dummynet setup failed: {e}")
            return False
    
    def _apply_pfctl_loss(self, conditions: NetworkConditions) -> bool:
        """Apply packet loss using pfctl."""
        try:
            subprocess.run(["sudo", "pfctl", "-e"], stderr=subprocess.DEVNULL, check=False)
            # pfctl packet loss is complex; defer to dummynet approach
            return self._apply_dummynet(conditions)
        except subprocess.CalledProcessError as e:
            _LOG.error(f"pfctl loss setup failed: {e}")
            return False
    
    def reset(self) -> bool:
        """Remove dummynet rules."""
        try:
            subprocess.run(["sudo", "ipfw", "flush"], check=False)
            subprocess.run(["sudo", "pfctl", "-d"], check=False)
            self.enabled = False
            self.conditions = None
            return True
        except Exception as e:
            _LOG.error(f"Failed to reset pfctl: {e}")
            return False
    
    @staticmethod
    def _check_sudo() -> bool:
        """Check if sudo is available."""
        try:
            subprocess.run(["sudo", "-n", "true"], stderr=subprocess.DEVNULL, timeout=1)
            return True
        except:
            return False


class WindowsNetLimiterBackend(NetworkEmulatorBackend):
    """Windows NetLimiter CLI implementation."""
    
    NETLIMITER_CMD = "NetLimiter"  # Assumes NetLimiter is in PATH
    
    def apply(self, conditions: NetworkConditions) -> bool:
        """Apply using NetLimiter CLI (requires NetLimiter 4+)."""
        try:
            # NetLimiter doesn't have a standard CLI; using WMI/PowerShell fallback
            return self._apply_powershell(conditions)
        except Exception as e:
            _LOG.error(f"NetLimiter backend failed: {e}")
            return False
    
    def _apply_powershell(self, conditions: NetworkConditions) -> bool:
        """Apply using Windows PowerShell/NDIS layer (experimental)."""
        try:
            if conditions.latency_ms > 0:
                # NetShell (deprecated but still works on older Windows)
                cmd = (
                    f"netsh interface tcp set supplemental subject=internet "
                    f"congestionprovider=none"
                )
                subprocess.run(["powershell", "-Command", cmd], check=False)
            
            _LOG.warning("Windows network emulation is experimental. "
                        "Install NetLimiter 4+ for reliable operation.")
            self.enabled = False  # Mark as not reliably enabled
            return False
        except Exception as e:
            _LOG.error(f"PowerShell network emulation failed: {e}")
            return False
    
    def reset(self) -> bool:
        """No-op on Windows (too risky without dedicated tools)."""
        self.enabled = False
        self.conditions = None
        return True


class PlatformNetworkEmulator:
    """Factory: Creates platform-appropriate network emulator."""
    
    @staticmethod
    def create(interface: str = "eth0") -> NetworkEmulatorBackend:
        """Create platform-specific backend."""
        system = platform.system()
        
        _LOG.info(f"Detected platform: {system}")
        
        if system == "Linux":
            return LinuxTcBackend(interface)
        elif system == "Darwin":  # macOS
            return macOSPfctlBackend(interface)
        elif system == "Windows":
            return WindowsNetLimiterBackend(interface)
        else:
            _LOG.error(f"Unsupported platform: {system}")
            raise RuntimeError(f"Network emulation not supported on {system}")


def get_platform_info() -> dict:
    """Return current platform info and capabilities."""
    system = platform.system()
    release = platform.release()
    
    capabilities = {
        "Linux": {
            "method": "tc (NetEm)",
            "latency": "✓",
            "jitter": "✓",
            "loss": "✓",
            "bandwidth": "✓",
            "requires": "sudo, iproute2"
        },
        "Darwin": {
            "method": "pfctl + dummynet",
            "latency": "✓",
            "jitter": "⚠ (via dummynet)",
            "loss": "✓",
            "bandwidth": "⚠",
            "requires": "sudo"
        },
        "Windows": {
            "method": "NetLimiter CLI (optional)",
            "latency": "✗",
            "jitter": "✗",
            "loss": "✗",
            "bandwidth": "✗",
            "requires": "NetLimiter 4+ (manual install)"
        }
    }
    
    return {
        "system": system,
        "release": release,
        "capabilities": capabilities.get(system, {"method": "Unknown", "requires": "Unknown"}),
        "recommended": "Install platform-specific tools for full functionality"
    }
