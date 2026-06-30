# 🏗️ STGen Three-Tier Architecture

Complete guide for deploying STGen with sensors, core server, and query clients.

## 📐 Architecture Overview

```
┌─────────────────────┐
│  Query Clients      │  (Tier 3: Request data)
│  - Web Dashboard    │
│  - Mobile Apps      │
│  - Analytics Tools  │
└──────────┬──────────┘
           │ Request specific data
           ↓
┌─────────────────────┐
│  Core Server        │  (Tier 2: Broker/Aggregator)
│  - MQTT Broker      │
│  - Data Buffer      │
│  - Query Handler    │
└──────────┬──────────┘
           │ Publish sensor data
           ↑
┌─────────────────────┐
│  Sensor Nodes       │  (Tier 1: Data Sources)
│  - IoT Devices      │
│  - Sensor Clusters  │
│  - Edge Nodes       │
└─────────────────────┘
```

## 🔄 Data Flow

### 1. **Sensor → Core (Push Model)**
- Sensors publish data to core continuously
- Core buffers recent data
- MQTT topics organize data by type/node

### 2. **Client → Core (Pull Model)**
- Clients request specific data via queries
- Filters: node_id, sensor_type, time range, value range
- Real-time or historical data

### 3. **Hybrid Model**
- Clients can subscribe (passive) OR query (active)
- Best of both worlds

---

## 🚀 Deployment Guide

### Tier 1: Sensor Nodes (Data Publishers)

**Multiple sensor nodes across different locations:**

```bash
# Node A - Smart Home (2000 sensors)
python distributed/sensor_node.py \
  --core-ip CORE_PUBLIC_IP \
  --node-id SmartHome_A \
  --sensors 2000 \
  --sensor-types "temp,humidity,motion,door" \
  --protocol mqtt

# Node B - Industrial Site (3000 sensors)
python distributed/sensor_node.py \
  --core-ip CORE_PUBLIC_IP \
  --node-id Industrial_B \
  --sensors 3000 \
  --sensor-types "temp,pressure,vibration,flow" \
  --protocol mqtt

# Node C - Healthcare (1000 sensors)
python distributed/sensor_node.py \
  --core-ip CORE_PUBLIC_IP \
  --node-id Healthcare_C \
  --sensors 1000 \
  --sensor-types "heartrate,spo2,temp,bp" \
  --protocol mqtt
```

### Tier 2: Core Server (Broker + Aggregator)

**Runs on central server with public IP:**

```bash
# Start core server with data buffering
python distributed/core_node.py \
  --bind-ip 0.0.0.0 \
  --protocol mqtt \
  --sensor-port 1883 \
  --duration 3600
```

**Core responsibilities:**
- Run MQTT broker (Mosquitto)
- Receive sensor data from all nodes
- Buffer recent data (configurable window)
- Handle query requests from clients
- Aggregate metrics

### Tier 3: Query Clients (Data Consumers)

**Multiple clients can query simultaneously:**

```bash
# Client 1 - Dashboard (query all temp sensors)
python distributed/query_client.py \
  --server-ip CORE_PUBLIC_IP \
  --protocol mqtt \
  --query-filter '{"sensor_type": "temp"}' \
  --query-interval 10 \
  --duration 3600

# Client 2 - Mobile App (query specific node)
python distributed/query_client.py \
  --server-ip CORE_PUBLIC_IP \
  --protocol mqtt \
  --query-filter '{"node_id": "SmartHome_A"}' \
  --query-interval 5 \
  --duration 600

# Client 3 - Analytics (high values only)
python distributed/query_client.py \
  --server-ip CORE_PUBLIC_IP \
  --protocol mqtt \
  --query-filter '{"sensor_type": "temp", "min_value": 30}' \
  --query-interval 15 \
  --duration 1800

# Client 4 - One-time query
python distributed/query_client.py \
  --server-ip CORE_PUBLIC_IP \
  --protocol mqtt \
  --query-filter '{"node_id": "Industrial_B", "sensor_type": "pressure"}' \
  --once
```

---

## 🔍 Query Filter Options

### Available Filters:

| Filter | Type | Example | Description |
|--------|------|---------|-------------|
| `node_id` | string | `"SmartHome_A"` | Filter by specific sensor node |
| `sensor_type` | string/list | `"temp"` or `["temp", "humidity"]` | Filter by sensor type(s) |
| `dev_id` | string | `"temp_001"` | Filter by specific device |
| `min_value` | number | `25.0` | Minimum sensor reading |
| `max_value` | number | `100.0` | Maximum sensor reading |
| `time_range` | object | `{"start": ts, "end": ts}` | Time window (future) |

