#!/bin/bash
# Deploy complete 3-tier STGen system

set -e

echo "🏗️  STGen 3-Tier Architecture Deployment"
echo "=========================================="
echo ""

# Check role
echo "Select your role:"
echo "  1) Core Server (Tier 2 - central broker)"
echo "  2) Sensor Node (Tier 1 - data publisher)"
echo "  3) Query Client (Tier 3 - data consumer)"
echo ""
read -p "Enter choice [1-3]: " ROLE

case $ROLE in
    1)
        echo ""
        echo "🎯 CORE SERVER DEPLOYMENT"
        echo "========================="
        echo ""
        
        # Get public IP
        PUBLIC_IP=$(curl -s ifconfig.me || echo "Unable to detect")
        LOCAL_IP=$(hostname -I | awk '{print $1}')
        
        echo "Network Information:"
        echo "  Local IP:  $LOCAL_IP"
        echo "  Public IP: $PUBLIC_IP"
        echo ""
        
        # Configure firewall
        if command -v ufw &> /dev/null; then
            read -p "Configure firewall (UFW)? [Y/n]: " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                echo "Opening ports..."
                sudo ufw allow 1883/tcp comment "MQTT"
                sudo ufw allow 5000/tcp comment "STGen"
                sudo ufw status
            fi
        fi
        
        echo ""
        read -p "Protocol (mqtt/coap/srtp) [mqtt]: " PROTOCOL
        PROTOCOL=${PROTOCOL:-mqtt}
        
        read -p "Duration in seconds [3600]: " DURATION
        DURATION=${DURATION:-3600}
        
        echo ""
        echo "📋 Configuration:"
        echo "  Bind IP: 0.0.0.0 (all interfaces)"
        echo "  Protocol: $PROTOCOL"
        echo "  Duration: $DURATION seconds"
        echo "  MQTT Port: 1883"
        echo ""
        echo "Share with sensor nodes:"
        echo "  --core-ip $PUBLIC_IP"
        echo ""
        
        read -p "Start core server now? [Y/n]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            echo ""
            echo "🚀 Starting core server..."
            echo ""
            python distributed/core_node.py \
                --bind-ip 0.0.0.0 \
                --protocol $PROTOCOL \
                --duration $DURATION
        else
            echo ""
            echo "Manual start command:"
            echo "  python distributed/core_node.py --bind-ip 0.0.0.0 --protocol $PROTOCOL --duration $DURATION"
        fi
        ;;
        
    2)
        echo ""
        echo "📡 SENSOR NODE DEPLOYMENT"
        echo "========================="
        echo ""
        
        read -p "Core server IP address: " CORE_IP
        read -p "Core server port [1883]: " CORE_PORT
        CORE_PORT=${CORE_PORT:-1883}
        
        read -p "Node ID (unique identifier): " NODE_ID
        read -p "Number of sensors [1000]: " NUM_SENSORS
        NUM_SENSORS=${NUM_SENSORS:-1000}
        
        read -p "Sensor types (comma-separated) [temp,humidity,motion]: " SENSOR_TYPES
        SENSOR_TYPES=${SENSOR_TYPES:-"temp,humidity,motion"}
        
        read -p "Protocol [mqtt]: " PROTOCOL
        PROTOCOL=${PROTOCOL:-mqtt}
        
        read -p "Duration [600]: " DURATION
        DURATION=${DURATION:-600}
        
        echo ""
        echo "Testing connection to core..."
        if ping -c 2 $CORE_IP &> /dev/null; then
            echo "✓ Core is reachable"
        else
            echo "⚠️  Warning: Cannot ping core (may be blocked)"
        fi
        
        if timeout 3 bash -c "cat < /dev/null > /dev/tcp/$CORE_IP/$CORE_PORT" 2>/dev/null; then
            echo "✓ Port $CORE_PORT is open"
        else
            echo "❌ Port $CORE_PORT not accessible"
        fi
        
        echo ""
        echo "📋 Configuration:"
        echo "  Core: $CORE_IP:$CORE_PORT"
        echo "  Node ID: $NODE_ID"
        echo "  Sensors: $NUM_SENSORS"
        echo "  Types: $SENSOR_TYPES"
        echo "  Protocol: $PROTOCOL"
        echo ""
        
        read -p "Start sensor node now? [Y/n]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            echo ""
            echo "🚀 Starting sensor node..."
            echo ""
            python distributed/sensor_node.py \
                --core-ip $CORE_IP \
                --core-port $CORE_PORT \
                --node-id $NODE_ID \
                --sensors $NUM_SENSORS \
                --sensor-types $SENSOR_TYPES \
                --protocol $PROTOCOL \
                --duration $DURATION
        else
            # Create start script
            SCRIPT_NAME="start_sensor_${NODE_ID}.sh"
            cat > $SCRIPT_NAME << EOF
#!/bin/bash
python distributed/sensor_node.py \\
    --core-ip $CORE_IP \\
    --core-port $CORE_PORT \\
    --node-id $NODE_ID \\
    --sensors $NUM_SENSORS \\
    --sensor-types $SENSOR_TYPES \\
    --protocol $PROTOCOL \\
    --duration $DURATION
