#!/usr/bin/env python3
"""
Automated distributed experiment to collect evidence for paper Section 8.3.
Runs both single-machine and distributed tests, collecting CPU/RAM/latency metrics.
"""

import argparse
import json
import subprocess
import time
import psutil
import sys
from pathlib import Path
from datetime import datetime
import threading


class ResourceMonitor:
    """Monitor CPU and RAM usage during test."""
    
    def __init__(self, process_filter=None):
        self.monitoring = False
        self.samples = []
        self.process_filter = process_filter
        
    def start(self):
        """Start monitoring in background thread."""
        self.monitoring = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self):
        """Stop monitoring and return statistics."""
        self.monitoring = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2)
        
        if not self.samples:
            return {'cpu_avg': 0, 'cpu_max': 0, 'ram_avg_mb': 0, 'ram_max_mb': 0}
        
        cpu_vals = [s['cpu'] for s in self.samples]
        ram_vals = [s['ram_mb'] for s in self.samples]
        
        return {
            'cpu_avg': sum(cpu_vals) / len(cpu_vals),
            'cpu_max': max(cpu_vals),
            'ram_avg_mb': sum(ram_vals) / len(ram_vals),
            'ram_max_mb': max(ram_vals),
            'sample_count': len(self.samples)
        }
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.monitoring:
            try:
                # System-wide metrics
                cpu_percent = psutil.cpu_percent(interval=0.5)
                ram_mb = psutil.virtual_memory().used / (1024 * 1024)
                
                # Process-specific if filter provided
                if self.process_filter:
                    total_cpu = 0
                    total_ram = 0
                    for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_info']):
                        try:
                            if self.process_filter in proc.info['name']:
                                total_cpu += proc.info['cpu_percent'] or 0
                                total_ram += (proc.info['memory_info'].rss / (1024 * 1024))
                        except:
                            pass
                    
                    if total_cpu > 0:  # Use process-specific if found
                        cpu_percent = total_cpu
                        ram_mb = total_ram
                
                self.samples.append({
                    'cpu': cpu_percent,
                    'ram_mb': ram_mb,
                    'timestamp': time.time()
                })
                
            except Exception as e:
                print(f"Monitor error: {e}")
            
            time.sleep(1)


def run_single_machine_test(protocol, num_sensors, duration):
    """Run test with all components on single machine."""
    print(f"\n{'='*60}")
    print(f"SINGLE MACHINE TEST: {protocol.upper()}")
    print(f"Sensors: {num_sensors}, Duration: {duration}s")
    print(f"{'='*60}\n")
    
    # Create temporary config with specified duration
    config_path = Path(f"configs/{protocol}.json")
    if not config_path.exists():
        print(f"Error: Config not found: {config_path}")
        return None
    
    with open(config_path) as f:
        config = json.load(f)
    
    # Modify duration
    config['duration'] = duration
    
    # Save temporary config
    temp_config = Path(f"configs/temp_{protocol}_single.json")
    with open(temp_config, 'w') as f:
        json.dump(config, f, indent=2)
    
    # Start resource monitoring
    monitor = ResourceMonitor(process_filter='python')
    monitor.start()
    
    # Run the test using config file
    cmd = [sys.executable, '-m', 'stgen.main', str(temp_config)]
    
    print(f"Running: {' '.join(cmd)}\n")
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start_time
    
    # Stop monitoring
    stats = monitor.stop()
    
    # Clean up temp config
    try:
        temp_config.unlink()
    except:
        pass
    
    print(f"\n✓ Single-machine test completed in {elapsed:.1f}s")
    print(f"  CPU: {stats['cpu_avg']:.1f}% avg, {stats['cpu_max']:.1f}% peak")
    print(f"  RAM: {stats['ram_avg_mb']:.0f} MB avg, {stats['ram_max_mb']:.0f} MB peak")
    
    if result.returncode != 0:
        print(f"\n⚠️  Warning: Test exited with code {result.returncode}")
        if result.stderr:
            print(f"Errors: {result.stderr[:500]}")
    else:
        # Show last few lines of output
        lines = result.stdout.strip().split('\n')
        print(f"\nTest output (last 10 lines):")
        for line in lines[-10:]:
            print(f"  {line}")
    
    return {
        'mode': 'single_machine',
        'protocol': protocol,
        'num_sensors': num_sensors,
        'duration': duration,
        'elapsed': elapsed,
        'cpu_avg': stats['cpu_avg'],
        'cpu_max': stats['cpu_max'],
        'ram_avg_mb': stats['ram_avg_mb'],
        'ram_max_mb': stats['ram_max_mb'],
        'stdout': result.stdout,
        'stderr': result.stderr,
        'returncode': result.returncode
    }


