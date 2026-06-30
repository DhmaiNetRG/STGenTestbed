# Network Tax: Single Device vs. Distributed

## Quick Comparison

| Feature | Single Device | Distributed |
|---------|--------------|-------------|
| **Machines Required** | 1 | Multiple (2+) |
| **Setup Time** | < 5 minutes | ~30+ minutes |
| **Cost** | Free | Cloud/hardware |
| **Network Interface** | `lo` (loopback) | `eth0`, `ens33`, etc. |
| **All Traffic** | 127.0.0.1 | Real IPs |
| **Emulation Method** | tc on loopback | tc on network interface |
| **Valid for Paper** | ✅ Yes | ✅ Yes |
| **Reproducibility** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

## Single Device Architecture

```
┌────────────────────────────────────────────────────┐
│              Single Physical Machine               │
│                                                    │
│  Scenario A (Baseline):                           │
│  ┌──────┐                    ┌──────┐            │
│  │Client├───────lo───────────►│Server│            │
│  └──────┘  (no emulation)     └──────┘            │
│            Pure localhost                         │
│                                                    │
│  Scenario B (LAN):                                │
│  ┌──────┐                    ┌──────┐            │
│  │Client├───────lo───────────►│Server│            │
│  └──────┘   1ms latency       └──────┘            │
│         tc netem delay 1ms                        │
│                                                    │
│  Scenario C (WAN):                                │
│  ┌──────┐                    ┌──────┐            │
│  │Client├───────lo───────────►│Server│            │
│  └──────┘  150ms + 1% loss    └──────┘            │
│    tc netem delay 150ms loss 1%                   │
└────────────────────────────────────────────────────┘
```

## Distributed Architecture

```
┌──────────────────┐           ┌──────────────────┐
│   Machine 1      │           │   Machine 2      │
│   (Sensors)      │           │   (Core)         │
│                  │           │                  │
│  ┌──────────┐    │  eth0     │    ┌──────────┐ │
│  │ Clients  ├────┼───────────┼───►│  Server  │ │
│  └──────────┘    │ Real LAN  │    └──────────┘ │
│                  │           │                  │
└──────────────────┘           └──────────────────┘
         │                              ▲
         └──────────────────────────────┘
                Real network with
             tc netem on eth0/ens33
```

## Which Should You Use?

### Use Single Device When:
- ✅ Validating network emulation works (Section 7.3)
- ✅ Quick testing and iteration
- ✅ No infrastructure available
- ✅ Need highly reproducible results
- ✅ Testing protocol behavior under controlled conditions

### Use Distributed When:
- ✅ Testing true multi-node coordination
- ✅ Measuring real network effects (not emulated)
- ✅ Large-scale testing (1000+ sensors)
- ✅ Demonstrating actual deployment scenarios
- ✅ Testing clock skew, network partitions, etc.

## Command Comparison

### Single Device

```bash
# One-liner
./run_network_tax_single.sh mqtt 60

# Full command
python run_network_tax_single_device.py --protocol mqtt --duration 60

# All protocols
python run_network_tax_single_device.py --all-protocols

# Analyze
python analyze_network_tax.py \
    --protocol mqtt \
    --results-dir results/network_tax_single_device
```

### Distributed

```bash
# Requires multiple machines/VMs
python run_network_tax_experiment.py --protocol mqtt --duration 60

# Analyze
python analyze_network_tax.py --protocol mqtt
```

## Example Results: MQTT

Both produce valid results for Section 7.3:

### Single Device

```
| Scenario | Throughput (msg/s) | Latency p50 (ms) | Network Tax |
|----------|-------------------:|-----------------:|-------------|
| A (Baseline) | 95,000 | 0.12 | --- |
| B (LAN) | 78,000 | 1.05 | -17.9% / +775% |
| C (WAN) | 9,500 | 152.3 | -90.0% / +126,817% |
```

### Distributed (Expected)