EOF
            chmod +x $SCRIPT_NAME
            echo ""
            echo "✓ Created start script: $SCRIPT_NAME"
            echo "  Run: ./$SCRIPT_NAME"
        fi
        ;;
        
    3)
        echo ""
        echo "🔍 QUERY CLIENT DEPLOYMENT"
        echo "=========================="
        echo ""
        
        read -p "Core server IP address: " CORE_IP
        read -p "Core server port [1883]: " CORE_PORT
        CORE_PORT=${CORE_PORT:-1883}
        
        read -p "Protocol [mqtt]: " PROTOCOL
        PROTOCOL=${PROTOCOL:-mqtt}
        
        echo ""
        echo "Query Filter Options:"
        echo "  1) All data (no filter)"
        echo "  2) Specific sensor type"
        echo "  3) Specific node ID"
        echo "  4) Temperature above threshold"
        echo "  5) Custom JSON filter"
        echo ""
        read -p "Choose filter [1-5]: " FILTER_CHOICE
        
        case $FILTER_CHOICE in
            1)
                QUERY_FILTER='{}'
                ;;
            2)
                read -p "Sensor type (temp/humidity/motion/etc): " SENSOR_TYPE
                QUERY_FILTER="{\"sensor_type\": \"$SENSOR_TYPE\"}"
                ;;
            3)
                read -p "Node ID: " TARGET_NODE
                QUERY_FILTER="{\"node_id\": \"$TARGET_NODE\"}"
                ;;
            4)
                read -p "Minimum temperature: " MIN_TEMP
                QUERY_FILTER="{\"sensor_type\": \"temp\", \"min_value\": $MIN_TEMP}"
                ;;
            5)
                read -p "Enter JSON filter: " CUSTOM_FILTER
                QUERY_FILTER="$CUSTOM_FILTER"
                ;;
            *)
                QUERY_FILTER='{}'
                ;;
        esac
        
        echo ""
        read -p "Query mode - (c)ontinuous or (o)nce [c]: " QUERY_MODE
        QUERY_MODE=${QUERY_MODE:-c}
        
        if [[ $QUERY_MODE == "c" ]]; then
            read -p "Query interval (seconds) [5]: " INTERVAL
            INTERVAL=${INTERVAL:-5}
            
            read -p "Total duration (seconds) [300]: " DURATION
            DURATION=${DURATION:-300}
            
            ONCE_FLAG=""
        else
            INTERVAL=0
            DURATION=0
            ONCE_FLAG="--once"
        fi
        
        read -p "Output file [results/query_results.json]: " OUTPUT
        OUTPUT=${OUTPUT:-"results/query_results.json"}
        
        echo ""
        echo "Testing connection to core..."
        if timeout 3 bash -c "cat < /dev/null > /dev/tcp/$CORE_IP/$CORE_PORT" 2>/dev/null; then
            echo "✓ Port $CORE_PORT is accessible"
        else
            echo "❌ Port $CORE_PORT not accessible"
            echo "   Check: firewall, network, VPN"
        fi
        
        echo ""
        echo "📋 Configuration:"
        echo "  Server: $CORE_IP:$CORE_PORT"
        echo "  Protocol: $PROTOCOL"
        echo "  Filter: $QUERY_FILTER"
        echo "  Mode: $([ \"$QUERY_MODE\" == \"c\" ] && echo \"Continuous (${INTERVAL}s interval)\" || echo \"One-time\")"
        [ "$QUERY_MODE" == "c" ] && echo "  Duration: $DURATION seconds"
        echo "  Output: $OUTPUT"
        echo ""
        
        read -p "Start query client now? [Y/n]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            echo ""
            echo "🚀 Starting query client..."
            echo ""
            
            if [[ $QUERY_MODE == "c" ]]; then
                python distributed/query_client.py \
                    --server-ip $CORE_IP \
                    --server-port $CORE_PORT \
                    --protocol $PROTOCOL \
                    --query-filter "$QUERY_FILTER" \
                    --query-interval $INTERVAL \
                    --duration $DURATION \
                    --output "$OUTPUT"
            else
                python distributed/query_client.py \
                    --server-ip $CORE_IP \
                    --server-port $CORE_PORT \
                    --protocol $PROTOCOL \
                    --query-filter "$QUERY_FILTER" \
                    --once \
                    --output "$OUTPUT"
            fi
        else
            # Create start script
            SCRIPT_NAME="start_query_client.sh"
            cat > $SCRIPT_NAME << EOF
#!/bin/bash
python distributed/query_client.py \\
    --server-ip $CORE_IP \\
    --server-port $CORE_PORT \\
    --protocol $PROTOCOL \\
    --query-filter '$QUERY_FILTER' \\
$([ "$QUERY_MODE" == "c" ] && echo "    --query-interval $INTERVAL \\" || echo "    --once \\")
$([ "$QUERY_MODE" == "c" ] && echo "    --duration $DURATION \\")
    --output "$OUTPUT"
EOF
            chmod +x $SCRIPT_NAME
            echo ""
            echo "✓ Created start script: $SCRIPT_NAME"
            echo "  Run: ./$SCRIPT_NAME"
        fi
        ;;
        
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📖 See THREE_TIER_ARCHITECTURE.md for complete documentation"
