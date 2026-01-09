# protocols/my_udp/my_udp.py
"""
Python wrapper for C-based UDP protocol.
Operates in PASSIVE mode - C binaries run autonomously.
"""

import subprocess
import os
import signal
import platform
import logging
import time
from pathlib import Path
from typing import List
from concurrent.futures import ThreadPoolExecutor

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from stgen.protocol_interface import ProtocolInterface

_LOG = logging.getLogger("my_udp")


class Protocol(ProtocolInterface):
    """
    Wrapper for C UDP server/client binaries.
    Assumes compiled binaries in ../../bin/
    """
    
    def __init__(self, cfg):
        super().__init__(cfg)
        self.procs: List[subprocess.Popen] = []
        self.mode = "passive"  # Force passive mode
    
    def start_server(self) -> None:
        """Launch C server binary."""
        exe = Path(__file__).parent / "../../bin/my_udp_server"
        
        if not exe.exists():
            raise FileNotFoundError(
                f"Server binary not found: {exe}\n"
                "Run: make -C protocols/my_udp"
            )
        
        cmd = [
            str(exe),
            self.cfg["server_ip"],
            str(self.cfg["server_port"])
        ]
        
        self._spawn(cmd, "server")
        _LOG.info(f"Server started on {self.cfg['server_ip']}:{self.cfg['server_port']}")
    
    def start_clients(self, num: int) -> None:
        """Launch N C client binaries."""
        exe = Path(__file__).parent / "../../bin/my_udp_client"
        
        if not exe.exists():
            raise FileNotFoundError(
                f"Client binary not found: {exe}\n"
                "Run: make -C protocols/my_udp"
            )
        
        def spawn_client(i):
            cmd = [
                str(exe),
                self.cfg["server_ip"],
                str(self.cfg["server_port"]),
                str(i)  # Client ID
            ]
            self._spawn(cmd, f"client-{i}")

        with ThreadPoolExecutor(max_workers=min(num, 100)) as executor:
            executor.map(spawn_client, range(num))
        
        _LOG.info(f"Started {num} clients")
    
    def stop(self) -> None:
        """Terminate all spawned processes."""
        self._alive = False
        
        _LOG.info("Stopping processes...")
        
        for p in self.procs:
            if p.poll() is None:  # Still running
                self._kill(p)
        
        # Wait for cleanup
        time.sleep(0.5)
        
        _LOG.info("All processes stopped")
    
    # ---------- Helper methods ----------
    
    def _spawn(self, cmd: List[str], name: str) -> None:
        """Spawn a subprocess in platform-safe way."""
        try:
            if platform.system() == "Windows":
                p = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                p = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setsid
                )
            
            self.procs.append(p)
            _LOG.info(f"Started {name} (PID {p.pid})")
            time.sleep(0.2)  # Brief settle time
            
        except Exception as e:
            _LOG.error(f"Failed to spawn {name}: {e}")
            raise
    
    def _kill(self, proc: subprocess.Popen) -> None:
        """Kill process in platform-safe way."""
        try:
            if platform.system() == "Windows":
                proc.terminate()
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                time.sleep(0.5)
                if proc.poll() is None:
                    proc.kill()
        except Exception as e:
            _LOG.warning(f"Failed to kill PID {proc.pid}: {e}")