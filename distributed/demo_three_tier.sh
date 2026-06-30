#!/bin/bash
# Demo script showing 3-tier architecture in action
# Simulates local deployment for testing

echo "🎬 STGen 3-Tier Architecture Demo"
echo "==================================="
echo ""
echo "This demo will start:"
echo "  1. Core Server (localhost)"
echo "  2. Two Sensor Nodes (simulated remote)"
echo "  3. Query Client (requesting data)"
echo ""
read -p "Press Enter to start demo..."

# Create log directory
mkdir -p logs/demo

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping all components..."
    pkill -f "core_node.py"
    pkill -f "sensor_node.py"
    pkill -f "query_client.py"
    echo "✅ Demo stopped"
}
trap cleanup EXIT INT

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TIER 2: Starting Core Server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start core server in background
python distributed/core_node.py \
    --bind-ip 127.0.0.1 \
    --protocol mqtt \
    --duration 300 \
    > logs/demo/core.log 2>&1 &

CORE_PID=$!
echo "✓ Core server started (PID: $CORE_PID)"
echo "  Logs: logs/demo/core.log"

# Wait for core to start
echo "  Waiting for core to initialize..."
sleep 5

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TIER 1: Starting Sensor Nodes"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start sensor node A
python distributed/sensor_node.py \
    --core-ip 127.0.0.1 \
    --core-port 1883 \
    --node-id Office_A \
    --sensors 50 \
    --sensor-types "temp,humidity,motion" \
    --protocol mqtt \
    --duration 300 \
    > logs/demo/sensor_a.log 2>&1 &

SENSOR_A_PID=$!
echo "✓ Sensor Node A started (PID: $SENSOR_A_PID)"
echo "  Location: Office_A"
echo "  Sensors: 50 (temp, humidity, motion)"
echo "  Logs: logs/demo/sensor_a.log"

sleep 2

# Start sensor node B
python distributed/sensor_node.py \
    --core-ip 127.0.0.1 \
    --core-port 1883 \
    --node-id Warehouse_B \
    --sensors 30 \
    --sensor-types "temp,door,light" \
    --protocol mqtt \
    --duration 300 \
    > logs/demo/sensor_b.log 2>&1 &

SENSOR_B_PID=$!
echo ""
echo "✓ Sensor Node B started (PID: $SENSOR_B_PID)"
echo "  Location: Warehouse_B"
echo "  Sensors: 30 (temp, door, light)"
echo "  Logs: logs/demo/sensor_b.log"

# Wait for sensors to connect and send data
echo ""
echo "⏳ Waiting for sensors to connect and generate data..."
sleep 10

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TIER 3: Starting Query Clients"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📊 Query Example 1: All Temperature Sensors"
echo "--------------------------------------------"
python distributed/query_client.py \
    --server-ip 127.0.0.1 \
    --server-port 1883 \
    --protocol mqtt \
    --query-filter '{"sensor_type": "temp"}' \
    --query-interval 3 \
    --duration 15 \
    --output results/demo_temp.json

echo ""
echo "📊 Query Example 2: Specific Node (Office_A)"
echo "--------------------------------------------"
python distributed/query_client.py \
    --server-ip 127.0.0.1 \
    --server-port 1883 \
    --protocol mqtt \
    --query-filter '{"node_id": "Office_A"}' \
    --query-interval 3 \
    --duration 15 \
    --output results/demo_office.json

echo ""
echo "📊 Query Example 3: One-Time Query (All Data)"
echo "----------------------------------------------"
python distributed/query_client.py \
    --server-ip 127.0.0.1 \
    --server-port 1883 \
    --protocol mqtt \
    --query-filter '{}' \
    --once \
    --output results/demo_all.json

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Demo Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 Results saved to:"
echo "  - results/demo_temp.json (temperature data)"
echo "  - results/demo_office.json (Office_A data)"
echo "  - results/demo_all.json (all data snapshot)"
echo ""
echo "📝 Logs available in:"
echo "  - logs/demo/core.log"
echo "  - logs/demo/sensor_a.log"
echo "  - logs/demo/sensor_b.log"
echo ""
echo "🔍 View results:"
echo "  cat results/demo_temp.json | jq ."
echo "  cat results/demo_office.json | jq '.[] | {node: .node_id, device: .dev_id}'"
echo ""
echo "Components will continue running..."
echo "Press Ctrl+C to stop all"
echo ""

# Keep running until interrupted
wait
