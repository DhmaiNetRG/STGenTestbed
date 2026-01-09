##! @mainpage STGen - IoT Protocol Testing Framework
##! 
##! @section overview Overview
##! STGen is a comprehensive testing framework for evaluating IoT protocols under various
##! network conditions with realistic sensor data streams and failure injection.
##! 
##! @section features Key Features
##! - **Multi-Protocol Support**: MQTT, CoAP, SRTP, UDP, and custom protocols
##! - **Realistic Sensors**: Temperature, humidity, GPS, motion, light, camera, device metrics
##! - **Network Emulation**: Latency, jitter, packet loss, bandwidth throttling
##! - **Failure Injection**: Packet loss, client crashes, network partitions
##! - **Web Dashboard**: Real-time monitoring and experiment management
##! - **CLI Interface**: Batch testing and automation
##! - **Metrics Collection**: Percentile latencies, throughput, packet loss, energy consumption
##! 
##! @section architecture Architecture
##! 
##! @subsection core Core Components
##! - @ref stgen.orchestrator.Orchestrator - Test orchestration engine
##! - @ref stgen.sensor_generator - Sensor data stream generation
##! - @ref stgen.network_emulator.NetworkEmulator - Network condition simulation
##! - @ref stgen.metrics_collector.MetricsCollector - Real-time metrics collection
##! - @ref stgen.failure_injector.FailureInjector - Failure simulation
##! - @ref stgen.validator.ProtocolValidator - Protocol validation
##! 
##! @subsection ui Web UI Components
##! - Frontend: React 18 with Material-UI 5
##! - Backend: FastAPI with WebSocket support
##! - API: RESTful endpoints for experiment management
##! 
##! @section usage Quick Start
##! 
##! @subsection web_ui Web Dashboard
##! @code
##! ./start_all.sh          # Linux/macOS
##! @endcode
##! 
##! Then open http://localhost:3000
##! 
##! @subsection cli_mode CLI Mode
##! @code
##! source myenv/bin/activate
##! python stgen/main.py --scenario smart_home --protocol mqtt --duration 30
##! @endcode
##! 
##! @section configuration Configuration
##! 
##! Experiments are configured via JSON:
##! @code
##! {
##!   "protocol": "mqtt",
##!   "num_clients": 10,
##!   "duration": 30,
##!   "sensors": ["temperature", "humidity"],
##!   "network_profile": "wifi"
##! }
##! @endcode
##! 
##! @section network_profiles Network Profiles
##! - **perfect**: 0ms latency, 0% loss (baseline)
##! - **wifi**: 20ms latency, 2% loss
##! - **4g**: 50ms latency, 1% loss
##! - **lorawan**: 2000ms latency, 5% loss
##! - **congested**: 100ms latency, 10% loss
##! - **intermittent**: Frequent disconnections
##! 
##! @section sensors Available Sensors
##! - Temperature (°C)
##! - Humidity (%)
##! - GPS (latitude/longitude)
##! - Motion (boolean)
##! - Light (lux)
##! - Camera (base64 image)
##! - Device Metrics (CPU, memory)
##! 
##! @section deployment Deployment
##! 
##! @subsection local Local Development
##! @code
##! ./start_all.sh
##! @endcode
##! 
##! @subsection docker Docker
##! @code
##! docker-compose up -d
##! @endcode
##! 
##! @subsection cloud Cloud (AWS)
##! See DOCKER.md for detailed cloud deployment
##! 
##! @section performance Performance
##! - Can simulate up to 6000+ IoT devices
##! - Sub-millisecond metric collection overhead
##! - Supports concurrent experiment execution
##! - Efficient memory usage with circular buffers
##! 
##! @section protocols Supported Protocols
##! - MQTT (lightweight pub/sub)
##! - CoAP (constrained application protocol)
##! - SRTP (secure real-time protocol)
##! - UDP (custom datagram protocol)
##! 
##! @section metrics Collected Metrics
##! - **Latency**: min, max, avg, p50, p75, p90, p95, p99
##! - **Throughput**: packets/sec, bytes/sec
##! - **Loss**: packet loss percentage
##! - **Resources**: CPU usage, memory consumption, energy
##! 
##! @section validation Protocol Validation
##! Automated checks for:
##! - SLA compliance
##! - Throughput requirements
##! - Latency requirements
##! - Resource constraints
##! 
##! @section examples Examples
##! 
##! @subsection example_mqtt Test MQTT Locally
##! @code
##! python stgen/main.py \
##!   --protocol mqtt \
##!   --num-clients 10 \
##!   --duration 30 \
##!   --sensors temperature humidity \
##!   --network-profile perfect
##! @endcode
##! 
##! @subsection example_compare Compare Protocols
##! @code
##! python stgen/main.py \
##!   --compare mqtt,coap,srtp \
##!   --scenario smart_agriculture \
##!   --num-clients 50
##! @endcode
##! 
##! @subsection example_failure Test Robustness
##! @code
##! python stgen/main.py \
##!   --protocol mqtt \
##!   --inject-failures 0.1 \  # 10% packet loss
##!   --num-clients 20 \
##!   --duration 60
##! @endcode
##! 
##! @section contributing Contributing
##! - Add new protocols in protocols/ directory
##! - Extend metrics in metrics_collector.py
##! - Add network profiles in configs/network_conditions/
##! - Submit pull requests
##! 
##! @section license License
##! See LICENSE file for details
##! 
##! @section authors Authors
##! STGen Development Team
##! 
##! @section acknowledgments Acknowledgments
##! Built with FastAPI, React, and Material-UI
##! Network emulation using Linux tc/netem
