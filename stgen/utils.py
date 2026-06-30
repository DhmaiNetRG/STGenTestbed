"""
Utility functions for STGen framework.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

_LOG = logging.getLogger("stgen.utils")


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from JSON file.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Dict with configuration
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    try:
        cfg = json.loads(path.read_text())
        _LOG.debug(f"Loaded config from {config_path}")
        return cfg
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {config_path}: {e}")


def load_scenario(scenario_name: str) -> Dict[str, Any]:
    """
    Load predefined scenario configuration.
    
    Args:
        scenario_name: Name of scenario (e.g., "smart_home")
        
    Returns:
        Dict with scenario configuration
    """
    scenario_path = Path("configs/scenarios") / f"{scenario_name}.json"
    return load_config(str(scenario_path))


def list_available_scenarios() -> List[str]:
    """Get list of available scenario names."""
    scenarios_dir = Path("configs/scenarios")
    if not scenarios_dir.exists():
        return []
    
    return [f.stem for f in scenarios_dir.glob("*.json")]


def list_available_protocols() -> List[str]:
    """Get list of available protocol implementations."""
    protocols_dir = Path("protocols")
    if not protocols_dir.exists():
        return []
    
    protocols = []
    for item in protocols_dir.iterdir():
        if item.is_dir() and not item.name.startswith("_"):
            # Check if it has __init__.py
            if (item / "__init__.py").exists():
                protocols.append(item.name)
    
    return protocols


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two configuration dictionaries.
    
    Args:
        base: Base configuration
        override: Values to override
        
    Returns:
        Merged configuration
    """
    merged = base.copy()
    merged.update(override)
    return merged


def validate_config(cfg: Dict[str, Any]) -> bool:
    """
    Validate configuration has required fields.
    
    Args:
        cfg: Configuration to validate
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    required_fields = ["protocol", "server_ip", "server_port", "num_clients", "duration"]
    
    missing = [field for field in required_fields if field not in cfg]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    
    # Validate types
    # Allow `num_clients == 0` for server-only / core nodes (no local clients).
    if not isinstance(cfg["num_clients"], int) or cfg["num_clients"] < 0:
        raise ValueError("num_clients must be a non-negative integer")
    
    if not isinstance(cfg["duration"], (int, float)) or cfg["duration"] <= 0:
        raise ValueError("duration must be a positive number")
    
    return True


def format_latency(latency_ms: float) -> str:
    """Format latency value for display."""
    if latency_ms < 1:
        return f"{latency_ms*1000:.0f}µs"
    elif latency_ms < 1000:
        return f"{latency_ms:.2f}ms"
    else:
        return f"{latency_ms/1000:.2f}s"


def format_throughput(messages: int, duration_sec: float) -> str:
    """Format throughput for display."""
    rate = messages / duration_sec if duration_sec > 0 else 0
    if rate < 1:
        return f"{rate*60:.1f} msg/min"
    else:
        return f"{rate:.1f} msg/s"


def calculate_percentile(values: List[float], percentile: float) -> float:
    """
    Calculate percentile from list of values.
    
    Args:
        values: List of numeric values
        percentile: Percentile to calculate (0-100)
        
    Returns:
        Percentile value
    """
    if not values:
        return 0.0
    
    sorted_vals = sorted(values)
    index = int(len(sorted_vals) * (percentile / 100.0))
    index = min(index, len(sorted_vals) - 1)
    return sorted_vals[index]


def save_json(data: Dict[str, Any], filepath: str) -> None:
    """
    Save dictionary as JSON file.
    
    Args:
        data: Data to save
        filepath: Output file path
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    _LOG.debug(f"Saved JSON to {filepath}")


def load_json(filepath: str) -> Dict[str, Any]:
    """
    Load JSON file.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Loaded data
    """
    with open(filepath, 'r') as f:
        return json.load(f)


# stgen/utils.py
# """
# Utility functions for STGen
# """

# import json
# import logging
# from pathlib import Path
# from typing import Dict, Any, List

# _LOG = logging.getLogger("stgen.utils")


# def load_config(config_path: str) -> Dict[str, Any]:
#     """
#     Load configuration from JSON file.
    
#     Args:
#         config_path: Path to configuration file
        
#     Returns:
#         Configuration dictionary
        
