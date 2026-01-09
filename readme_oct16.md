# STGen - IoT Protocol Testing Framework

A lightweight testbed for validating custom IoT communication protocols under realistic workloads.

## Features

-  **Protocol-Agnostic**: Easy integration for any IoT protocol
-  **Realistic Workloads**: 7 predefined scenarios (smart home, industrial, agriculture, etc.)
-  **Failure Injection**: Test resilience under packet loss, crashes, network partitions
- **Automated Comparison**: Side-by-side protocol performance analysis
-  **Validation Checks**: Automated QoS compliance verification
- **Binary Support**: Works with both Python and C/C++ implementations

## Quick Start
```bash
python3 -m venv myenv
source myenv/bin/activate

# Install
pip install -r requirements.txt

# Run a test
python -m stgen.main --scenario smart_agriculture --protocol coap

# Compare protocols
python -m stgen.main --compare coap,srtp --scenario smart_agriculture

# List available scenarios
python -m stgen.main --list-scenarios
```

## Documentation

See `docs/` for detailed guides.

## Citation




STGen_Future_Present/
├── bin/                          # Executable scripts
│   └── stgen-compare             # Comparison CLI tool
│
├── configs/                      # Configuration files
│   ├── scenarios/                
│   │   ├── smart_home.json
│   │   ├── industrial_iot.json
│   │   ├── smart_agriculture.json
│   │   ├── healthcare_wearables.json
│   │   ├── burst_event_driven.json
│   │   ├── stress_test.json
│   │   └── intermittent_connectivity.json
│   │
│   ├── network_conditions/      
│   │   ├── perfect.json          # No impairments
│   │   ├── wifi.json             # Typical WiFi
│   │   ├── 4g.json               # Mobile network
│   │   ├── lorawan.json          # LPWAN conditions
│   │   └── congested.json        # High loss/latency
│   │
│   ├── coap.json                 # Protocol-specific configs
│   ├── srtp.json
│   ├── my_udp.json
│   └── template.json
│
├── protocols/                    # Protocol implementations
│   ├── __pycache__/
│   ├── coap/
│   │   ├── __init__.py
│   │   ├── coap.py
│   │   ├── README.md
│   │   └── requirements.txt
│   ├── SRTP/
│   │   ├── __init__.py
│   │   ├── srtp.py
│   │   ├── STGen_Server         # Binary
│   │   ├── STGen_Client         # Binary
│   │   └── README.md
│   ├── my_udp/
│   └── template/
│       ├── __init__.py
│       ├── template.py
│       └── README.md
│
├── stgen/                        # Core framework
│   ├── __pycache__/
│   ├── __init__.py
│   ├── main.py
│   ├── orchestrator.py
│   ├── protocol_interface.py
│   ├── sensor_generator.py
│   │
│   ├── failure_injector.py      
│   ├── validator.py              
│   ├── comparator.py             
│   ├── network_emulator.py       
│   ├── metrics_collector.py      
│   ├── report_generator.py       
│   └── utils.py                  
│
├── results/                     
│   ├── coap_1760470635/
│   ├── SRTP_1760472029/
│   └── comparisons/              
│       ├── coap_vs_srtp_smart_home/
│       └── stress_test_all_protocols/
│
├── tests/                        # Unit tests
│   ├── test_orchestrator.py
│   ├── test_sensor_generator.py
│   ├── test_failure_injector.py  
│   └── test_comparator.py        
│
├── tools/                       
│   ├── venv/
│   ├── install_dependencies.sh
│   ├── run_all_scenarios.sh      
│   ├── generate_graphs.py       
│   └── export_results.py         
│
├── docs/                         
│   ├── getting_started.md
│   ├── protocol_integration.md
│   ├── scenarios_guide.md
│   ├── failure_injection.md
│   ├── api_reference.md
│   └── case_studies/
│       ├── srtp_validation.md
│       └── coap_vs_srtp.md
│
├── paper/                       
│   ├── figures/
│   │   ├── architecture.pdf
│   │   ├── latency_comparison.pdf
│   │   └── scaling_results.pdf
│   ├── tables/
│   │   └── comparison_table.tex
│   ├── draft.tex
│   └── bibliography.bib
│
├── examples/                     
│   ├── simple_udp/
│   ├── reliable_udp/
│   └── custom_coap/
│
├── .gitignore
├── README.md
├── LICENSE
├── requirements.txt
├── setup.py                    
└── CONTRIBUTING.md              