def run_distributed_core(protocol, bind_ip, sensor_port, duration):
    """Run core node for distributed test."""
    print(f"\n{'='*60}")
    print(f"DISTRIBUTED TEST: {protocol.upper()} - CORE NODE")
    print(f"Listening on {bind_ip}:{sensor_port}")
    print(f"Duration: {duration}s")
    print(f"{'='*60}\n")
    
    # Start resource monitoring
    monitor = ResourceMonitor(process_filter='python')
    monitor.start()
    
    # Start core node
    cmd = [
        sys.executable, 'distributed/core_node.py',
        '--bind-ip', bind_ip,
        '--sensor-port', str(sensor_port),
        '--protocol', protocol,
        '--duration', str(duration)
    ]
    
    print(f"Starting core node: {' '.join(cmd)}")
    print(f"\n⏳ Waiting for sensor nodes to connect...")
    print(f"   Run on LAPTOP: python distributed/sensor_node.py \\")
    print(f"                    --core-ip <THIS_MACHINE_IP> \\")
    print(f"                    --core-port {sensor_port} \\")
    print(f"                    --node-id W1 \\")
    print(f"                    --sensors 100 \\")
    print(f"                    --protocol {protocol} \\")
    print(f"                    --duration {duration}\n")
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start_time
    
    # Stop monitoring
    stats = monitor.stop()
    
    print(f"\n✓ Core node completed in {elapsed:.1f}s")
    print(f"  CPU: {stats['cpu_avg']:.1f}% avg, {stats['cpu_max']:.1f}% peak")
    print(f"  RAM: {stats['ram_avg_mb']:.0f} MB avg, {stats['ram_max_mb']:.0f} MB peak")
    
    return {
        'mode': 'distributed_core',
        'protocol': protocol,
        'bind_ip': bind_ip,
        'sensor_port': sensor_port,
        'duration': duration,
        'elapsed': elapsed,
        'cpu_avg': stats['cpu_avg'],
        'cpu_max': stats['cpu_max'],
        'ram_avg_mb': stats['ram_avg_mb'],
        'ram_max_mb': stats['ram_max_mb'],
        'stdout': result.stdout,
        'stderr': result.stderr
    }


def get_network_interfaces():
    """Get available network interfaces."""
    interfaces = {}
    stats = psutil.net_if_addrs()
    
    for iface, addrs in stats.items():
        for addr in addrs:
            if addr.family == 2:  # IPv4
                interfaces[iface] = addr.address
    
    return interfaces


def print_network_info():
    """Display network configuration."""
    print("\n" + "="*60)
    print("NETWORK CONFIGURATION")
    print("="*60)
    
    interfaces = get_network_interfaces()
    for iface, ip in interfaces.items():
        print(f"  {iface:10s} → {ip}")
    
    print("\nFor distributed test, use one of the IPs above")
    print("="*60 + "\n")


def save_results(results, output_file):
    """Save experiment results to JSON."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_file}")


def generate_latex_table(single_results, distributed_results):
    """Generate LaTeX table for paper."""
    single = single_results
    dist = distributed_results
    
    cpu_reduction = ((single['cpu_avg'] - dist['cpu_avg']) / single['cpu_avg']) * 100
    ram_reduction = ((single['ram_avg_mb'] - dist['ram_avg_mb']) / single['ram_avg_mb']) * 100
    
    latex = f"""
