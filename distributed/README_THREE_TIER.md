# 🚀 STGen 3-Tier Quick Reference

## Yes! You can have clients request sensor data!

Your system already supports a **three-tier architecture**:

```
Tier 1: SENSORS      →  Tier 2: CORE SERVER  ←  Tier 3: QUERY CLIENTS
(Publishers)            (Broker/Aggregator)      (Data Consumers)
```

---

## 📋 Quick Commands

### Start Core Server (Tier 2)
```bash
python distributed/core_node.py --bind-ip 0.0.0.0 --protocol mqtt
```

### Start Sensor Node (Tier 1)
```bash
python distributed/sensor_node.py \
  --core-ip CORE_IP \
  --node-id MyNode \
  --sensors 1000 \
  --protocol mqtt
```

### Start Query Client (Tier 3)
```bash
# Query all temperature sensors
python distributed/query_client.py \
  --server-ip CORE_IP \
  --query-filter '{"sensor_type": "temp"}' \
  --query-interval 5

# Query specific node
python distributed/query_client.py \
  --server-ip CORE_IP \
  --query-filter '{"node_id": "MyNode"}' \
  --once

# Query high values only
python distributed/query_client.py \
  --server-ip CORE_IP \
  --query-filter '{"sensor_type": "temp", "min_value": 30}' \
  --query-interval 10
```

---

## 🎯 Example Scenarios

### Scenario 1: Local Testing
```bash
# Terminal 1: Core
python distributed/core_node.py --bind-ip 127.0.0.1 --protocol mqtt

# Terminal 2: Sensor
python distributed/sensor_node.py --core-ip 127.0.0.1 --node-id Test --sensors 100

# Terminal 3: Query Client
python distributed/query_client.py --server-ip 127.0.0.1 --query-filter '{}' --query-interval 5
```

### Scenario 2: Public Network (Multiple Locations)
```bash
# On Core Server (AWS/VPS - Public IP: 203.0.113.10)
sudo ufw allow 1883/tcp
python distributed/core_node.py --bind-ip 0.0.0.0 --protocol mqtt

# On Sensor Node 1 (Tokyo)
python distributed/sensor_node.py --core-ip 203.0.113.10 --node-id Tokyo --sensors 2000

# On Sensor Node 2 (London)
python distributed/sensor_node.py --core-ip 203.0.113.10 --node-id London --sensors 1500

# On Query Client (Laptop anywhere)
python distributed/query_client.py --server-ip 203.0.113.10 --query-filter '{"node_id": "Tokyo"}'
```

### Scenario 3: Multiple Clients Simultaneously
```bash
# Client 1: Temperature dashboard
python distributed/query_client.py --server-ip CORE_IP --query-filter '{"sensor_type": "temp"}' &

# Client 2: Mobile app (specific node)
python distributed/query_client.py --server-ip CORE_IP --query-filter '{"node_id": "Building_A"}' &

# Client 3: Analytics (all data)
python distributed/query_client.py --server-ip CORE_IP --query-filter '{}' --output analytics.json &
```

---

## 🔍 Query Filter Examples

```json
// All sensors from specific node
{"node_id": "SmartHome_A"}

// All temperature sensors
{"sensor_type": "temp"}

// Multiple sensor types
{"sensor_type": ["temp", "humidity"]}

// High temperature alert
{"sensor_type": "temp", "min_value": 35}

// Normal range monitoring
{"sensor_type": "pressure", "min_value": 90, "max_value": 120}

// Specific device
{"dev_id": "temp_042"}

// Combine filters
{"node_id": "Factory_B", "sensor_type": "vibration", "min_value": 50}
```

---

## 🛠️ Tools & Scripts

| Script | Purpose |
|--------|---------|
| `deploy_three_tier.sh` | Interactive deployment wizard |
| `demo_three_tier.sh` | Local demo (all 3 tiers) |
| `query_client.py` | Request/query sensor data |
| `core_node.py` | Central broker |
| `sensor_node.py` | Data publisher |

---

## 🎬 Try the Demo

```bash
# Run complete local demo
cd distributed
./demo_three_tier.sh
```

This starts:
- 1 core server
- 2 sensor nodes (Office_A, Warehouse_B)
- 3 query clients (different filters)

---

## 📖 Full Documentation

- **[THREE_TIER_ARCHITECTURE.md](THREE_TIER_ARCHITECTURE.md)** - Complete guide
- **[PUBLIC_NETWORK_DEPLOYMENT.md](PUBLIC_NETWORK_DEPLOYMENT.md)** - Public internet setup

---

## 💡 Key Features

✅ **Multiple clients can query simultaneously**
✅ **Filter by node, sensor type, value range**
✅ **Continuous monitoring or one-time queries**
✅ **Works over local network AND public internet**
✅ **Real-time data requests**
✅ **Export results to JSON**

---

## 🚀 Quick Start (3 Commands)

```bash
# 1. Interactive setup
./deploy_three_tier.sh

# 2. Or use demo
./demo_three_tier.sh

# 3. Or manual
python distributed/query_client.py --server-ip YOUR_CORE_IP --query-filter '{"sensor_type": "temp"}'
```

---

**Your system fully supports request-response with query clients!** 🎉
