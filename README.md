# STGen: IoT Protocol Testing and Evaluation Framework

**License**: MIT | **Version**: 2.0

---

## Overview

STGen is a comprehensive, **research-grade** framework for testing, validating, and comparing IoT communication protocols under realistic network conditions. Designed for academic and industrial use.

### Key Capabilities

- **Protocol-Agnostic Architecture**: Support for MQTT, CoAP, SRTP, and custom protocols
- **Realistic Workloads**: 7 predefined IoT scenarios (smart home, agriculture, healthcare, etc.)
- **Network Emulation**: Simulate latency, jitter, packet loss, and bandwidth constraints
- **Fault Injection**: Test resilience under failures (crashes, partitions, corruption)
- **Automated Validation**: SLA compliance checks and protocol benchmarking
- **Scalability**: Support for 6000+ concurrent IoT devices
- **Real-time Monitoring**: Web-based dashboard with live metrics
- **Publication-Ready Reports**: Automated comparison analysis and metrics export

---

##  Getting Started (Zero to Running)

Follow these steps to set up the STGen environment from scratch.

###  Install Prerequisites

Before you begin, ensure you have the following installed:
*   **Linux (Ubuntu/Debian recommended)** or **macOS**. (Windows is not supported)
*   **Python 3.8+**: [Download Python](https://www.python.org/downloads/)
*   **Node.js 16+**: [Download Node.js](https://nodejs.org/) (Required for the Dashboard)
*   **Mosquitto MQTT Broker**: Essential for protocol messaging.

#### Installing Mosquitto (Required)
*   **Ubuntu/Debian**:
    ```bash
    sudo apt update
    sudo apt install mosquitto mosquitto-clients
    # Ensure it's running
    sudo systemctl enable mosquitto
    sudo systemctl start mosquitto
    ```
*   **macOS**:
    ```bash
    brew install mosquitto
    brew services start mosquitto
    ```

---

###  Setup Python Environment

Open your terminal and navigate to the project folder.

#### 1. Create Virtual Environment
Isolates dependencies from your system.

```bash
python3 -m venv myenv
source myenv/bin/activate
```

#### 2. Install Dependencies
Installs STGen core, dashboard backend, and protocol libs.
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

###  Run the System

We provide a single startup script to launch the Backend and Frontend.

```bash
chmod +x start_all.sh  # Make executable (first time only)
./start_all.sh
```

---

###  Access the Dashboard

Open your web browser and go to:
👉 **[http://localhost:3000](http://localhost:3000)**

You can now create experiments, simulate failures, and visualize real-time metrics.

---

## Project Structure

```
STGen_Future_Present/
├── stgen/                      # Core Framework
│   ├── orchestrator.py         # Test lifecycle management
│   ├── sensor_generator.py     # Realistic IoT workloads
│   ├── network_emulator.py     # Network condition simulation
│   ├── metrics_collector.py    # Performance metrics
│   ├── failure_injector.py     # Fault injection
│   ├── validator.py            # Protocol validation
│   └── main.py                 # CLI interface
│
├── protocols/                  # Protocol Implementations
│   ├── mqtt/                   # MQTT (pub/sub)
│   ├── coap/                   # CoAP (REST-like)
│   ├── srtp/                   # SRTP (real-time)
│   └── custom_udp/             # Custom UDP
│
├── stgen-ui/                   # Web Dashboard
│   ├── backend/                # FastAPI server
│   └── frontend/               # React application
│
├── configs/                    # Configuration Files
│   ├── network_conditions/     # Network profiles
│   └── scenarios/              # Test scenarios
│
├── results/                    # Experiment Results
│   └── ui_experiments/         # Web UI results
│
└── docs/                       # Documentation
    ├── getting_started.md
    ├── protocol_integration.md
    ├── NETWORK_TAX_EXPERIMENT.md  # Section 7.3 guide
    └── api_reference.md
```

---

## Command-Line Usage

### Run Tests via CLI

```bash
source myenv/bin/activate

# Basic test
python -m stgen.main --scenario smart_agriculture --protocol mqtt --duration 30

# Compare protocols
python -m stgen.main --compare mqtt,coap --scenario smart_agriculture

# With failure injection
python3 -m stgen.main --protocol mqtt --inject-failures 0.1 --duration 60 --num-clients 100 --scenario connected_vehicle

# Network tax experiment (Section 7.3) - Single device
python run_network_tax_single_device.py --protocol mqtt --duration 60
python analyze_network_tax.py --all --results-dir results/network_tax_single_device --format latex

# List available options
python -m stgen.main --help
```

### Available Scenarios
- **smart_home**: Residential IoT (light, temperature, security)
- **smart_agriculture**: Farm automation (soil sensors, irrigation)
- **industrial_iot**: Factory equipment monitoring
- **healthcare_wearables**: Medical device streams
- **smart_city**: Urban infrastructure
- **burst_event_driven**: Event-based traffic
- **intermittent_connectivity**: Offline-capable devices

### Network Profiles
- **perfect**: No impairments (baseline)
- **wifi**: 20ms latency, 2% loss
- **4g**: 50ms latency, 1% loss
- **lorawan**: 2000ms latency, 5% loss
- **congested**: 100ms latency, 10% loss
- **intermittent**: Frequent disconnections

---

## Web Dashboard

Access: **http://localhost:3000**

### Features
- Create and manage experiments
- Real-time metric visualization
- Live log streaming
- Automated result analysis
- Export data for publication

### API Documentation
Interactive API docs available at: **http://localhost:8000/docs**

---

## Metrics & Performance

### Collected Metrics
- **Latency**: min, max, mean, p50, p75, p90, p95, p99
- **Throughput**: packets/sec, bytes/sec
- **Reliability**: packet loss %, delivery ratio
- **Resource Usage**: CPU, memory, energy consumption
- **Connection Stats**: establish time, disconnect rate

### Performance Specifications
- **Device Scalability**: Simulates up to 6000+ concurrent devices
- **Metric Overhead**: < 1ms per measurement
- **Memory Efficiency**: Circular buffers with O(1) space complexity
- **Real-time Updates**: 2-second refresh interval

---

## Documentation

### Essential Guides
| Document | Purpose |
|----------|---------|
| [INDEX.md](INDEX.md) | Navigation and quick reference |
| [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) | Full setup and usage |
| [docs/](docs/) | Technical documentation |

### Code Standards
- Doxygen-documented classes and functions
- Type hints for Python functions
- Comprehensive error handling
- Academic comment style

---

## Deployment Options

### Local Development
```bash
./start_all.sh          # Unix-like systems
start_all.bat           # Windows
```

---

## Contributing

Contributions are welcome! To extend STGen:

1. **Add Protocol**: Implement `protocols/your_protocol/your_protocol.py`
2. **Add Scenario**: Create `configs/scenarios/your_scenario.json`
3. **Add Sensor**: Extend `stgen/sensor_generator.py`
4. **Improve Metrics**: Enhance `stgen/metrics_collector.py`

---

## Citation

If you use STGen in your research, please cite:

```bibtex
@software{stgen2024,
  title={STGen: IoT Protocol Testing and Evaluation Framework},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/stgen}
}
```

---

## Technical Stack

| Component | Technology |
|-----------|-----------|
| Core | Python 3.12 |
| Web UI | React 18, Material-UI 5 |
| Backend API | FastAPI, Uvicorn |
| Network Simulation | Linux tc/netem |
| Documentation | Doxygen, Markdown |
| Containerization | Docker |

---

## System Requirements
### Minimum
- **OS**: Linux, macOS, or Windows (via WSL2/Docker)
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 1.5 GB
- **Python**: 3.8+
- **Node.js**: 16+

### Recommended
- **CPU**: 4+ cores
- **RAM**: 8 GB
- **Disk**: SSD with 5 GB space

---

## Troubleshooting

### Port Conflicts
```bash
lsof -i :3000
lsof -i :8000
kill -9 <PID>
```

### Missing Dependencies
```bash
pip install -r requirements.txt
cd stgen-ui/frontend && npm install
```

See [docs/](docs/) for more troubleshooting.

---

## License

MIT License - See [LICENSE](LICENSE) for details

---

## Support

- **Documentation**: See [INDEX.md](INDEX.md)
- **API Reference**: http://localhost:8000/docs (after running)
- **Academic**: See [docs/](docs/) for research guides

---

**STGen - Research-Grade IoT Protocol Testing**

*Version 2.0 | January 10, 2026 | Production Ready*

### 4. View Results
```bash
ls results/
python tools/plot_results.py results/coap_1234567890/
```

##  Usage

### Running Tests
```bash
python -m stgen.main <config.json>
```

### Creating Your Own Protocol

1. Copy the template:
```bash
cp -r protocols/template protocols/my_protocol
```

2. Implement the protocol interface in `my_protocol/template.py`

3. Create a config file:
```bash
cp configs/template.json configs/my_protocol.json
```

4. Run:
```bash
python -m stgen.main configs/my_protocol.json
```

See [protocols/template/README.md](protocols/template/README.md) for details.

##  Distributed simulation
### Core Node
```
python distributed/run_distributed_experiment.py \
  --mode core \
  --protocol mqtt \
  --bind-ip 0.0.0.0 \
  --duration 30
```
### Sensor Node
```
python distributed/sensor_node.py \
  --core-ip 192.168.1.108 \
  --core-port 5000 \
  --node-id W1 \
  --sensors 100 \
  --protocol mqtt \
  --duration 30
```

### Client Node
```
python3 distributed/query_client.py \
  --server-ip 192.168.1.108 \
  --server-port 5000 \
  --protocol mqtt \
  --query-filter '{}' \
  --query-interval 5 \
  --duration 60
```
