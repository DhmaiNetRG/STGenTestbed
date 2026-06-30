#!/usr/bin/env python3
"""
MQTT Protocol Plugin Test Suite
Validates MQTT implementation with various scenarios.
"""

import sys
import time
import json
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

_LOG = logging.getLogger("mqtt_test")


def test_import():
    """Test 1: Verify MQTT module can be imported."""
    _LOG.info("Test 1: Import test")
    try:
        from protocols.mqtt import Protocol
        _LOG.info(" MQTT Protocol imported successfully")
        return True
    except Exception as e:
        _LOG.error(" Import failed: %s", e)
        return False


def test_basic_config():
    """Test 2: Verify basic configuration."""
    _LOG.info("Test 2: Basic configuration")
    try:
        from protocols.mqtt import Protocol
        
        cfg = {
            "protocol": "mqtt",
            "mode": "active",
            "server_ip": "127.0.0.1",
            "server_port": 1883,
            "num_clients": 2,
            "duration": 5,
            "topic": "test/stgen",
            "qos": 1
        }
        
        protocol = Protocol(cfg)
        assert protocol.broker_host == "127.0.0.1"
        assert protocol.broker_port == 1883
        assert protocol.qos == 1
        
        _LOG.info(" Configuration validated")
        return True
    except Exception as e:
        _LOG.error(" Configuration test failed: %s", e)
        return False


def test_connection():
    """Test 3: Test broker connection."""
    _LOG.info("Test 3: Broker connection")
    try:
        from protocols.mqtt import Protocol
        
        cfg = {
            "protocol": "mqtt",
            "mode": "active",
            "server_ip": "127.0.0.1",
            "server_port": 1883,
            "num_clients": 1,
            "topic": "test/stgen/connection",
            "qos": 0
        }
        
        protocol = Protocol(cfg)
        protocol.start_server()
        time.sleep(1)
        
        if protocol._server_client and protocol._server_client.is_connected():
            _LOG.info(" Server connection successful")
            protocol.stop()
            return True
        else:
            _LOG.error(" Server not connected")
            protocol.stop()
            return False
            
    except Exception as e:
        _LOG.error(" Connection test failed: %s", e)
        return False


def test_publish_subscribe():
    """Test 4: Test publish/subscribe functionality."""
    _LOG.info("Test 4: Publish/Subscribe")
    try:
        from protocols.mqtt import Protocol
        
        cfg = {
            "protocol": "mqtt",
            "mode": "active",
            "server_ip": "127.0.0.1",
            "server_port": 1883,
            "num_clients": 1,
            "topic": "test/stgen/pubsub",
            "qos": 1
        }
        
        protocol = Protocol(cfg)
        protocol.start_server()
        time.sleep(1)
        protocol.start_clients(1)
        time.sleep(1)
        
        # Send test message
        test_data = {
            "dev_id": "test_sensor",
            "ts": time.time(),
            "seq_no": 1,
            "sensor_data": "TEST_VALUE"
        }
        
        success, timestamp = protocol.send_data("client_0", test_data)
        time.sleep(1)
        
        if success and protocol._recv_count > 0:
            _LOG.info(" Publish/Subscribe successful (sent: 1, received: %d)", 
                     protocol._recv_count)
            protocol.stop()
            return True
        else:
            _LOG.error(" Publish/Subscribe failed (received: %d)", protocol._recv_count)
            protocol.stop()
            return False
            
    except Exception as e:
        _LOG.error(" Publish/Subscribe test failed: %s", e)
        return False


def test_qos_levels():
    """Test 5: Test different QoS levels."""
    _LOG.info("Test 5: QoS Levels")
    results = {}
    
    for qos in [0, 1, 2]:
        try:
            from protocols.mqtt import Protocol
            
            cfg = {
                "protocol": "mqtt",
                "mode": "active",
                "server_ip": "127.0.0.1",
                "server_port": 1883,
                "num_clients": 1,
                "topic": f"test/stgen/qos{qos}",
                "qos": qos
            }
            
            protocol = Protocol(cfg)
            protocol.start_server()
            time.sleep(0.5)
            protocol.start_clients(1)
            time.sleep(0.5)
            
            # Send 5 messages
            sent = 0
            for i in range(5):
                test_data = {
                    "dev_id": "test_sensor",
                    "ts": time.time(),
                    "seq_no": i,
                    "sensor_data": f"QoS{qos}_MSG_{i}"
                }
                success, _ = protocol.send_data("client_0", test_data)
                if success:
                    sent += 1
                time.sleep(0.1)
            
            time.sleep(1)
            received = protocol._recv_count
            results[qos] = (sent, received)
            
            _LOG.info("QoS %d: Sent=%d, Received=%d", qos, sent, received)
            protocol.stop()
            time.sleep(0.5)
            
        except Exception as e:
            _LOG.error(" QoS %d test failed: %s", qos, e)
            results[qos] = (0, 0)
    
    # Check results
    success = all(r[1] > 0 for r in results.values())
    if success:
        _LOG.info(" All QoS levels working")
        return True
    else:
        _LOG.error(" Some QoS levels failed")
        return False


