# Running Network Tax on a Single Device

## Overview

You can run the **complete Network Tax experiment on a single machine** without needing multiple physical devices or a distributed network. This works by:

1. Running all components (clients + server) on **localhost (127.0.0.1)**
2. Applying **network emulation to the loopback interface** (`lo`)
3. Comparing three scenarios with different network conditions on the same machine

## Key Insight

The "Network Tax" can be demonstrated on a single device because:
- **Scenario A**: No emulation = pure localhost performance (baseline)
- **Scenario B**: Apply 1ms latency to loopback = simulates LAN
- **Scenario C**: Apply 150ms latency + 1% loss = simulates WAN

The performance degradation proves that network emulation works correctly, even when all traffic is local.

## Quick Start

### 1. Single Protocol Test

```bash
# Run experiment for MQTT
python run_network_tax_single_device.py --protocol mqtt --duration 60

# Run for CoAP
python run_network_tax_single_device.py --protocol coap --duration 60
```

### 2. All Protocols

```bash
python run_network_tax_single_device.py --all-protocols --duration 120
```

### 3. Analyze Results

```bash
# Markdown table
python analyze_network_tax.py --protocol mqtt --results-dir results/network_tax_single_device

# LaTeX table for paper
python analyze_network_tax.py --all --results-dir results/network_tax_single_device --format latex
```

## How It Works

### Network Emulation on Loopback

Linux `tc` (traffic control) can apply network conditions to **any interface**, including `lo` (loopback):

```bash
# Scenario A: No emulation (baseline)
# (no tc rules applied)

# Scenario B: LAN emulation on loopback
sudo tc qdisc add dev lo root netem delay 1ms

# Scenario C: WAN emulation on loopback  
sudo tc qdisc add dev lo root netem delay 150ms 10ms loss 1% rate 10000kbit
```

All traffic to/from `127.0.0.1` goes through these rules, simulating network conditions.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Single Device                         │
│                                                         │
│  ┌──────────────┐         ┌──────────────┐            │
│  │   Clients    │         │    Server    │            │
│  │ (Sensors)    │◄───────►│ (Protocol    │            │
│  │              │   lo    │  Broker)     │            │
│  └──────────────┘         └──────────────┘            │
│         │                        ▲                     │
│         │                        │                     │
│         └────────────────────────┘                     │
│              127.0.0.1 with                            │
│           tc netem emulation                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Three Scenarios

| Scenario | tc Command | Expected Result |
|----------|-----------|-----------------|
| **A (Baseline)** | *(none)* | Max throughput (~100k msg/s), min latency (~0.1ms) |
| **B (LAN)** | `netem delay 1ms` | ~80k msg/s, ~1ms latency (20% tax) |
| **C (WAN)** | `netem delay 150ms 10ms loss 1%` | ~10k msg/s, ~150ms latency (90% tax) |

## Requirements

### System Requirements

- **Linux** (Ubuntu/Debian recommended)
- **Sudo access** (for `tc` commands)
- **Python 3.8+**
- **netem kernel module** (usually included)

### Verify Setup

```bash
# Check if tc is available
which tc

# Check if netem module is loaded
lsmod | grep sch_netem

# Test tc on loopback (requires sudo)
sudo tc qdisc add dev lo root netem delay 1ms
sudo tc qdisc del dev lo root
```

## Expected Results

### Example: MQTT on Single Device

```
| Scenario | Throughput (msg/s) | Latency p50 (ms) | Network Tax |
|----------|-------------------:|-----------------:|-------------|
| A (Baseline) | 95,000 | 0.12 | --- |
| B (LAN) | 78,000 | 1.05 | -17.9% / +775% |
| C (WAN) | 9,500 | 152.3 | -90.0% / +126,817% |
```

The clear degradation proves:
1. **Network emulation works** on loopback
2. **Testbed is valid** - shows predictable performance impact
3. **Protocol behavior is realistic** - matches expected network effects

## Troubleshooting

### "Permission denied" for tc

```bash
# Grant sudo access
sudo -v

# Or run with sudo directly
sudo python run_network_tax_single_device.py --protocol mqtt
```

### Network interface issues

If `lo` doesn't work, check your loopback interface name:

```bash
# List interfaces
ip link show

# Common names: lo, lo0, loopback
```

Edit the script to use your interface name (search for `"lo"` and replace).

### Results identical across scenarios

If all scenarios show the same performance:

```bash
# Verify tc rules are applied
sudo tc qdisc show dev lo

# Should show "netem" during scenarios B and C
# Should show "noqueue" or nothing during scenario A
```

### Performance too low even in baseline

```bash
# Ensure no emulation rules from previous runs
sudo tc qdisc del dev lo root 2>/dev/null

# Check system resources
top
free -h

# Reduce load
python run_network_tax_single_device.py --protocol mqtt --num-sensors 100 --duration 30
```

## Advantages of Single-Device Testing

✅ **No infrastructure needed**: No VMs, containers, or physical machines required  
✅ **Reproducible**: Eliminates variability from actual networks  
✅ **Fast iteration**: Quick to run, easy to debug  
✅ **Cost-effective**: No cloud resources or hardware  
✅ **Scientifically valid**: Network Tax is still demonstrable  

## Limitations

⚠️ **CPU contention**: Both client and server compete for same CPU  
⚠️ **Memory sharing**: May hit system limits with very large scale  
⚠️ **No true distribution**: Can't test multi-node coordination  

However, for **Section 7.3's purpose** (proving network emulation works), single-device testing is perfectly valid.

## Comparison: Single Device vs. Distributed

| Aspect | Single Device | Distributed |
|--------|--------------|-------------|
| **Setup** | 1 machine | Multiple machines/VMs |
| **Cost** | Free | Cloud/hardware costs |
| **Reproducibility** | High | Medium (network variability) |
| **Realism** | Network emulated | Real network |
| **Scale** | Limited by CPU/RAM | Nearly unlimited |
| **For Section 7.3** | ✅ Sufficient | ✅ Ideal but not required |

## Integration with Paper

For Section 7.3, you can note:

> "To demonstrate the validity of network emulation, we conducted the Network Tax experiment on a single device by applying tc/netem rules to the loopback interface. This approach isolates the impact of network conditions from other distributed systems effects (e.g., clock skew, partial failures), providing a controlled validation of the testbed's network modeling capabilities."

This is actually **better** for validation because it's more controlled!

## Next Steps

1. **Run the experiment**:
   ```bash
   python run_network_tax_single_device.py --protocol mqtt --duration 60
   ```

2. **Verify degradation**:
   - Check that Scenario B shows ~20% tax
   - Check that Scenario C shows ~90% tax

3. **Generate tables**:
   ```bash
   python analyze_network_tax.py --all \
       --results-dir results/network_tax_single_device \
       --format latex > paper/tables/network_tax.tex
   ```

4. **Add to paper**: Use the results to validate your testbed in Section 7.3

## Files

```
run_network_tax_single_device.py   # Single-device experiment runner
results/network_tax_single_device/  # Results directory
```

The analysis script (`analyze_network_tax.py`) works with both single-device and distributed results—just specify the correct `--results-dir`.
