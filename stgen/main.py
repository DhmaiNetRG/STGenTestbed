# # stgen/main.py
# """
# STGen CLI Entry Point
# Usage: python -m stgen.main <config.json>
# """

# import json
# import logging
# import sys
# import time
# from pathlib import Path

# from .orchestrator import Orchestrator
# from .sensor_generator import generate_sensor_stream



# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
#     datefmt="%H:%M:%S"
# )

# _LOG = logging.getLogger("stgen.main")


# def main():
#     """Main entry point."""
#     if len(sys.argv) != 2:
#         print("Usage: python -m stgen.main <config.json>")
#         print("\nExample config:")
#         print(json.dumps({
#             "protocol": "coap",
#             "mode": "active",
#             "server_ip": "127.0.0.1",
#             "server_port": 5683,
#             "num_clients": 4,
#             "duration": 30,
#             "sensors": ["temp", "humidity", "motion"]
#         }, indent=2))
#         sys.exit(1)
    
#     config_file = sys.argv[1]
    
#     # Load configuration
#     try:
#         cfg = json.loads(Path(config_file).read_text())
#         _LOG.info(f"Loaded config from {config_file}")
#     except Exception as e:
#         _LOG.error(f"Failed to load config: {e}")
#         sys.exit(1)
    
#     # Validate required fields
#     required = ["protocol", "server_ip", "server_port", "num_clients", "duration"]
#     missing = [k for k in required if k not in cfg]
#     if missing:
#         _LOG.error(f"Missing required config fields: {missing}")
#         sys.exit(1)
    
#     # Create orchestrator
#     try:
#         orch = Orchestrator(cfg["protocol"], cfg)
#     except Exception as e:
#         _LOG.error(f"Orchestrator creation failed: {e}")
#         sys.exit(1)
    
#     # Generate sensor stream
#     stream = generate_sensor_stream(cfg)
    
#     # Run test
#     try:
#         ok = orch.run_test(stream)
#     except KeyboardInterrupt:
#         _LOG.warning("Test interrupted by user")
#         ok = False
#     except Exception as e:
#         _LOG.exception("Test failed")
#         ok = False
#     finally:
#         orch.protocol.stop()
    
#     # Save results
#     if ok or orch.metrics["sent"] > 0:  # Save partial results on interrupt
#         timestamp = int(time.time())
#         out_dir = Path("results") / f"{cfg['protocol']}_{timestamp}"
#         orch.save_report(out_dir)
#         _LOG.info("Test completed successfully")
#     else:
#         _LOG.error("Test failed - no results saved")
#         sys.exit(1)


# if __name__ == "__main__":
#     main()


# stgen/main.py
"""
STGen CLI Entry Point - Enhanced Version
Usage: 
  python -m stgen.main <config.json>
  python -m stgen.main --scenario smart_home --protocol YOUR_PROTOCOL
  python -m stgen.main --compare coap,srtp --scenario industrial_iot
"""

import json
import logging
import sys
import time
import argparse
from pathlib import Path

from .orchestrator import Orchestrator
from .sensor_generator import generate_sensor_stream
from .utils import load_config, load_scenario, list_available_scenarios, list_available_protocols
from .failure_injector import FailureInjector
from .validator import validate_protocol_results
from .network_emulator import NetworkEmulator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S"
)