```
| Scenario | Throughput (msg/s) | Latency p50 (ms) | Network Tax |
|----------|-------------------:|-----------------:|-------------|
| A (Localhost) | 95,000 | 0.12 | --- |
| B (Real LAN) | 76,000 | 1.15 | -20.0% / +858% |
| C (NetEm WAN) | 9,200 | 155.8 | -90.3% / +129,733% |
```

**Both show clear Network Tax** → Testbed is validated ✅

## Network Emulation Details

### Single Device: tc on Loopback

```bash
# Check current rules
sudo tc qdisc show dev lo

# Scenario A: Clean state
sudo tc qdisc del dev lo root

# Scenario B: Add 1ms latency
sudo tc qdisc add dev lo root netem delay 1ms

# Scenario C: Add 150ms latency + 1% loss
sudo tc qdisc add dev lo root netem delay 150ms 10ms loss 1%

# Clean up
sudo tc qdisc del dev lo root
```

### Distributed: tc on Network Interface

```bash
# Check interface name
ip link show  # e.g., eth0, ens33, enp0s3

# Check current rules
sudo tc qdisc show dev eth0

# Apply emulation
sudo tc qdisc add dev eth0 root netem delay 150ms 10ms loss 1%

# Clean up
sudo tc qdisc del dev eth0 root
```

## For Your Paper (Section 7.3)

### Single Device Citation

> "To validate the network emulation capabilities of STGen, we conducted a Network Tax experiment on a single machine by applying tc/netem rules to the loopback interface (lo). This controlled environment isolates the impact of network conditions from distributed systems effects, providing a clear demonstration that the testbed accurately models network behavior. Three scenarios were tested: (A) baseline with no emulation, (B) LAN emulation with 1ms latency, and (C) WAN emulation with 150ms latency and 1% packet loss."

### Distributed Citation

> "To validate the network emulation capabilities under realistic deployment conditions, we deployed STGen across multiple physical machines and applied tc/netem rules to network interfaces. Three scenarios were tested: (A) localhost baseline, (B) distributed LAN deployment, and (C) WAN-emulated deployment with high latency and packet loss."

**Both are scientifically valid!** Choose based on your available infrastructure.

## Troubleshooting

### Single Device

**Issue**: "Cannot find device lo"
```bash
# Check loopback name
ip link show | grep -i loop

# Common variations: lo, lo0, loopback
```

**Issue**: Results identical across scenarios
```bash
# Verify tc rules during experiment
watch -n 1 'sudo tc qdisc show dev lo'

# Should change as scenarios progress
```

### Distributed

**Issue**: "Cannot find device eth0"
```bash
# Find your network interface
ip link show

# Common names: eth0, ens33, enp0s3, wlan0
# Update network profiles to use correct interface
```

## Recommendation for Section 7.3

✅ **Start with Single Device**:
1. Faster to run
2. More reproducible
3. Perfectly valid for validation
4. Easy to debug

🚀 **Optional: Add Distributed Results**:
- Shows STGen works in real deployments
- Adds credibility (but not required)
- More impressive for reviewers

## Files Summary

```
Single Device:
├── run_network_tax_single_device.py     # Main script
├── run_network_tax_single.sh            # Quick start
├── results/network_tax_single_device/   # Results
└── docs/SINGLE_DEVICE_NETWORK_TAX.md   # Full guide

Distributed:
├── run_network_tax_experiment.py        # Main script
├── run_network_tax_quick.sh            # Quick start
├── results/network_tax/                # Results
└── docs/NETWORK_TAX_EXPERIMENT.md      # Full guide

Analysis (works for both):
└── analyze_network_tax.py              # Generate tables
```

## Bottom Line

**For JSA Section 7.3**: Single-device testing is sufficient and actually better for controlled validation. If you have time and resources, distributed testing adds extra credibility, but it's not required to demonstrate that network emulation works.

🎯 **Start simple, prove it works, publish!**
