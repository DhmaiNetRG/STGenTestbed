# 🌐 STGen Distributed Deployment Over Public Network

Complete guide for running STGen with multiple clients over public IPs with security.

## 📋 Quick Start Checklist

- [ ] 1. Configure firewall on core machine
- [ ] 2. Set up port forwarding (if behind NAT)
- [ ] 3. Choose and implement security (VPN/SSL/Auth)
- [ ] 4. Measure network characteristics
- [ ] 5. Calculate bandwidth requirements
- [ ] 6. Deploy core node
- [ ] 7. Deploy sensor nodes from different locations

---

## 1. 🔥 Firewall Configuration

### On Core Machine (Linux/Desktop):

```bash
# Check firewall status
sudo ufw status

# Open required ports
sudo ufw allow 1883/tcp   # MQTT
sudo ufw allow 5683/udp   # CoAP
sudo ufw allow 5000/tcp   # STGen default
sudo ufw allow 51820/udp  # WireGuard VPN (if using)

# Enable firewall
sudo ufw enable

# Verify
sudo ufw status numbered
```

### Check what ports your system is using:
```bash
# See what's listening
sudo netstat -tlnp | grep LISTEN

# Check if specific port is open
sudo netstat -tlnp | grep :1883
```

---

## 2. 🌐 NAT/Port Forwarding

### Find your network info:
```bash
# Find your local IP
hostname -I | awk '{print $1}'

# Find your router IP
ip route | grep default | awk '{print $3}'

# Find your public IP
curl -s ifconfig.me
```

### Configure Router:
1. Access router: `http://192.168.1.1` (or your router IP)
2. Navigate to: **Port Forwarding** or **Virtual Server**
3. Add forwarding rules:

| External Port | Internal IP | Internal Port | Protocol |
|--------------|-------------|---------------|----------|
| 1883         | 192.168.x.x | 1883         | TCP      |
| 5683         | 192.168.x.x | 5683         | UDP      |
| 5000         | 192.168.x.x | 5000         | TCP      |

Replace `192.168.x.x` with your core machine's local IP.

### Test port forwarding:
```bash
# From remote machine, test connectivity
nc -zv YOUR_PUBLIC_IP 1883
telnet YOUR_PUBLIC_IP 1883

# Or use online tools:
# https://www.yougetsignal.com/tools/open-ports/
```

---

## 3. 🔒 Security Options

### Option A: WireGuard VPN (RECOMMENDED)

**Advantages:**
- ✅ Encrypted tunnel between all nodes
- ✅ Simple setup, high performance
- ✅ No need to expose individual ports
- ✅ Works great over public internet

**Setup:**
```bash
# Run setup script on EACH machine
cd /home/mehraj-rahman/Desktop/STGen_Future_Present/distributed
./setup_wireguard.sh
```

**Deploy:**
```bash
# Core machine (10.0.0.1 in VPN)
python distributed/core_node.py --bind-ip 10.0.0.1 --protocol mqtt

# Sensor machine A (10.0.0.2 in VPN)
python distributed/sensor_node.py --core-ip 10.0.0.1 --node-id A --sensors 1000

# Sensor machine B (10.0.0.3 in VPN)
python distributed/sensor_node.py --core-ip 10.0.0.1 --node-id B --sensors 1000
```

### Option B: MQTT with SSL/TLS

**Advantages:**
- ✅ Standard MQTT security
- ✅ Works without VPN
- ✅ Certificate-based authentication

**Setup:**
```bash
# Run on core machine only
./setup_mqtt_ssl.sh
```

**Deploy:**
```bash
# Core: Start Mosquitto with SSL
mosquitto -c ~/mqtt-certs/mosquitto_ssl.conf

# Core: Start STGen
python distributed/core_node.py --bind-ip 0.0.0.0 --protocol mqtt --sensor-port 8883

# Sensors: Connect using SSL port
python distributed/sensor_node.py --core-ip YOUR_PUBLIC_IP --core-port 8883 --node-id A --sensors 1000
```

### Option C: API Key Authentication

**Advantages:**
- ✅ Simple token-based auth
- ✅ Prevents unauthorized connections
- ✅ Works with any protocol

**Setup:**
```bash
# Edit SECRET_KEY in sensor_node_secure.py
nano distributed/sensor_node_secure.py
# Change: SECRET_KEY = "your-secret-key-here-change-this"
```

**Deploy:**
```bash
# Use secure sensor node script
python distributed/sensor_node_secure.py \
  --core-ip YOUR_PUBLIC_IP \
  --node-id A \
  --sensors 1000 \
  --api-key "your-secret-key"
```

---

## 4. 📊 Measure Network Characteristics

Before deploying, measure the network between your nodes:

```bash
# Test network quality between sensor and core
./measure_network_tax.sh YOUR_CORE_PUBLIC_IP 60

# This will measure:
# - Latency (ping time)
# - Jitter (latency variation)
# - Packet loss
# - Bandwidth (if iperf3 available)
# - Network path (traceroute)
```

**Install measurement tools:**
```bash
sudo apt install -y iperf3 mtr-tiny traceroute
```

**Run iperf3 bandwidth test:**
```bash
# On CORE machine:
iperf3 -s

# On SENSOR machine:
iperf3 -c YOUR_CORE_PUBLIC_IP -t 30
```

**Expected Results:**

