#!/bin/bash
# Quick start for single-device network tax experiment

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  STGen Network Tax - Single Device Mode"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "✓ Runs on one machine (localhost only)"
echo "✓ No infrastructure needed"
echo "✓ Network emulation via loopback interface"
echo ""

# Check for sudo
if ! sudo -n true 2>/dev/null; then
    echo "⚠️  This experiment requires sudo for network emulation"
    echo "   Please enter your password:"
    sudo -v
fi

# Clean existing network rules on loopback
echo "🧹 Cleaning network emulation on loopback..."
sudo tc qdisc del dev lo root 2>/dev/null || true

# Activate virtual environment
if [ -d "myenv" ]; then
    echo "🐍 Activating Python environment..."
    source myenv/bin/activate
else
    echo "❌ Virtual environment not found. Run setup first:"
    echo "   python3 -m venv myenv"
    echo "   source myenv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Protocol selection
PROTOCOL="${1:-mqtt}"
DURATION="${2:-60}"

echo ""
echo "📊 Single-Device Network Tax Experiment"
echo "   Protocol: $PROTOCOL"
echo "   Duration: ${DURATION}s per scenario"
echo "   Scenarios: 3 (Baseline, LAN emulation, WAN emulation)"
echo "   Total time: ~$(($DURATION * 3 + 40))s"
echo ""
echo "🔬 All traffic on 127.0.0.1 with tc/netem emulation"
echo ""

# Run experiment
echo "🚀 Starting experiment..."
python run_network_tax_single_device.py \
    --protocol "$PROTOCOL" \
    --duration "$DURATION" \
    --num-sensors 500

# Check if results exist
if [ -d "results/network_tax_single_device" ]; then
    echo ""
    echo "📈 Generating summary table..."
    python analyze_network_tax.py \
        --protocol "$PROTOCOL" \
        --results-dir results/network_tax_single_device
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ Experiment complete!"
echo ""
echo "📂 Results: results/network_tax_single_device/"
echo ""
echo "📊 To generate LaTeX table:"
echo "   python analyze_network_tax.py \\"
echo "       --protocol $PROTOCOL \\"
echo "       --results-dir results/network_tax_single_device \\"
echo "       --format latex"
echo ""
echo "🔄 To test all protocols:"
echo "   python run_network_tax_single_device.py --all-protocols"
echo "════════════════════════════════════════════════════════════════"
