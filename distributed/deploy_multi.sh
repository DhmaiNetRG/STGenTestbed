#!/bin/bash
# Automated multi-device deployment orchestration

CORE_IP="192.168.1.100"  # Change to your core machine IP
PROTOCOL="mqtt"
DURATION=300

echo "STGen Distributed Deployment"
echo "================================"
echo "Core IP: $CORE_IP"
echo "Protocol: $PROTOCOL"
echo ""

# Instructions for manual deployment
cat << EOF
Manual Deployment Steps:
========================

1. On Core Machine ($CORE_IP):
   python distributed/core_node.py --bind-ip 0.0.0.0 --protocol $PROTOCOL

2. On Sensor Machine A:
   python distributed/sensor_node.py --core-ip $CORE_IP --node-id A --sensors 2000

3. On Sensor Machine B:
   python distributed/sensor_node.py --core-ip $CORE_IP --node-id B --sensors 2000

4. On Sensor Machine C:
   python distributed/sensor_node.py --core-ip $CORE_IP --node-id C --sensors 2000

Total: 6000 sensors across 3 machines + 1 core

EOF

# Automated SSH deployment (if SSH is configured)
read -p "Deploy via SSH? (requires passwordless SSH) [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    MACHINE_A="user@192.168.1.101"
    MACHINE_B="user@192.168.1.102"
    MACHINE_C="user@192.168.1.103"
    
    echo "Deploying to remote machines..."
    
    # Deploy to Machine A
    ssh $MACHINE_A "cd ~/stgen && python distributed/sensor_node.py --core-ip $CORE_IP --node-id A --sensors 2000" &
    
    # Deploy to Machine B  
    ssh $MACHINE_B "cd ~/stgen && python distributed/sensor_node.py --core-ip $CORE_IP --node-id B --sensors 2000" &
    
    # Deploy to Machine C
    ssh $MACHINE_C "cd ~/stgen && python distributed/sensor_node.py --core-ip $CORE_IP --node-id C --sensors 2000" &
    
    wait
    echo " Distributed deployment complete"
fi