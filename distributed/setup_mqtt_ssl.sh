#!/bin/bash
# Setup MQTT with SSL/TLS for secure public network communication

echo "🔐 MQTT SSL/TLS Setup"
echo "====================="

# Create certificate directory
CERT_DIR=~/mqtt-certs
mkdir -p $CERT_DIR
cd $CERT_DIR

echo "Generating self-signed certificates..."

# Generate CA (Certificate Authority)
openssl req -new -x509 -days 3650 -extensions v3_ca \
    -keyout ca.key -out ca.crt \
    -subj "/C=US/ST=State/L=City/O=STGen/CN=STGen-CA"

# Generate server key and certificate
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
    -subj "/C=US/ST=State/L=City/O=STGen/CN=YOUR_PUBLIC_IP_OR_DOMAIN"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out server.crt -days 3650

# Set permissions
chmod 644 server.crt ca.crt
chmod 600 server.key ca.key

echo ""
echo "✅ Certificates generated in: $CERT_DIR"
echo ""

# Create Mosquitto config with SSL
cat > mosquitto_ssl.conf << EOF
# Mosquitto SSL Configuration
listener 8883
protocol mqtt

# SSL/TLS settings
cafile $CERT_DIR/ca.crt
certfile $CERT_DIR/server.crt
keyfile $CERT_DIR/server.key

# Require certificate from clients (set to false for easier testing)
require_certificate false

# Allow anonymous (for testing - disable in production)
allow_anonymous true

# Logging
log_type all
log_dest file /var/log/mosquitto/mosquitto.log

# Persistence
persistence true
persistence_location /var/lib/mosquitto/
EOF

echo "📝 Mosquitto SSL config created: mosquitto_ssl.conf"
echo ""
echo "Next Steps:"
echo "==========="
echo ""
echo "1. Install Mosquitto broker (if not installed):"
echo "   sudo apt install -y mosquitto mosquitto-clients"
echo ""
echo "2. Stop default Mosquitto:"
echo "   sudo systemctl stop mosquitto"
echo ""
echo "3. Start Mosquitto with SSL config:"
echo "   mosquitto -c $CERT_DIR/mosquitto_ssl.conf"
echo ""
echo "4. Open firewall for SSL MQTT:"
echo "   sudo ufw allow 8883/tcp"
echo ""
echo "5. Test connection:"
echo "   mosquitto_sub -h localhost -p 8883 --cafile $CERT_DIR/ca.crt -t test"
echo ""
echo "6. Update STGen config to use port 8883"
echo ""
echo "⚠️  For production: Replace YOUR_PUBLIC_IP_OR_DOMAIN in server certificate"
echo "   and set allow_anonymous to false, require_certificate to true"