def test_multiple_clients():
    """Test 6: Test multiple concurrent clients."""
    _LOG.info("Test 6: Multiple Clients")
    try:
        from protocols.mqtt import Protocol
        
        cfg = {
            "protocol": "mqtt",
            "mode": "active",
            "server_ip": "127.0.0.1",
            "server_port": 1883,
            "num_clients": 4,
            "topic": "test/stgen/multi",
            "qos": 1
        }
        
        protocol = Protocol(cfg)
        protocol.start_server()
        time.sleep(1)
        protocol.start_clients(4)
        time.sleep(1)
        
        # Send from multiple clients
        sent = 0
        for i in range(4):
            for j in range(3):
                test_data = {
                    "dev_id": f"sensor_{i}",
                    "ts": time.time(),
                    "seq_no": j,
                    "sensor_data": f"CLIENT_{i}_MSG_{j}"
                }
                success, _ = protocol.send_data(f"client_{i}", test_data)
                if success:
                    sent += 1
                time.sleep(0.1)
        
        time.sleep(2)
        received = protocol._recv_count
        
        _LOG.info("Sent: %d, Received: %d", sent, received)
        
        if received >= sent * 0.9:  # Allow 10% tolerance
            _LOG.info(" Multiple clients working (%.1f%% delivery)", 
                     (received/sent)*100)
            protocol.stop()
            return True
        else:
            _LOG.error(" Too many messages lost (%.1f%% delivery)", 
                      (received/sent)*100)
            protocol.stop()
            return False
            
    except Exception as e:
        _LOG.error(" Multiple clients test failed: %s", e)
        return False


def test_latency_measurement():
    """Test 7: Verify latency measurement."""
    _LOG.info("Test 7: Latency Measurement")
    try:
        from protocols.mqtt import Protocol
        
        cfg = {
            "protocol": "mqtt",
            "mode": "active",
            "server_ip": "127.0.0.1",
            "server_port": 1883,
            "num_clients": 1,
            "topic": "test/stgen/latency",
            "qos": 1
        }
        
        protocol = Protocol(cfg)
        protocol.start_server()
        time.sleep(1)
        protocol.start_clients(1)
        time.sleep(1)
        
        # Send messages and collect latencies
        for i in range(10):
            test_data = {
                "dev_id": "test_sensor",
                "ts": time.time(),
                "seq_no": i,
                "sensor_data": f"LATENCY_TEST_{i}"
            }
            protocol.send_data("client_0", test_data)
            time.sleep(0.2)
        
        time.sleep(1)
        
        if len(protocol._lat) > 0:
            avg_lat = sum(protocol._lat) / len(protocol._lat)
            _LOG.info(" Latency measurement working (avg: %.2f ms, samples: %d)", 
                     avg_lat, len(protocol._lat))
            protocol.stop()
            return True
        else:
            _LOG.error(" No latency measurements collected")
            protocol.stop()
            return False
            
    except Exception as e:
        _LOG.error(" Latency test failed: %s", e)
        return False


def test_error_handling():
    """Test 8: Test error handling with invalid broker."""
    _LOG.info("Test 8: Error Handling")
    try:
        from protocols.mqtt import Protocol
        
        cfg = {
            "protocol": "mqtt",
            "mode": "active",
            "server_ip": "127.0.0.1",
            "server_port": 18830,  # Invalid port
            "num_clients": 1,
            "topic": "test/stgen/error",
            "qos": 1
        }
        
        protocol = Protocol(cfg)
        
        try:
            protocol.start_server()
            time.sleep(2)
            
            # Should fail gracefully
            if not protocol._server_client or not protocol._server_client.is_connected():
                _LOG.info(" Error handling working (failed gracefully)")
                protocol.stop()
                return True
            else:
                _LOG.error(" Connected to invalid broker?")
                protocol.stop()
                return False
                
        except Exception:
            _LOG.info(" Error handling working (exception caught)")
            return True
            
    except Exception as e:
        _LOG.error(" Error handling test failed: %s", e)
        return False


def run_all_tests():
    """Run all test cases."""
    print("\n" + "="*70)
    print("  MQTT Protocol Plugin Test Suite")
    print("="*70 + "\n")
    
    tests = [
        ("Import Test", test_import),
        ("Configuration Test", test_basic_config),
        ("Connection Test", test_connection),
        ("Publish/Subscribe Test", test_publish_subscribe),
        ("QoS Levels Test", test_qos_levels),
        ("Multiple Clients Test", test_multiple_clients),
        ("Latency Measurement Test", test_latency_measurement),
        ("Error Handling Test", test_error_handling),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{'─'*70}")
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            _LOG.exception("Test crashed: %s", e)
            results.append((name, False))
        time.sleep(1)  # Pause between tests
    
    # Summary
    print(f"\n{'='*70}")
    print("  TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = " PASS" if result else " FAIL"
        print(f"  {status}  {name}")
    
    print("─"*70)
    print(f"  Results: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    print("="*70 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)