\\begin{{table}}[h!]
\\centering
\\caption{{Resource Utilization: Single-Machine vs. Distributed Deployment}}
\\label{{tab:dist-resource}}
\\begin{{tabular}}{{l c c c}}
\\hline
\\textbf{{Metric}} & \\textbf{{Single Machine}} & \\textbf{{Distributed (Core)}} & \\textbf{{Impact}} \\\\ \\hline
CPU Usage (avg) & {single['cpu_avg']:.1f}\\% & {dist['cpu_avg']:.1f}\\% & \\textbf{{{cpu_reduction:+.0f}\\%}} \\\\
CPU Usage (peak) & {single['cpu_max']:.1f}\\% & {dist['cpu_max']:.1f}\\% & \\textbf{{{((single['cpu_max']-dist['cpu_max'])/single['cpu_max'])*100:+.0f}\\%}} \\\\
Memory (RAM) & {single['ram_avg_mb']:.0f} MB & {dist['ram_avg_mb']:.0f} MB & \\textbf{{{ram_reduction:+.0f}\\%}} \\\\
Network & Loopback (lo) & Ethernet/WiFi & Real Traffic \\\\
\\hline
\\end{{tabular}}
\\end{{table}}
"""
    
    print("\n" + "="*60)
    print("LATEX TABLE FOR PAPER (Section 8.3)")
    print("="*60)
    print(latex)
    
    return latex


def main():
    parser = argparse.ArgumentParser(
        description="Run distributed experiment for paper validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Step 1: Run single-machine baseline (on this machine)
  python distributed/run_distributed_experiment.py --mode single --protocol mqtt --duration 60

  # Step 2: Run distributed core (on this machine)
  python distributed/run_distributed_experiment.py --mode core --protocol mqtt --bind-ip 0.0.0.0 --duration 60

  # Step 3: On laptop, run sensor node
  python distributed/sensor_node.py --core-ip <THIS_MACHINE_IP> --core-port 5000 --node-id W1 --sensors 100 --protocol mqtt --duration 60

  # Step 4: Generate comparison
  python distributed/run_distributed_experiment.py --compare results/exp_single.json results/exp_dist.json
        """
    )
    
    parser.add_argument('--mode', choices=['single', 'core', 'compare'], required=True,
                       help='Test mode: single machine, distributed core, or compare results')
    parser.add_argument('--protocol', default='mqtt', help='Protocol to test (mqtt/coap)')
    parser.add_argument('--num-sensors', type=int, default=100, help='Number of sensors')
    parser.add_argument('--duration', type=int, default=60, help='Test duration (seconds)')
    parser.add_argument('--bind-ip', default='0.0.0.0', help='Core bind IP (for distributed)')
    parser.add_argument('--sensor-port', type=int, default=5000, help='Sensor port')
    parser.add_argument('--output', help='Output JSON file')
    parser.add_argument('--compare', nargs=2, metavar=('SINGLE', 'DIST'),
                       help='Compare two result files')
    
    args = parser.parse_args()
    
    # Show network info
    print_network_info()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if args.mode == 'single':
        output = args.output or f'results/distributed_exp/single_{args.protocol}_{timestamp}.json'
        results = run_single_machine_test(args.protocol, args.num_sensors, args.duration)
        save_results(results, output)
        
    elif args.mode == 'core':
        output = args.output or f'results/distributed_exp/dist_{args.protocol}_{timestamp}.json'
        results = run_distributed_core(args.protocol, args.bind_ip, args.sensor_port, args.duration)
        save_results(results, output)
        
    elif args.mode == 'compare':
        if not args.compare:
            print("Error: --compare requires two JSON files")
            sys.exit(1)
        
        with open(args.compare[0]) as f:
            single = json.load(f)
        with open(args.compare[1]) as f:
            dist = json.load(f)
        
        latex = generate_latex_table(single, dist)
        
        # Save LaTeX
        latex_file = f'paper/tables/distributed_comparison_{timestamp}.tex'
        Path(latex_file).parent.mkdir(parents=True, exist_ok=True)
        with open(latex_file, 'w') as f:
            f.write(latex)
        print(f"✓ LaTeX table saved to: {latex_file}")


if __name__ == '__main__':
    main()