_LOG = logging.getLogger("stgen.main")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="STGen - IoT Protocol Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with config file
  python -m stgen.main configs/coap.json
  
  # Run with scenario
  python -m stgen.main --scenario smart_home --protocol coap
  
  # Compare protocols
  python -m stgen.main --compare coap,srtp --scenario industrial_iot
  
  # List available scenarios
  python -m stgen.main --list-scenarios
  
  # List available protocols
  python -m stgen.main --list-protocols
        """
    )
    
    parser.add_argument("config", nargs="?", help="Path to configuration file")
    parser.add_argument("--scenario", help="Use predefined scenario (e.g., smart_home)")
    parser.add_argument("--protocol", help="Protocol to test")
    parser.add_argument("--compare", help="Comma-separated list of protocols to compare")
    parser.add_argument("--list-scenarios", action="store_true", help="List available scenarios")
    parser.add_argument("--list-protocols", action="store_true", help="List available protocols")
    parser.add_argument("--validate", action="store_true", help="Run validation checks on results")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    return parser.parse_args()


def list_scenarios():
    """Print available scenarios."""
    scenarios = list_available_scenarios()
    if not scenarios:
        print("No scenarios found in configs/scenarios/")
        return
    
    print("\n📋 Available Scenarios:")
    print("=" * 60)
    for scenario in sorted(scenarios):
        try:
            cfg = load_scenario(scenario)
            name = cfg.get("name", scenario)
            desc = cfg.get("description", "No description")
            print(f"\n  {scenario}")
            print(f"    Name: {name}")
            print(f"    Description: {desc}")
        except Exception as e:
            print(f"  {scenario} (error loading: {e})")
    print()


def list_protocols():
    """Print available protocols."""
    protocols = list_available_protocols()
    if not protocols:
        print("No protocols found in protocols/")
        return
    
    print("\n🔌 Available Protocols:")
    print("=" * 60)
    for protocol in sorted(protocols):
        print(f"  • {protocol}")
    print()


# def run_single_test(cfg: dict) -> bool:
#     """Run a single protocol test."""
#     # Validate config
#     from .utils import validate_config
#     validate_config(cfg)
    
#     _LOG.info(f"Loaded config from {cfg.get('_source', 'dict')}")
    
#     # Create orchestrator
#     try:
#         orch = Orchestrator(cfg["protocol"], cfg)
#     except Exception as e:
#         _LOG.error(f"Orchestrator creation failed: {e}")
#         return False
    
#     # Setup failure injection if configured
#     if "failure_injection" in cfg:
#         _LOG.info("Failure injection enabled")
#         injector = FailureInjector(cfg)
#         # Wrap send_data with failure injection
#         from .failure_injector import wrap_send_with_failures
#         orch.protocol.send_data = wrap_send_with_failures(
#             orch.protocol.send_data, 
#             injector
#         )
    
#     # Generate sensor stream
#     stream = generate_sensor_stream(cfg)
    
#     # Run test
#     try:
#         ok = orch.run_test(stream)
#     except KeyboardInterrupt:
#         _LOG.warning("Test interrupted by user")
#         ok = False
#     except Exception as e:
#         _LOG.exception("Test failed")
#         ok = False
#     finally:
#         orch.protocol.stop()
    
#     # Save results
#     if ok or orch.metrics["sent"] > 0:
#         timestamp = int(time.time())
#         out_dir = Path("results") / f"{cfg['protocol']}_{timestamp}"
#         orch.save_report(out_dir)
        
#         # Run validation if requested
#         if cfg.get("validate", False):
#             qos = cfg.get("qos_requirements", {})
#             validation_report = validate_protocol_results(orch.metrics, qos)
#             print("\n" + validation_report)
#             (out_dir / "validation.txt").write_text(validation_report)
        
#         _LOG.info("Test completed successfully")
#         return True
#     else:
#         _LOG.error("Test failed - no results saved")
#         return False

# def run_single_test(cfg: dict) -> bool:
#     """Run a single protocol test."""
#     from .utils import validate_config
#     validate_config(cfg)
    
#     _LOG.info(f"Loaded config from {cfg.get('_source', 'dict')}")
    
#     emulator = None
#     orch = None
#     ok = False
    
#     try:
#         # --- 1. START NETWORK EMULATOR ---
#         if "network_profile" in cfg:
#             _LOG.info(f"Applying network profile: {cfg['network_profile']}")
            
#             # Assumes profiles are in configs/networks/
#             profile_path = f"configs/networks/{cfg['network_profile']}.json"
            
#             # Use 'lo' for local testing
#             emulator = NetworkEmulator.from_profile(profile_path, interface="lo")
        
#         # --- 2. CREATE ORCHESTRATOR ---
#         orch = Orchestrator(cfg["protocol"], cfg)

#         # ... (Your existing FailureInjector code can go here) ...
        
#         # --- 3. GENERATE STREAM ---
#         stream = generate_sensor_stream(cfg)
        
#         # --- 4. RUN TEST ---
#         ok = orch.run_test(stream)

#     except KeyboardInterrupt:
#         _LOG.warning("Test interrupted by user")
#         ok = False
#     except Exception as e:
#         _LOG.exception("Test failed")
#         ok = False
#     finally:
#         # --- 5. CLEANUP ---
#         _LOG.info("Cleaning up test...")
#         if orch:
#             orch.protocol.stop()
#         if emulator:
#             emulator.clear()
#             _LOG.info("Network emulation cleared.")
    
#     # --- 6. SAVE REPORT ---
#     if ok or (orch and orch.metrics["sent"] > 0):
#         timestamp = int(time.time())
#         # Use a scenario-based name if available
#         scenario_name = cfg.get('_source', 'unknown').split(':')[-1]
#         out_dir = Path("results") / f"{cfg['protocol']}_{scenario_name}_{timestamp}"
        
#         orch.save_report(out_dir)
#         _LOG.info("Test completed successfully")
#         return True
#     else:
#         _LOG.error("Test failed - no results saved")
#         return False
def run_single_test(cfg: dict) -> bool:
    """Run a single protocol test."""
    # Validate config
    from .utils import validate_config
    validate_config(cfg)
    
    _LOG.info(f"Loaded config from {cfg.get('_source', 'dict')}")
    
    # --- Define variables ---
    emulator = None
    orch = None
    ok = False
    
    try:
        # --- 1. START NETWORK EMULATOR ---
        if "network_profile" in cfg:
            profile_name = cfg['network_profile']
            _LOG.info(f"Applying network profile: {profile_name}")
            
            # --- FIX 1: Correct path ---
            # (Your configs are in 'networks/', not 'networks_conditions/')
            profile_path = f"configs/network_conditions/{profile_name}.json"
            
            # Import here to avoid circular dependency
            from .network_emulator import NetworkEmulator 
            
            # Use 'lo' for local testing (requires sudo)
            emulator = NetworkEmulator.from_profile(profile_path, interface="lo")
        
        # --- 2. CREATE ORCHESTRATOR ---
        orch = Orchestrator(cfg["protocol"], cfg)

        # --- (FailureInjector code could go here if you want to use it) ---
        
        # --- 3. GENERATE STREAM ---
        stream = generate_sensor_stream(cfg)
        
        # --- 4. RUN TEST ---
        ok = orch.run_test(stream)

    except KeyboardInterrupt:
        _LOG.warning("Test interrupted by user")
        ok = False
    except Exception as e:
        _LOG.exception("Test failed")
        ok = False
    finally:
        # --- 5. CLEANUP (CRITICAL) ---
        _LOG.info("Cleaning up test...")
        if orch:
            orch.protocol.stop()
        if emulator:
            emulator.clear()
            _LOG.info("Network emulation cleared.")
    
    # --- 6. SAVE REPORT ---
    if ok or (orch and orch.metrics["sent"] > 0):
        timestamp = int(time.time())
        
        # Use a scenario-based name if available
        scenario_name = "default"
        if "_source" in cfg:
            scenario_name = cfg.get('_source', 'unknown').split(':')[-1]
            # remove .json
            scenario_name = scenario_name.replace('.json', '')
            
        out_dir = Path("results") / f"{cfg['protocol']}_{scenario_name}_{timestamp}"
        
        orch.save_report(out_dir)
        _LOG.info("Test completed successfully")
        return True
    else:
        _LOG.error("Test failed - no results saved")
        return False
def run_comparison(protocols: list, scenario_cfg: dict):
    """Run comparison of multiple protocols."""
    from .comparator import ProtocolComparator
    
    _LOG.info(f"Comparing protocols: {', '.join(protocols)}")
    
    # Save scenario as temp file
    temp_scenario = Path("temp_scenario.json")
    temp_scenario.write_text(json.dumps(scenario_cfg, indent=2))
    
    try:
        comparator = ProtocolComparator(str(temp_scenario), protocols)
        comparator.run_comparison()
        
        # Generate report
        timestamp = int(time.time())
        report_file = f"results/comparisons/comparison_{timestamp}.txt"
        Path(report_file).parent.mkdir(parents=True, exist_ok=True)
        comparator.generate_report(report_file)
        
        _LOG.info(f"Comparison complete - report saved to {report_file}")
    finally:
        temp_scenario.unlink(missing_ok=True)


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Handle list commands
    if args.list_scenarios:
        list_scenarios()
        return
    
    if args.list_protocols:
        list_protocols()
        return
    
    # Load configuration
    if args.config:
        # Load from file
        try:
            cfg = load_config(args.config)
            cfg["_source"] = args.config
        except Exception as e:
            _LOG.error(f"Failed to load config: {e}")
            sys.exit(1)
    elif args.scenario:
        # Load from scenario
        try:
            cfg = load_scenario(args.scenario)
            cfg["_source"] = f"scenario:{args.scenario}"
            
            # Override protocol if specified
            if args.protocol:
                cfg["protocol"] = args.protocol
        except Exception as e:
            _LOG.error(f"Failed to load scenario: {e}")
            sys.exit(1)
    else:
        _LOG.error("No configuration specified. Use --config or --scenario")
        sys.exit(1)
    
    # Add validation flag
    if args.validate:
        cfg["validate"] = True
    
    # Run comparison or single test
    if args.compare:
        protocols = [p.strip() for p in args.compare.split(",")]
        run_comparison(protocols, cfg)
    else:
        success = run_single_test(cfg)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()