#     Raises:
#         FileNotFoundError: If config file doesn't exist
#         json.JSONDecodeError: If config is invalid JSON
#     """
#     path = Path(config_path)
#     if not path.exists():
#         raise FileNotFoundError(f"Config file not found: {config_path}")
    
#     try:
#         cfg = json.loads(path.read_text())
#         _LOG.info(f"Loaded config from {config_path}")
#         return cfg
#     except json.JSONDecodeError as e:
#         raise json.JSONDecodeError(f"Invalid JSON in {config_path}: {e}", e.doc, e.pos)


# def load_scenario(scenario_name: str) -> Dict[str, Any]:
#     """
#     Load a predefined scenario configuration.
    
#     Args:
#         scenario_name: Name of scenario (without .json extension)
        
#     Returns:
#         Configuration dictionary
#     """
#     scenario_path = Path("configs/scenarios") / f"{scenario_name}.json"
    
#     if not scenario_path.exists():
#         raise FileNotFoundError(
#             f"Scenario '{scenario_name}' not found. "
#             f"Available scenarios: {', '.join(list_available_scenarios())}"
#         )
    
#     return load_config(str(scenario_path))


# def list_available_scenarios() -> List[str]:
#     """
#     List all available scenario configurations.
    
#     Returns:
#         List of scenario names (without .json extension)
#     """
#     scenarios_dir = Path("configs/scenarios")
    
#     if not scenarios_dir.exists():
#         return []
    
#     return [
#         f.stem for f in scenarios_dir.glob("*.json")
#     ]


# def list_available_protocols() -> List[str]:
#     """
#     List all available protocol implementations.
#     Supports both flat structure (protocols/mqtt.py) and 
#     nested structure (protocols/mqtt/mqtt.py).
    
#     Returns:
#         List of protocol names
#     """
#     # Try multiple possible locations for protocols directory
#     possible_paths = [
#         Path("protocols"),
#         Path(__file__).parent.parent / "protocols",
#         Path.cwd() / "protocols"
#     ]
    
#     protocols_dir = None
#     for path in possible_paths:
#         if path.exists() and path.is_dir():
#             protocols_dir = path
#             break
    
#     if not protocols_dir:
#         _LOG.warning("Protocols directory not found, skipping validation")
#         return []
    
#     protocols = []
    
#     # Check for flat structure: protocols/mqtt.py
#     for f in protocols_dir.glob("*.py"):
#         if f.stem != "__init__" and not f.stem.startswith("_"):
#             protocols.append(f.stem)
    
#     # Check for nested structure: protocols/mqtt/mqtt.py
#     for subdir in protocols_dir.iterdir():
#         if subdir.is_dir() and not subdir.name.startswith("_"):
#             protocol_file = subdir / f"{subdir.name}.py"
#             if protocol_file.exists():
#                 protocols.append(subdir.name)
    
#     return protocols


# def validate_config(cfg: Dict[str, Any]) -> None:
#     """
#     Validate configuration dictionary.
    
#     Args:
#         cfg: Configuration to validate
        
#     Raises:
#         ValueError: If configuration is invalid
#     """
#     required = ["protocol", "server_ip", "server_port", "duration"]
#     missing = [k for k in required if k not in cfg]
    
#     if missing:
#         raise ValueError(f"Missing required config fields: {missing}")
    
#     # Check protocol is valid
#     protocol = cfg["protocol"]
#     available = list_available_protocols()
    
#     # Only validate if we found protocols directory
#     if available and protocol not in available:
#         raise ValueError(
#             f"Unknown protocol '{protocol}'. "
#             f"Available: {', '.join(available)}"
#         )
#     elif not available:
#         # Protocols dir not found, skip validation but log warning
#         _LOG.warning(
#             f"Could not validate protocol '{protocol}' - protocols directory not found. "
#             f"Make sure '{protocol}.py' exists in the protocols/ directory."
#         )
    
#     # Validate num_clients
#     num_clients = cfg.get("num_clients", 0)
#     if not isinstance(num_clients, int) or num_clients < 0:
#         raise ValueError("num_clients must be a non-negative integer")
    
