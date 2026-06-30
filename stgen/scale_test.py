# stgen/scale_test.py
"""
Automated scalability testing - runs protocol with increasing load.
"""

def run_scale_test(protocol: str, client_counts: List[int], scenario: str):
    """Test protocol with increasing client counts."""
    results = {}
    
    for num_clients in client_counts:
        _LOG.info(f"Testing with {num_clients} clients...")
        cfg = load_scenario(scenario)
        cfg["protocol"] = protocol
        cfg["num_clients"] = num_clients
        
        # Run test
        result = run_test(cfg)
        results[num_clients] = result
        
    # Generate scaling graph
    plot_scaling_results(results)