| Network Type | Latency | Jitter | Packet Loss | Bandwidth |
|-------------|---------|--------|-------------|-----------|
| Local LAN | 1-5ms | <1ms | <0.1% | 100-1000 Mbps |
| Same City | 10-30ms | 2-5ms | 0.1-0.5% | 50-200 Mbps |
| Same Country | 30-80ms | 5-15ms | 0.5-1% | 20-100 Mbps |
| International | 100-300ms | 10-50ms | 1-3% | 10-50 Mbps |

---

## 5. 💰 Calculate Bandwidth Requirements

```bash
# Run bandwidth calculator
python distributed/calculate_bandwidth.py

# Or calculate for your specific scenario:
# Example: 5000 sensors, 1 msg/sec each, 100 bytes
```

**Example scenarios:**

| Sensors | Msg/sec/sensor | Msg Size | Bandwidth | Monthly Data |
|---------|---------------|----------|-----------|--------------|
| 1,000 | 0.1 | 50B | 0.7 Kbps | 0.2 GB |
| 5,000 | 0.2 | 100B | 13 Kbps | 3.5 GB |
| 10,000 | 0.5 | 150B | 98 Kbps | 26 GB |
| 1,000 | 5.0 | 80B | 52 Kbps | 14 GB |

**Rule of thumb:**
- Add 50% buffer for peaks and overhead
- Monitor during tests and adjust
- Consider message frequency vs data freshness tradeoff

---

## 6. 🚀 Complete Deployment Example

### Scenario: 3 sensor nodes in different locations → 1 core

**Architecture:**
- **Core**: Your desktop (Public IP: 203.0.113.10)
- **Sensor A**: Windows laptop (Public IP: 198.51.100.5) - 2000 sensors
- **Sensor B**: Remote server (Public IP: 192.0.2.8) - 3000 sensors
- **Sensor C**: Cloud VM (Public IP: 203.0.114.22) - 1000 sensors

### Step 1: Prepare Core Machine

```bash
# 1. Open firewall
sudo ufw allow 1883/tcp
sudo ufw allow 5000/tcp

# 2. Verify public IP
curl ifconfig.me

# 3. Start core node
cd /home/mehraj-rahman/Desktop/STGen_Future_Present
source myenv/bin/activate
python distributed/core_node.py \
  --bind-ip 0.0.0.0 \
  --protocol mqtt \
  --duration 600
```

### Step 2: Deploy Sensor Nodes

**On each sensor machine:**

```bash
# Sensor A (Windows - adjust paths)
python distributed\sensor_node.py ^
  --core-ip 203.0.113.10 ^
  --node-id SensorA ^
  --sensors 2000 ^
  --protocol mqtt

# Sensor B (Linux)
python distributed/sensor_node.py \
  --core-ip 203.0.113.10 \
  --node-id SensorB \
  --sensors 3000 \
  --protocol mqtt

# Sensor C (Linux)
python distributed/sensor_node.py \
  --core-ip 203.0.113.10 \
  --node-id SensorC \
  --sensors 1000 \
  --protocol mqtt
```

### Step 3: Monitor

```bash
# On core machine, monitor logs
tail -f logs/*

# Check MQTT broker connections
mosquitto_sub -h localhost -t "stgen/#" -v

# Monitor system resources
htop
```

---

## 🔍 Troubleshooting

### Connection Refused

```bash
# Check if port is listening
sudo netstat -tlnp | grep 1883

# Check firewall
sudo ufw status

# Test from sensor machine
telnet CORE_PUBLIC_IP 1883
```

### High Latency

```bash
# Measure latency
ping -c 100 CORE_PUBLIC_IP

# Check for packet loss
mtr CORE_PUBLIC_IP

# Consider reducing message frequency or using compression
```

### Authentication Failed

```bash
# Check MQTT logs
sudo tail -f /var/log/mosquitto/mosquitto.log

# Verify credentials
mosquitto_pub -h CORE_IP -p 1883 -t test -m "hello" -d
```

### Bandwidth Issues

```bash
# Monitor bandwidth usage
sudo iftop -i eth0

# Test available bandwidth
iperf3 -c CORE_PUBLIC_IP -t 30

# Reduce message rate if needed
# Edit sensor_node.py and adjust --sensors or message frequency
```

---

## 📝 Best Practices

1. **Start Small**: Test with 1-2 sensor nodes first
2. **Monitor Resources**: Watch CPU, memory, network on core
3. **Use QoS**: Set MQTT QoS level 1 or 2 for important messages
4. **Log Everything**: Keep logs for debugging
5. **Automate**: Use systemd services for auto-restart
6. **Backup Configs**: Save working configurations
7. **Test Failures**: Simulate network issues before production

---

## 🛠️ Scripts Reference

| Script | Purpose |
|--------|---------|
| `setup_wireguard.sh` | Generate VPN configs for secure tunnel |
| `setup_mqtt_ssl.sh` | Create SSL certificates for MQTT |
| `sensor_node_secure.py` | Sensor node with API key authentication |
| `measure_network_tax.sh` | Test network latency, jitter, packet loss |
| `calculate_bandwidth.py` | Estimate bandwidth requirements |
| `core_node.py` | Run core node (broker + subscriber) |
| `sensor_node.py` | Run sensor node (clients only) |

---

## 📞 Need Help?

Check logs in: `/home/mehraj-rahman/Desktop/STGen_Future_Present/logs/`

Common issues:
- Port not open → Check firewall and port forwarding
- Connection timeout → Verify public IP is correct
- High latency → Consider VPN or regional servers
- Authentication error → Check credentials and tokens
