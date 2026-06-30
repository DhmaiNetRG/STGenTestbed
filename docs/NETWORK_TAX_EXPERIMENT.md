# Network Tax Experiment Guide (Section 7.3)

## Overview

The **Network Tax Experiment** demonstrates that STGen's distributed deployment correctly adheres to network profiles by measuring performance degradation across three deployment scenarios. This validates the testbed's network emulation capabilities—a critical requirement for JSA publication.

## Hypothesis

Network conditions should predictably impact protocol performance:

- **Scenario A (Localhost)**: Minimal overhead → Maximum throughput, minimum latency
- **Scenario B (Distributed LAN)**: LAN overhead (1ms RTT) → Moderate degradation
- **Scenario C (WAN Emulated)**: High latency + packet loss → Significant degradation

**Key Insight**: If results are identical across all scenarios, the emulation is broken. If they show predictable degradation, the testbed is valid.

## Network Profiles

### Scenario A: Localhost (Baseline)
```json
{
  "latency_ms": 0,
  "jitter_ms": 0,
  "loss_percent": 0.0,
  "bandwidth_kbps": 0
}
```
**Expected**: Throughput ≈ 100k msg/sec, Latency ≈ 0.1ms

### Scenario B: Distributed LAN
```json
{
  "latency_ms": 1,
  "jitter_ms": 0,
  "loss_percent": 0.0,
  "bandwidth_kbps": 1000000
}
```
**Expected**: Throughput ≈ 80k msg/sec (20% tax), Latency ≈ 1.0ms

### Scenario C: WAN Emulated
```json
{
  "latency_ms": 150,
  "jitter_ms": 10,
  "loss_percent": 1.0,
  "bandwidth_kbps": 10000
}
```
**Expected**: Throughput ≈ 10k msg/sec (90% tax), Latency ≈ 150ms

## Running the Experiment

### Single Device (Recommended for Quick Testing)

**Run everything on one machine** using loopback network emulation:

```bash
# Single protocol test
python run_network_tax_single_device.py --protocol mqtt --duration 60

# Test all protocols
python run_network_tax_single_device.py --all-protocols --duration 120

# Custom configuration
python run_network_tax_single_device.py \
    --protocol coap \
    --num-sensors 1000 \
    --duration 300
```

✅ **Advantages**: No infrastructure needed, faster, perfectly valid for Section 7.3  
📖 **Full Guide**: See [docs/SINGLE_DEVICE_NETWORK_TAX.md](SINGLE_DEVICE_NETWORK_TAX.md)

### Distributed Deployment (Optional)

For true multi-node testing across physical/virtual machines:

```bash
# Distributed test (requires multiple machines)
python run_network_tax_experiment.py --protocol mqtt --duration 60

# Test all protocols
python run_network_tax_experiment.py --all-protocols --duration 120
```

### Step-by-Step (Single Device)

1. **Ensure clean environment**:
   ```bash
   sudo tc qdisc del dev lo root 2>/dev/null || true
   ```

2. **Run experiment** (requires sudo for network emulation):
   ```bash
   # Single protocol
   python run_network_tax_single_device.py --protocol mqtt
   
   # All protocols
   python run_network_tax_single_device.py --all-protocols
   ```

3. **Analyze results**:
   ```bash
   # Markdown table
   python analyze_network_tax.py --protocol mqtt --results-dir results/network_tax_single_device
   
   # LaTeX table for paper
   python analyze_network_tax.py --all \
       --results-dir results/network_tax_single_device \
       --format latex > paper/tables/network_tax.tex
   ```

## Expected Results

### Example: MQTT

| Scenario | Deployment | Throughput (msg/s) | Latency p50 (ms) | Network Tax |
|----------|------------|-------------------:|------------------:|-------------|
| A | Localhost | 95,000 | 0.12 | Baseline |
| B | Distributed LAN | 78,000 | 1.05 | -17.9% / +775% |
| C | WAN Emulated | 9,500 | 152.3 | -90.0% / +126,817% |

### Protocol-Specific Behaviors

**CoAP (Confirmable)**:
- Should show **retransmission behavior** under packet loss
- Scenario C: Increased latency due to ACK timeouts
- Loss recovery increases throughput tax

**Custom UDP**:
- **No retransmission** → packets are simply dropped
- Scenario C: High packet loss directly reduces effective throughput
- Latency remains low for successful packets

