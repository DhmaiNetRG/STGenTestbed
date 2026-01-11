#!/bin/bash
# Measure network characteristics between sensor node and core

CORE_IP="${1:-8.8.8.8}"
DURATION="${2:-60}"

echo "🌐 Network Tax Measurement"
echo "=========================="
echo "Target: $CORE_IP"
echo "Duration: ${DURATION}s"
echo ""

# Check if tools are installed
command -v ping >/dev/null 2>&1 || { echo "ping not found"; exit 1; }
command -v mtr >/dev/null 2>&1 || echo "⚠️  mtr not installed (optional): sudo apt install mtr"

echo "1. Testing Latency (RTT)..."
echo "----------------------------"
ping -c 10 $CORE_IP | tail -n 2

echo ""
echo "2. Testing Bandwidth (using iperf3 if available)..."
echo "----------------------------------------------------"
if command -v iperf3 &> /dev/null; then
    echo "Run on CORE machine first: iperf3 -s"
    read -p "Is iperf3 server running on core? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Upload bandwidth test (sensor → core):"
        iperf3 -c $CORE_IP -t 10
        echo ""
        echo "Download bandwidth test (core → sensor):"
        iperf3 -c $CORE_IP -t 10 -R
    fi
else
    echo "⚠️  iperf3 not installed. Install: sudo apt install iperf3"
fi

echo ""
echo "3. Testing Packet Loss..."
echo "-------------------------"
ping -c 100 -i 0.2 $CORE_IP | grep "packet loss"

echo ""
echo "4. Continuous Monitoring (mtr)..."
echo "----------------------------------"
if command -v mtr &> /dev/null; then
    echo "Running mtr for $DURATION seconds..."
    mtr -r -c 50 $CORE_IP
else
    echo "⚠️  mtr not installed (recommended): sudo apt install mtr"
fi

echo ""
echo "5. Traceroute (network path)..."
echo "--------------------------------"
traceroute -m 20 $CORE_IP || echo "traceroute not available"

echo ""
echo "📈 Summary & Recommendations:"
echo "============================="
echo ""
echo "Typical network characteristics:"
echo ""
echo "Local Network (LAN):"
echo "  - Latency: 1-5 ms"
echo "  - Jitter: < 1 ms"
echo "  - Packet loss: < 0.1%"
echo "  - Bandwidth: 100-1000 Mbps"
echo ""
echo "Public Internet (same region):"
echo "  - Latency: 10-50 ms"
echo "  - Jitter: 2-10 ms"
echo "  - Packet loss: 0.1-1%"
echo "  - Bandwidth: 10-100 Mbps"
echo ""
echo "Public Internet (different regions):"
echo "  - Latency: 50-200 ms"
echo "  - Jitter: 5-30 ms"
echo "  - Packet loss: 0.5-2%"
echo "  - Bandwidth: 5-50 Mbps"
echo ""
echo "⚠️  If latency > 100ms or packet loss > 1%, consider:"
echo "   - Using a VPN with better routing"
echo "   - Reducing message frequency"
echo "   - Implementing retry logic"
echo "   - Using QoS settings in MQTT"
