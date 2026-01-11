#!/usr/bin/env python3
"""
STGen Bandwidth Calculator for Distributed Deployments
Calculates required bandwidth for sensor network over public internet
"""

def calculate_bandwidth(
    num_sensors: int,
    messages_per_sec: float,
    message_size_bytes: int,
    protocol: str = "mqtt",
    overhead_factor: float = 1.3
) -> dict:
    """
    Calculate bandwidth requirements.
    
    Args:
        num_sensors: Total number of sensors across all nodes
        messages_per_sec: Messages per second per sensor
        message_size_bytes: Average message payload size
        protocol: Protocol name (mqtt, coap, srtp)
        overhead_factor: Protocol overhead multiplier (1.3 = 30% overhead)
    
    Returns:
        Dictionary with bandwidth calculations
    """
    
    # Protocol overhead estimates
    protocol_overhead = {
        "mqtt": 10,      # bytes (topic + headers)
        "coap": 4,       # bytes (CoAP header)
        "srtp": 20,      # bytes (RTP + SRTP)
        "custom_udp": 8  # bytes (UDP header)
    }
    
    overhead_bytes = protocol_overhead.get(protocol.lower(), 10)
    total_message_size = message_size_bytes + overhead_bytes
    
    # Calculate rates
    messages_per_sec_total = num_sensors * messages_per_sec
    bytes_per_sec = messages_per_sec_total * total_message_size
    
    # Apply overhead factor for TCP/IP, retransmissions, etc.
    bytes_per_sec_with_overhead = bytes_per_sec * overhead_factor
    
    # Convert to common units
    kbps = (bytes_per_sec_with_overhead * 8) / 1000
    mbps = kbps / 1000
    
    # Monthly data transfer
    bytes_per_month = bytes_per_sec_with_overhead * 60 * 60 * 24 * 30
    gb_per_month = bytes_per_month / (1024 ** 3)
    
    return {
        "num_sensors": num_sensors,
        "messages_per_sec_total": round(messages_per_sec_total, 2),
        "message_size_bytes": total_message_size,
        "bandwidth_kbps": round(kbps, 2),
        "bandwidth_mbps": round(mbps, 3),
        "data_transfer_gb_month": round(gb_per_month, 2),
        "recommended_connection": get_connection_recommendation(mbps)
    }

def get_connection_recommendation(mbps: float) -> str:
    """Get connection type recommendation based on bandwidth."""
    if mbps < 1:
        return "Basic DSL/Cable (5+ Mbps)"
    elif mbps < 10:
        return "Standard Broadband (10+ Mbps)"
    elif mbps < 50:
        return "High-Speed Broadband (50+ Mbps)"
    elif mbps < 100:
        return "Very High-Speed Broadband (100+ Mbps)"
    else:
        return "Enterprise/Fiber Connection (100+ Mbps)"

def print_scenario(name: str, **kwargs):
    """Print a bandwidth scenario."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print('='*60)
    result = calculate_bandwidth(**kwargs)
    
    print(f"Sensors: {result['num_sensors']:,}")
    print(f"Total Messages/sec: {result['messages_per_sec_total']:,}")
    print(f"Message Size: {result['message_size_bytes']} bytes")
    print(f"\n📊 Bandwidth Requirements:")
    print(f"   Upload: {result['bandwidth_kbps']:,.2f} Kbps ({result['bandwidth_mbps']:.3f} Mbps)")
    print(f"   Monthly Data: {result['data_transfer_gb_month']:.2f} GB")
    print(f"\n💡 Recommended: {result['recommended_connection']}")

if __name__ == "__main__":
    print("🌐 STGen Distributed Network - Bandwidth Calculator")
    print("=" * 60)
    
    # Scenario 1: Small deployment
    print_scenario(
        "Scenario 1: Small Deployment",
        num_sensors=1000,
        messages_per_sec=0.1,  # 1 message every 10 seconds
        message_size_bytes=50,
        protocol="mqtt"
    )
    
    # Scenario 2: Medium deployment
    print_scenario(
        "Scenario 2: Medium Deployment",
        num_sensors=5000,
        messages_per_sec=0.2,  # 1 message every 5 seconds
        message_size_bytes=100,
        protocol="mqtt"
    )
    
    # Scenario 3: Large deployment
    print_scenario(
        "Scenario 3: Large Deployment (10K sensors)",
        num_sensors=10000,
        messages_per_sec=0.5,  # 2 messages per second
        message_size_bytes=150,
        protocol="mqtt"
    )
    
    # Scenario 4: High-frequency deployment
    print_scenario(
        "Scenario 4: High-Frequency (Healthcare Wearables)",
        num_sensors=1000,
        messages_per_sec=5.0,  # 5 messages per second (vital signs)
        message_size_bytes=80,
        protocol="mqtt"
    )
    
    # Scenario 5: Your previous distributed test
    print_scenario(
        "Scenario 5: Your Windows + Desktop Setup",
        num_sensors=6000,  # 3 nodes × 2000 sensors
        messages_per_sec=0.5,
        message_size_bytes=100,
        protocol="mqtt"
    )
    
    print("\n" + "="*60)
    print("📝 Notes:")
    print("="*60)
    print("• Bandwidth is UPLOAD from core (downlink to sensors minimal)")
    print("• Add 20-30% buffer for peaks and protocol overhead")
    print("• Test with measure_network_tax.sh before deployment")
    print("• Consider QoS settings in MQTT for reliability")
    print("• Public networks have variable latency - monitor jitter")
    print()
    
    # Interactive calculator
    print("="*60)
    print("Custom Calculation")
    print("="*60)
    try:
        sensors = int(input("Number of sensors: "))
        msg_rate = float(input("Messages per second per sensor: "))
        msg_size = int(input("Message size (bytes): "))
        protocol = input("Protocol (mqtt/coap/srtp) [mqtt]: ").strip() or "mqtt"
        
        print_scenario(
            "Your Custom Scenario",
            num_sensors=sensors,
            messages_per_sec=msg_rate,
            message_size_bytes=msg_size,
            protocol=protocol
        )
    except (EOFError, KeyboardInterrupt):
        print("\n\nSkipping custom calculation.")
    except ValueError as e:
        print(f"\nInvalid input: {e}")
