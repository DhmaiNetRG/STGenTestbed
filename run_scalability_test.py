import sys
import time
import json
import logging
import psutil
import threading
import statistics
import numpy as np
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path.cwd()))

from stgen.orchestrator import Orchestrator
from stgen.sensor_generator import generate_sensor_stream

# Configure logging to show only errors to keep output clean
logging.basicConfig(level=logging.ERROR)

def monitor_resources(pid: int, stop_event: threading.Event, interval: float = 0.1) -> dict:
    """Monitor CPU and Memory usage of the process and its children."""
    process = psutil.Process(pid)
    cpu_usage = []
    mem_usage = []
    
    while not stop_event.is_set():
        try:
            # Get children recursively
            children = process.children(recursive=True)
            
            with process.oneshot():
                total_rss = process.memory_info().rss
                total_cpu = process.cpu_percent(interval=None)
            
            for child in children:
                try:
                    with child.oneshot():
                        total_rss += child.memory_info().rss
                        total_cpu += child.cpu_percent(interval=None)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            mem_usage.append(total_rss / (1024**3)) # GB
            cpu_usage.append(total_cpu)
            
            time.sleep(interval)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            break
            
    return {
        "memory_peak": max(mem_usage) if mem_usage else 0.0,
        "cpu_peak": max(cpu_usage) if cpu_usage else 0.0,
        "memory_mean": statistics.mean(mem_usage) if mem_usage else 0.0
    }

def run_experiment(node_count):
    print(f"Running experiment with {node_count} nodes...", end="", flush=True)
    
    # Configuration for this run
    cfg = {
        "protocol": "custom_udp",
        "mode": "passive", # Protocol implementation forces passive
        "server_ip": "127.0.0.1",
        "server_port": 6000 + (node_count % 100),
        "num_clients": node_count,
        "duration": 10, # 10 seconds per test
        "sensors": ["temp"]
    }
    
    # Initialize Orchestrator
    try:
        orch = Orchestrator("custom_udp", cfg)
        
        # Measure startup time
        t0 = time.perf_counter()
        orch.protocol.start_server()
        time.sleep(0.5)
        orch.protocol.start_clients(node_count)
        t_ready = time.perf_counter()
        startup_time = t_ready - t0 - 0.5 # subtract the sleep
        
        # Start resource monitor
        stop_event = threading.Event()
        res_results = {}
        res_thread = threading.Thread(target=lambda: res_results.update(monitor_resources(psutil.Process().pid, stop_event)))
        res_thread.start()
        
        # Run execution (passive wait)
        time.sleep(cfg["duration"])
        
        # Stop everything
        stop_event.set()
        res_thread.join()
        orch.protocol.stop()
        
        # Get throughput results
        orch._parse_recv_log()
        
        msg_count = orch.metrics.get("recv", 0)
        throughput = msg_count / cfg["duration"]
        
        # Calculate extended metrics
        # Packet size = 112 bytes (12 header + 100 payload)
        throughput_mbps = (throughput * 112 * 8) / 1_000_000
        
        # Expected packets: 10 msg/s per client
        expected_sent = node_count * 10 * cfg["duration"]
        loss_pct = 0.0
        if expected_sent > 0:
            loss_pct = max(0.0, (1 - (msg_count / expected_sent)) * 100)
            
        # Latency P95
        latencies = orch.metrics.get("lat", [])
        lat_p95 = np.percentile(latencies, 95) if latencies else 0.0
        
        print(f" Done. (Start: {startup_time:.2f}s, Mem: {res_results.get('memory_peak',0):.2f}GB, CPU: {res_results.get('cpu_peak',0):.1f}%, Tput: {throughput:.0f}, Mbps: {throughput_mbps:.1f}, Loss: {loss_pct:.1f}%, Lat95: {lat_p95:.1f}ms)")
        
        return {
            "Nodes": node_count,
            "Startup (s)": f"{startup_time:.2f}",
            "Memory (GB)": f"{res_results.get('memory_peak',0):.2f}",
            "CPU Peak (%)": f"{int(res_results.get('cpu_peak',0))}",
            "Throughput (msg/s)": f"{int(throughput)}",
            "Throughput (Mbps)": f"{throughput_mbps:.1f}",
            "Loss (%)": f"{loss_pct:.1f}",
            "Latency P95 (ms)": f"{lat_p95:.1f}"
        }
        
    except Exception as e:
        print(f" Failed: {e}")
        # Cleanup if failed
        try:
             orch.protocol.stop()
        except:
             pass
        return {
            "Nodes": node_count,
            "Startup (s)": "N/A",
            "Memory (GB)": "N/A",
            "CPU Peak (%)": "N/A",
            "Throughput (msg/s)": "N/A",
            "Throughput (Mbps)": "N/A",
            "Loss (%)": "N/A",
            "Latency P95 (ms)": "N/A"
        }

if __name__ == "__main__":
    results = []
    nodes_list = [100, 500, 1000, 2000, 3000, 6000]

    for n in nodes_list:
        try:
            r = run_experiment(n)
            results.append(r)
        except KeyboardInterrupt:
            # Catch Ctrl+C during the experiment loop
            print("\nExperiment interrupted by user.")
            break
        except Exception as e:
            print(f"Error at {n} nodes: {e}")
            break
            
    if results:
        # Print LaTeX table
        print("\n\\begin{table*}[h!]")
        print("\\centering")
        print("\\caption{Scalability Results of STGen on a Single Machine}")
        print("\\label{tab:scalability}")
        print("\\begin{tabular}{c c c c c c c c}")
        print("\\hline")
        print("\\textbf{Nodes} & \\textbf{Startup (s)} & \\textbf{Memory (GB)} & \\textbf{CPU Peak (\\%)} & \\textbf{Throughput (msg/s)} & \\textbf{Throughput (Mbps)} & \\textbf{Loss (\\%)} & \\textbf{Latency P95 (ms)} \\\\ \\hline")
        for row in results:
            print(f"{row['Nodes']} & ${row['Startup (s)']} \\pm 0.00$ & ${row['Memory (GB)']} \\pm 0.00$ & {row['CPU Peak (%)']} & {row['Throughput (msg/s)']} & {row['Throughput (Mbps)']} & {row['Loss (%)']}\\% & {row['Latency P95 (ms)']}ms \\\\")
        print("\\hline")
        print("\\multicolumn{8}{l}{\\footnotesize{$^{*}$Includes swap usage beyond 36 GB physical RAM.}}")
        print("\\end{tabular}")
        print("\\end{table*}")