### Example Query Filters:

```json
// All temperature sensors
{"sensor_type": "temp"}

// Specific node
{"node_id": "SmartHome_A"}

// High temperature alerts
{"sensor_type": "temp", "min_value": 35}

// Multiple sensor types from one node
{"node_id": "Healthcare_C", "sensor_type": ["heartrate", "spo2"]}

// Normal range monitoring
{"sensor_type": "pressure", "min_value": 90, "max_value": 120}

// Specific device
{"dev_id": "temp_042"}
```

---

## 🌐 Complete Public Network Example

### Setup: 3 Sensor Nodes + 1 Core + 2 Query Clients

**Network Topology:**
```
Sensor Node A (Tokyo)     → Core (AWS US-East)    ← Query Client 1 (Web Dashboard)
Sensor Node B (London)    →                        ← Query Client 2 (Mobile App)
Sensor Node C (Mumbai)    →
```

### Step 1: Configure Core (AWS/VPS)

```bash
# Find public IP
PUBLIC_IP=$(curl -s ifconfig.me)
echo "Core Public IP: $PUBLIC_IP"

# Configure firewall
sudo ufw allow 1883/tcp
sudo ufw allow 22/tcp
sudo ufw enable

# Start core
cd STGen_Future_Present
source myenv/bin/activate
python distributed/core_node.py --bind-ip 0.0.0.0 --protocol mqtt --duration 86400
```

### Step 2: Deploy Sensor Nodes (Different Locations)

**Tokyo Node:**
```bash
python distributed/sensor_node.py \
  --core-ip 203.0.113.10 \
  --node-id Tokyo_A \
  --sensors 1500 \
  --sensor-types "temp,humidity,aqi" \
  --protocol mqtt
```

**London Node:**
```bash
python distributed/sensor_node.py \
  --core-ip 203.0.113.10 \
  --node-id London_B \
  --sensors 2000 \
  --sensor-types "temp,humidity,motion" \
  --protocol mqtt
```

**Mumbai Node:**
```bash
python distributed/sensor_node.py \
  --core-ip 203.0.113.10 \
  --node-id Mumbai_C \
  --sensors 1000 \
  --sensor-types "temp,humidity,light" \
  --protocol mqtt
```

### Step 3: Deploy Query Clients (Anywhere)

**Dashboard Client (Laptop):**
```bash
python distributed/query_client.py \
  --server-ip 203.0.113.10 \
  --protocol mqtt \
  --query-filter '{}' \
  --query-interval 5 \
  --duration 3600 \
  --output dashboard_data.json
```

**Mobile Analytics Client:**
```bash
python distributed/query_client.py \
  --server-ip 203.0.113.10 \
  --protocol mqtt \
  --query-filter '{"sensor_type": "temp"}' \
  --query-interval 10 \
  --duration 7200 \
  --output mobile_temp_data.json
```

---

## 📊 Query Modes

### Mode 1: Continuous Monitoring (Default)

```bash
# Query every 5 seconds for 1 hour
python distributed/query_client.py \
  --server-ip CORE_IP \
  --query-filter '{"sensor_type": "temp"}' \
  --query-interval 5 \
  --duration 3600
```

**Output:**
```
======================================================
Query #1 - Collected 42 messages so far
======================================================
✓ Found 15 matching messages
Showing last 5 results:
  [1] Node: Tokyo_A | Device: temp_023
      Data: {'value': 25.3, 'unit': 'celsius'}
      Time: 14:32:15
  [2] Node: London_B | Device: temp_087
      Data: {'value': 18.7, 'unit': 'celsius'}
      Time: 14:32:16
  ...
```

### Mode 2: One-Time Query

```bash
# Single query and exit
python distributed/query_client.py \
  --server-ip CORE_IP \
  --query-filter '{"node_id": "Tokyo_A"}' \
  --once
```

### Mode 3: Alert Monitoring

```bash
# Only high temperature alerts
python distributed/query_client.py \
  --server-ip CORE_IP \
  --query-filter '{"sensor_type": "temp", "min_value": 40}' \
  --query-interval 1 \
  --duration 86400
```

---

## 🔧 Advanced Features

### 1. Multi-Client Concurrent Queries

Multiple clients can query simultaneously without interference:

```bash
# Terminal 1 - Temperature monitoring
python distributed/query_client.py --server-ip X --query-filter '{"sensor_type": "temp"}' &

# Terminal 2 - Humidity monitoring
python distributed/query_client.py --server-ip X --query-filter '{"sensor_type": "humidity"}' &

# Terminal 3 - Node-specific monitoring
python distributed/query_client.py --server-ip X --query-filter '{"node_id": "Tokyo_A"}' &
```

