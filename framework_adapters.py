#!/usr/bin/env python3
"""
Framework Adapters for Gotham and other IoT testing frameworks

These adapters provide standard interfaces to run Gotham and other frameworks
within the comparison pipeline.

Gotham Reference: https://github.com/xsaga/gotham-iot-testbed
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any
import logging
import os

_LOG = logging.getLogger(__name__)


class GothamAdapter:
    """
    Adapter for Gotham IoT Testbed (GNS3-based).
    
    Reference: https://github.com/xsaga/gotham-iot-testbed
    Gotham is a reproducible IoT testbed for security experiments using GNS3.
    """
    
    def __init__(self, repo_path: str = None, timeout: int = 300):
        """
        Initialize Gotham adapter.
        
        Args:
            repo_path: Path to Gotham repository root
            timeout: Timeout in seconds
        """
        self.repo_path = Path(repo_path) if repo_path else self._find_repo()
        self.timeout = timeout
        self.src_dir = self.repo_path / "src" if self.repo_path else None
        self.venv_activate = self.repo_path / "venv" / "bin" / "activate" if self.repo_path else None
    
    def _find_repo(self) -> Path:
        """Find Gotham repository in common locations."""
        candidates = [
            Path.home() / "gotham-iot-testbed",
            Path("/opt/gotham-iot-testbed"),
            Path("../gotham-iot-testbed"),
            Path("./gotham-iot-testbed"),
            Path("/home/mehraj-rahman/gotham-iot-testbed"),
        ]
        
        for path in candidates:
            if (path / "src" / "run_scenario_gotham.py").exists():
                _LOG.info(f"Found Gotham at: {path}")
                return path
        
        _LOG.warning("Gotham repository not found in standard locations")
        return None
    
    def run_scenario(self, scenario_name: str, config_file: str = None) -> Dict[str, Any]:
        """
        Run a test scenario on Gotham.
        
        Gotham uses GNS3 to simulate IoT topologies. This runs the scenario generator
        which creates and executes the network topology, captures traffic, and generates results.
        
        Args:
            scenario_name: Name of the scenario (GNS3 project)
            config_file: Optional custom config file path
            
        Returns:
            Dictionary of results
        """
        if not self.repo_path:
            return {
                "error": "Gotham repository not found",
                "message": "Install from: https://github.com/xsaga/gotham-iot-testbed",
                "status": "not_installed"
            }
        
        if not self.src_dir.exists():
            return {"error": f"Gotham src directory not found: {self.src_dir}"}
        
        # Build command - Gotham requires running Python script that interacts with GNS3
        cmd = ["python3", "run_scenario_gotham.py"]
        
        _LOG.info(f"Running Gotham scenario: {scenario_name}")
        _LOG.info(f"Command: {' '.join(cmd)} (in {self.src_dir})")
        _LOG.info("Note: Gotham requires GNS3 server to be running")
        
        try:
            # Run from src directory where the script is located
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["SCENARIO_NAME"] = scenario_name
            
            result = subprocess.run(
                cmd,
                cwd=str(self.src_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env
            )
            
            if result.returncode != 0:
                _LOG.error(f"Gotham stderr: {result.stderr}")
                return {
                    "error": f"Gotham exited with code {result.returncode}",
                    "stderr": result.stderr[:500],  # Limit size
                    "stdout": result.stdout[:500],
                    "framework": "gotham"
                }
            
            # Gotham generates GNS3 projects and pcap traffic captures
            results = {
                "status": "completed",
                "scenario": scenario_name,
                "framework": "gotham",
                "method": "GNS3-based IoT simulation",
                "output_summary": result.stdout[:500]  # First 500 chars
            }
            
            # Look for generated results/pcap files
            results_dir = self.repo_path / "results"
            if results_dir.exists():
                pcap_files = list(results_dir.glob("*.pcap"))
                if pcap_files:
                    results["pcap_files"] = len(pcap_files)
                    results["pcap_paths"] = [str(f) for f in pcap_files[:5]]  # First 5
            
            # Try to parse any JSON output from Gotham
            try:
                json_output = json.loads(result.stdout)
                results["parsed_output"] = json_output
            except json.JSONDecodeError:
                pass  # Not JSON output
            
            return results
                
        except subprocess.TimeoutExpired:
            return {
                "error": f"Gotham timed out after {self.timeout}s",
                "framework": "gotham",
                "suggestion": "Increase timeout or check if GNS3 server is responsive"
            }
        except FileNotFoundError as e:
            return {
                "error": f"Failed to run Gotham: Python or script not found",
                "details": str(e),
                "framework": "gotham"
            }
        except Exception as e:
            return {
                "error": f"Gotham execution failed: {type(e).__name__}",
                "details": str(e),
                "framework": "gotham"
            }
    
    def validate_installation(self) -> bool:
        """Check if Gotham is properly set up."""
        if not self.repo_path:
            return False
        
        # Check essential files exist
        required_files = [
            self.repo_path / "src" / "run_scenario_gotham.py",
            self.repo_path / "src" / "create_topology_gotham.py",
            self.repo_path / "requirements.txt"
        ]
        
        all_exist = all(f.exists() for f in required_files)
        
        if all_exist:
            _LOG.info(f"✓ Gotham installation verified at {self.repo_path}")
        else:
            missing = [f for f in required_files if not f.exists()]
            _LOG.warning(f"✗ Missing Gotham files: {missing}")
        
        return all_exist
    
    def get_info(self) -> Dict[str, Any]:
        """Get information about this Gotham installation."""
        return {
            "name": "Gotham IoT Testbed",
            "type": "GNS3-based emulation platform",
            "repo_url": "https://github.com/xsaga/gotham-iot-testbed",
            "repo_path": str(self.repo_path) if self.repo_path else "Not found",
            "installed": self.validate_installation(),
            "requires_gns3": True,
            "description": "Reproducible IoT testbed for security experiments and dataset generation"
        }


def validate_frameworks() -> Dict[str, bool]:
    """
    Check which frameworks are available on the system.
    
    Returns:
        Dict mapping framework names to availability status
    """
    status = {
        "stgen": _check_stgen(),
        "gotham": GothamAdapter().validate_installation(),
    }
    
    return status


def _check_stgen() -> bool:
    """Check if STGen is available."""
    try:
        result = subprocess.run(
            ["python", "-m", "stgen.main", "--help"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


def print_framework_status():
    """Print status of all available frameworks."""
    print("\n" + "=" * 60)
    print("IoT Framework Installation Status")
    print("=" * 60)
    
    status = validate_frameworks()
    
    for framework, available in status.items():
        symbol = "✓" if available else "✗"
        print(f"{symbol} {framework.upper():<20} {'Available' if available else 'Not Installed'}")
    
    print("\n" + "-" * 60)
    print("Framework Information:")
    print("-" * 60)
    
    gotham = GothamAdapter()
    gotham_info = gotham.get_info()
    print(f"\nGotham IoT Testbed:")
    print(f"  Repository: {gotham_info['repo_url']}")
    print(f"  Local Path: {gotham_info['repo_path']}")
    print(f"  Installed: {gotham_info['installed']}")
    print(f"  Requires: GNS3 server running")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print_framework_status()
    
    print("\n" + "-" * 60)
    print("To install Gotham:")
    print("-" * 60)
    print("""
1. Clone the repository:
   git clone https://github.com/xsaga/gotham-iot-testbed.git
   
2. Install dependencies:
   cd gotham-iot-testbed
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
3. Build Docker images:
   make
   
4. Set up GNS3 templates:
   python3 src/create_templates.py
   
5. Create topology:
   python3 src/create_topology_gotham.py
   
6. Run scenario (requires GNS3 running):
   python3 src/run_scenario_gotham.py
    """)
