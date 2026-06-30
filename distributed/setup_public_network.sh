#!/bin/bash
# Quick setup for distributed STGen over public network

set -e

echo "🌐 STGen Public Network Quick Setup"
echo "===================================="
echo ""

# Detect if this is core or sensor
read -p "Is this the CORE machine? [y/N]: " -n 1 -r
echo
IS_CORE=$REPLY

if [[ $IS_CORE =~ ^[Yy]$ ]]; then
    echo ""
    echo "📍 CORE MACHINE SETUP"
    echo "====================="
    echo ""
    
    # Get public IP
    PUBLIC_IP=$(curl -s ifconfig.me)
    echo "✓ Your public IP: $PUBLIC_IP"
    echo ""
    
    # Check firewall
    if command -v ufw &> /dev/null; then
        echo "Configuring firewall..."
        sudo ufw allow 1883/tcp comment "MQTT"
        sudo ufw allow 5000/tcp comment "STGen"
        sudo ufw allow 5683/udp comment "CoAP"
        echo "✓ Firewall configured"
    else
        echo "⚠️  UFW not found - configure firewall manually"
    fi
    
    echo ""
    echo "Security options:"
    echo "  1) No security (testing only)"
    echo "  2) WireGuard VPN (recommended)"
    echo "  3) MQTT SSL/TLS"
    read -p "Choose [1-3]: " -n 1 -r SEC_CHOICE
    echo ""
    
    case $SEC_CHOICE in
        2)
            echo "Setting up WireGuard..."
            ./setup_wireguard.sh
            ;;
        3)
            echo "Setting up MQTT SSL..."
            ./setup_mqtt_ssl.sh
            ;;
        *)
            echo "⚠️  No security - for testing only!"
            ;;
    esac
    
    echo ""
    echo "✅ Core setup complete!"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Share this info with sensor node operators:"
    echo "      Core IP: $PUBLIC_IP"
    echo "      Port: 1883 (MQTT) or 5000 (STGen)"
    echo ""
    echo "   2. Start core node:"
    echo "      python distributed/core_node.py --bind-ip 0.0.0.0 --protocol mqtt"
    echo ""
    
else
    echo ""
    echo "📡 SENSOR NODE SETUP"
    echo "===================="
    echo ""
    
    read -p "Enter CORE machine public IP: " CORE_IP
    read -p "Enter your node ID (e.g., A, B, C): " NODE_ID
    read -p "Number of sensors [1000]: " NUM_SENSORS
    NUM_SENSORS=${NUM_SENSORS:-1000}
    
    echo ""
    echo "Testing connection to core..."
    
    # Test ping
    if ping -c 3 $CORE_IP &> /dev/null; then
        echo "✓ Core is reachable (ping successful)"
    else
        echo "⚠️  Warning: Core not responding to ping (may be blocked)"
    fi
    
    # Test port
    if timeout 3 bash -c "cat < /dev/null > /dev/tcp/$CORE_IP/1883" 2>/dev/null; then
        echo "✓ MQTT port (1883) is open"
    else
        echo "❌ MQTT port (1883) not accessible"
        echo "   Check: firewall, port forwarding, VPN"
    fi
    
    echo ""
    echo "Measuring network characteristics..."
    if command -v ping &> /dev/null; then
        RTT=$(ping -c 5 $CORE_IP 2>/dev/null | tail -1 | awk -F '/' '{print $5}')
        if [ ! -z "$RTT" ]; then
            echo "✓ Average latency: ${RTT} ms"
        fi
    fi
    
    echo ""
    echo "✅ Sensor setup complete!"
    echo ""
    echo "📋 Start sensor node with:"
    echo "   python distributed/sensor_node.py \\"
    echo "     --core-ip $CORE_IP \\"
    echo "     --node-id $NODE_ID \\"
    echo "     --sensors $NUM_SENSORS \\"
    echo "     --protocol mqtt"
    echo ""
    
    # Create quick-start script
    cat > start_sensor_$NODE_ID.sh << EOF
#!/bin/bash
python distributed/sensor_node.py \\
  --core-ip $CORE_IP \\
  --node-id $NODE_ID \\
  --sensors $NUM_SENSORS \\
  --protocol mqtt \\
  --duration 300
EOF
    chmod +x start_sensor_$NODE_ID.sh
    echo "✓ Created quick-start script: start_sensor_$NODE_ID.sh"
fi

echo ""
echo "📖 See PUBLIC_NETWORK_DEPLOYMENT.md for detailed guide"