**MQTT (QoS 1)**:
- **Delivery guarantees** maintained despite loss
- Scenario C: Throughput degradation due to retransmissions
- Should maintain near-zero packet loss even in WAN

**SRTP**:
- **Encryption overhead** should be consistent across scenarios
- Network tax primarily from transport, not cryptography
- Demonstrates security doesn't compound network effects

## Interpretation for Section 7.3

### What Makes a Valid Result

✅ **VALID** - Results show clear degradation:
- Localhost: Highest throughput, lowest latency
- LAN: Moderate degradation (~20%)
- WAN: Significant degradation (~90%)

❌ **INVALID** - Results are identical:
- All scenarios show same metrics → Network emulation not working
- No observable network tax → Testbed cannot validate protocols

### Key Insights to Highlight

1. **Predictable Degradation**: Network conditions impact performance in expected ways
2. **Protocol Resilience**: Different protocols handle impairments differently
   - CoAP: Retransmission adds overhead
   - UDP: Drops packets, no recovery
   - MQTT: Maintains reliability at cost of throughput
3. **Emulation Validity**: Results prove NetEm accurately models real network conditions
4. **Testbed Realism**: STGen can reproduce field conditions in controlled environment

## Paper Table Format

For Section 7.3, use this structure:

```latex
\begin{table*}[htbp]
\centering
\caption{Network Tax Analysis: Impact of Deployment Scenarios on Protocol Performance}
\label{tab:network_tax}
\begin{tabular}{llrrrrr}
\toprule
Protocol & Scenario & Throughput & Latency & Latency & \multicolumn{2}{c}{Network Tax} \\
 &  & (msg/s) & p50 (ms) & p95 (ms) & Throughput & Latency \\
\midrule
MQTT & Localhost & 95,000 & 0.12 & 0.25 & --- & --- \\
     & LAN       & 78,000 & 1.05 & 1.82 & -17.9\% & +775\% \\
     & WAN       & 9,500  & 152.3 & 187.5 & -90.0\% & +126,817\% \\
\midrule
CoAP & Localhost & 88,000 & 0.15 & 0.35 & --- & --- \\
     & LAN       & 72,000 & 1.12 & 2.05 & -18.2\% & +647\% \\
     & WAN       & 8,200  & 158.7 & 245.2 & -90.7\% & +105,700\% \\
\bottomrule
\end{tabular}
\end{table*}
```

## Troubleshooting

### Network emulation not working
```bash
# Check tc rules
sudo tc qdisc show dev eth0

# Verify permissions
sudo -v

# Check kernel modules
lsmod | grep sch_netem
```

### Results identical across scenarios
- Ensure network profile is being loaded
- Check that `sudo` permissions allow `tc` commands
- Verify correct network interface (eth0 vs ens33 vs enp0s3)

### Performance too low in localhost
- Disable unnecessary network emulation
- Check system resources (CPU, memory)
- Reduce sensor count or message rate

## Files Created

```
configs/network_conditions/
├── localhost.json           # Scenario A profile
├── distributed_lan.json     # Scenario B profile
└── wan_emulated.json        # Scenario C profile

run_network_tax_experiment.py  # Main experiment runner
analyze_network_tax.py          # Results analyzer & table generator

results/network_tax/
├── network_tax_mqtt_latest.json
├── network_tax_coap_latest.json
└── ...
```

## Next Steps

1. **Run experiments** for all protocols
2. **Generate tables** in LaTeX format
3. **Add to Section 7.3** with analysis
4. **Discuss insights**:
   - Why does each protocol behave differently?
   - What does this tell us about real-world deployment?
   - How does STGen enable this analysis?

## Citation Example

> "Table X demonstrates the Network Tax—the performance degradation due to network conditions—across three deployment scenarios. As expected, the localhost baseline (Scenario A) achieves maximum throughput (95k msg/s for MQTT) with minimal latency (0.12ms). Distributed LAN deployment (Scenario B) incurs a moderate tax of 17.9% throughput degradation due to 1ms RTT overhead. WAN emulation (Scenario C) with 150ms latency and 1% packet loss results in a 90% throughput tax, demonstrating STGen's ability to accurately model constrained networks. Notably, CoAP's confirmable messages exhibit increased retransmission overhead under packet loss, while UDP simply drops packets, validating the testbed's protocol-specific behavior modeling."
