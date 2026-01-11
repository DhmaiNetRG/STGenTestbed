#!/bin/bash
# WireGuard VPN Setup for Secure Distributed STGen
# This creates a secure network between core and sensor nodes

echo "🔒 WireGuard VPN Setup for STGen Distributed Network"
echo "======================================================"

# Check if WireGuard is installed
if ! command -v wg &> /dev/null; then
    echo "Installing WireGuard..."
    sudo apt update
    sudo apt install -y wireguard wireguard-tools
fi

# Generate keys
mkdir -p ~/wireguard-keys
cd ~/wireguard-keys

echo "Generating WireGuard keys..."
wg genkey | tee privatekey | wg pubkey > publickey

echo ""
echo "✅ Keys generated!"
echo "Private Key: $(cat privatekey)"
echo "Public Key: $(cat publickey)"
echo ""
echo "Keep private key secret!"
echo ""

# Server configuration template (Core Machine)
cat > server_config_template.conf << 'EOF'
# /etc/wireguard/wg0.conf (on CORE machine)
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = YOUR_SERVER_PRIVATE_KEY

# Save and restore iptables rules
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# Peer 1 (Sensor Node A)
[Peer]
PublicKey = SENSOR_A_PUBLIC_KEY
AllowedIPs = 10.0.0.2/32

# Peer 2 (Sensor Node B)
[Peer]
PublicKey = SENSOR_B_PUBLIC_KEY
AllowedIPs = 10.0.0.3/32

# Peer 3 (Sensor Node C)
[Peer]
PublicKey = SENSOR_C_PUBLIC_KEY
AllowedIPs = 10.0.0.4/32
EOF

# Client configuration template (Sensor Nodes)
cat > client_config_template.conf << 'EOF'
# /etc/wireguard/wg0.conf (on SENSOR machine)
[Interface]
Address = 10.0.0.2/24
PrivateKey = YOUR_CLIENT_PRIVATE_KEY
DNS = 8.8.8.8

[Peer]
PublicKey = SERVER_PUBLIC_KEY
Endpoint = YOUR_CORE_PUBLIC_IP:51820
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
EOF

echo "📝 Configuration templates created:"
echo "   - server_config_template.conf (for core machine)"
echo "   - client_config_template.conf (for sensor nodes)"
echo ""
echo "Next Steps:"
echo "==========="
echo ""
echo "1. On CORE machine:"
echo "   - Replace YOUR_SERVER_PRIVATE_KEY with your private key"
echo "   - Replace SENSOR_X_PUBLIC_KEY with each sensor's public key"
echo "   - Copy to: sudo cp server_config_template.conf /etc/wireguard/wg0.conf"
echo "   - Start: sudo wg-quick up wg0"
echo "   - Enable on boot: sudo systemctl enable wg-quick@wg0"
echo ""
echo "2. On each SENSOR machine:"
echo "   - Generate keys (run this script)"
echo "   - Replace YOUR_CLIENT_PRIVATE_KEY with sensor's private key"
echo "   - Replace SERVER_PUBLIC_KEY with core's public key"
echo "   - Replace YOUR_CORE_PUBLIC_IP with core's public IP"
echo "   - Copy to: sudo cp client_config_template.conf /etc/wireguard/wg0.conf"
echo "   - Start: sudo wg-quick up wg0"
echo ""
echo "3. Firewall (on CORE):"
echo "   sudo ufw allow 51820/udp"
echo ""
echo "4. Run STGen using VPN IPs:"
echo "   Core: python distributed/core_node.py --bind-ip 10.0.0.1"
echo "   Sensor: python distributed/sensor_node.py --core-ip 10.0.0.1 --node-id A --sensors 1000"
echo ""
echo "5. Verify connection:"
echo "   sudo wg show"