### 2. Data Export for Analytics

```bash
# Collect data for 1 hour, export to JSON
python distributed/query_client.py \
  --server-ip CORE_IP \
  --query-filter '{}' \
  --duration 3600 \
  --output analytics_data.json

# Then analyze with Python/R/Excel
python analyze_exported_data.py analytics_data.json
```

### 3. Real-Time Dashboard Integration

```python
# Custom dashboard script
from distributed.query_client import QueryClient

client = QueryClient("mqtt", "CORE_IP", 1883, {"topic": "stgen/sensors"})
client.connect()

while True:
    # Get latest data
    data = client.query_data({"sensor_type": "temp"})
    
    # Update dashboard
    update_temperature_chart(data)
    
    time.sleep(5)
```

---

## 🛡️ Security Considerations

### For Public Networks:

1. **Use WireGuard VPN** (recommended)
   - Encrypts all traffic
   - See: `setup_wireguard.sh`

2. **Enable MQTT Authentication**
   ```bash
   # Create password file
   mosquitto_passwd -c /etc/mosquitto/passwd username
   
   # Update mosquitto.conf
   allow_anonymous false
   password_file /etc/mosquitto/passwd
   ```

3. **Client authentication in queries**
   ```bash
   # Add to query_client.py
   python distributed/query_client.py \
     --server-ip CORE_IP \
     --mqtt-username admin \
     --mqtt-password secret123 \
     --query-filter '{}'
   ```

---

## 📈 Scalability

### Scale by Node Count:
- ✅ **10 sensor nodes**: Easy, standard setup
- ✅ **50 sensor nodes**: Add load balancer
- ✅ **100+ nodes**: Multiple core servers with clustering

### Scale by Client Count:
- ✅ **10 query clients**: No problem
- ✅ **50 clients**: Monitor broker load
- ✅ **100+ clients**: Use dedicated query broker

### Scale by Sensor Count per Node:
- ✅ **1K sensors/node**: Standard
- ✅ **10K sensors/node**: Adjust message rate
- ✅ **100K+ sensors/node**: Batch messages

---

## 🔍 Monitoring & Debugging

### Monitor Core Server:

```bash
# Watch MQTT traffic
mosquitto_sub -h localhost -t "stgen/#" -v

# Monitor connections
watch -n 1 'netstat -tnp | grep :1883'

# Check system resources
htop
```

### Test Query Client:

```bash
# Simple connectivity test
python distributed/query_client.py \
  --server-ip CORE_IP \
  --query-filter '{}' \
  --once \
  --debug
```

### View Collected Data:

```bash
# Pretty print results
cat results/query_results.json | jq '.[] | select(.node_id == "Tokyo_A")'
```

---

## 📝 Use Cases

### Use Case 1: Smart Building Management
```bash
# Core: Building server
# Sensors: Floor A, B, C (HVAC, lights, occupancy)
# Clients: Facility dashboard, mobile app, energy analytics
```

### Use Case 2: Industrial IoT
```bash
# Core: Cloud server (AWS/Azure)
# Sensors: Factory 1, 2, 3 (machines, environment)
# Clients: Operations dashboard, maintenance alerts, ML pipeline
```

### Use Case 3: Healthcare Monitoring
```bash
# Core: Hospital server
# Sensors: Patient wards (vital signs, equipment)
# Clients: Nurse stations, doctor tablets, alarm system
```

---

## 🎯 Quick Start Commands

```bash
# 1. Start core
python distributed/core_node.py --bind-ip 0.0.0.0 --protocol mqtt

# 2. Start sensor node
python distributed/sensor_node.py --core-ip CORE_IP --node-id MyNode --sensors 1000

# 3. Start query client
python distributed/query_client.py --server-ip CORE_IP --query-filter '{"sensor_type": "temp"}' --query-interval 5

# 4. View results
cat results/query_results.json | jq '.'
```

---

## 📚 Related Documentation

- [PUBLIC_NETWORK_DEPLOYMENT.md](PUBLIC_NETWORK_DEPLOYMENT.md) - Public internet deployment
- [../docs/NETWORK_TAX_EXPERIMENT.md](../docs/NETWORK_TAX_EXPERIMENT.md) - Network performance testing
- [sensor_node.py](sensor_node.py) - Sensor node implementation
- [core_node.py](core_node.py) - Core server implementation
- [query_client.py](query_client.py) - Query client implementation
