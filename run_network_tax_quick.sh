#!/bin/bash
# Quick start script for network tax experiment

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  STGen Network Tax Experiment (Section 7.3)"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check for sudo
if ! sudo -n true 2>/dev/null; then
    echo "⚠️  This experiment requires sudo access for network emulation"
    echo "   Please enter your password when prompted"
    sudo -v
fi

# Clean existing network rules
echo "🧹 Cleaning existing network emulation rules..."
sudo tc qdisc del dev eth0 root 2>/dev/null || true

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
echo "📊 Running network tax experiment:"
echo "   Protocol: $PROTOCOL"
echo "   Duration: ${DURATION}s per scenario"
echo "   Total time: ~$(($DURATION * 3 + 60))s (including cooldown)"
echo ""

# Run experiment
echo "🚀 Starting experiment..."
python run_network_tax_experiment.py \
    --protocol "$PROTOCOL" \
    --duration "$DURATION" \
    --num-sensors 500

# Analyze results
echo ""
echo "📈 Analyzing results..."
python analyze_network_tax.py --protocol "$PROTOCOL"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ Experiment complete!"
echo ""
echo "Results saved in: results/network_tax/"
echo ""
echo "To generate LaTeX table for paper:"
echo "  python analyze_network_tax.py --protocol $PROTOCOL --format latex"
echo ""
echo "To test all protocols:"
echo "  python run_network_tax_experiment.py --all-protocols"
echo "════════════════════════════════════════════════════════════════"