#     # Check role compatibility
#     role = cfg.get("role", "core")
#     if role == "core" and num_clients > 0:
#         _LOG.warning(
#             "Core node with num_clients > 0 detected. "
#             "This will create local clients that publish to itself. "
#             "Consider setting num_clients=0 for pure server mode."
#         )
    
#     if role == "sensor" and num_clients == 0:
#         raise ValueError(
#             "Sensor nodes must have num_clients > 0. "
#             "Sensor nodes are client-only and need publishers."
#         )
    
#     # Validate duration
#     duration = cfg.get("duration", 30)
#     if not isinstance(duration, (int, float)) or duration <= 0:
#         raise ValueError("duration must be a positive number")
    
#     # Validate ports
#     server_port = cfg.get("server_port")
#     if not isinstance(server_port, int) or not (1 <= server_port <= 65535):
#         raise ValueError("server_port must be between 1 and 65535")
    
#     _LOG.debug("Configuration validated successfully")


# def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Merge two configuration dictionaries.
#     Override values take precedence over base values.
    
#     Args:
#         base: Base configuration
#         override: Override configuration
        
#     Returns:
#         Merged configuration
#     """
#     merged = base.copy()
#     merged.update(override)
#     return merged


# def format_bytes(num_bytes: int) -> str:
#     """
#     Format bytes into human-readable string.
    
#     Args:
#         num_bytes: Number of bytes
        
#     Returns:
#         Formatted string (e.g., "1.5 KB")
#     """
#     for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
#         if num_bytes < 1024.0:
#             return f"{num_bytes:.1f} {unit}"
#         num_bytes /= 1024.0
#     return f"{num_bytes:.1f} PB"


# def format_duration(seconds: float) -> str:
#     """
#     Format duration into human-readable string.
    
#     Args:
#         seconds: Duration in seconds
        
#     Returns:
#         Formatted string (e.g., "1h 30m 45s")
#     """
#     if seconds < 60:
#         return f"{seconds:.1f}s"
    
#     minutes = int(seconds // 60)
#     seconds = seconds % 60
    
#     if minutes < 60:
#         return f"{minutes}m {seconds:.0f}s"
    
#     hours = minutes // 60
#     minutes = minutes % 60
    
#     return f"{hours}h {minutes}m"


# def calculate_percentile(data: List[float], percentile: float) -> float:
#     """
#     Calculate percentile of a dataset.
    
#     Args:
#         data: Sorted list of values
#         percentile: Percentile to calculate (0-100)
        
#     Returns:
#         Percentile value
#     """
#     if not data:
#         return 0.0
    
#     if percentile < 0 or percentile > 100:
#         raise ValueError("Percentile must be between 0 and 100")
    
#     sorted_data = sorted(data)
#     index = int(len(sorted_data) * (percentile / 100.0))
#     index = min(index, len(sorted_data) - 1)
    
#     return sorted_data[index]


# # Example configuration templates
# CONFIG_TEMPLATES = {
#     "basic": {
#         "protocol": "mqtt",
#         "mode": "active",
#         "server_ip": "127.0.0.1",
#         "server_port": 1883,
#         "num_clients": 4,
#         "duration": 30,
#         "sensors": ["temp", "humidity"]
#     },
#     "distributed_core": {
#         "protocol": "mqtt",
#         "mode": "active",
#         "server_ip": "0.0.0.0",
#         "server_port": 5000,
#         "num_clients": 0, 
#         "duration": 300,
#         "role": "core"
#     },
#     "distributed_sensor": {
#         "protocol": "mqtt",
#         "mode": "active",
#         "server_ip": "192.168.1.100",  
#         "server_port": 5000,
#         "num_clients": 10,
#         "duration": 300,
#         "role": "sensor",
#         "node_id": "sensor_A"
#     }
# }


# def get_template(template_name: str) -> Dict[str, Any]:
#     """
#     Get a configuration template.
    
#     Args:
#         template_name: Name of template
        
#     Returns:
#         Configuration dictionary
        
#     Raises:
#         KeyError: If template doesn't exist
#     """
#     if template_name not in CONFIG_TEMPLATES:
#         available = ', '.join(CONFIG_TEMPLATES.keys())
#         raise KeyError(
#             f"Template '{template_name}' not found. "
#             f"Available templates: {available}"
#         )
    
#     return CONFIG_TEMPLATES[template_name].copy()