import subprocess
import psutil
import time
import csv
import re
import os
import sys

# Configuration
ITERATIONS = 20
PLAYWRIGHT = './playwright_script.py'
SELENIUM = './selenium_script.py'
SCRIPTS_TO_TEST = [PLAYWRIGHT, SELENIUM]
REPORT_FILE = "benchmark_results.csv"

# Regex patterns to parse the standard output from your test scripts
AXE_PAGE_PATTERN = r"Hasil Aksesibilitas:\s*(.+?)\s*---"
AXE_COUNT_PATTERN = r"Ditemukan\s+(\d+)\s+pelanggaran"

def run_script(script_name, iteration):
    print(f"[{script_name}] Starting iteration {iteration}/{ITERATIONS}...")
    
    start_time = time.time()
    safe_name = os.path.basename(script_name)
    log_filename = f"temp_log_{safe_name}_{iteration}.txt"
    
    # 1. Force UTF-8 encoding for child process streams
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    with open(log_filename, "w", encoding="utf-8") as log_file:
        # 2. Add "-u" flag to ensure output is unbuffered and pass the env
        process = subprocess.Popen(
            [sys.executable, "-u", script_name],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=env
        )

        cpu_usage = []
        mem_usage = []

        try:
            p = psutil.Process(process.pid)
            
            # Prime the CPU calculation (psutil needs a baseline call before it can calculate a %)
            p.cpu_percent(interval=None) 
            
            # Monitor resources while the process is active
            while process.poll() is None:
                try:
                    # 1. Grab the Python process AND all spawned browsers/drivers
                    all_procs = [p] + p.children(recursive=True)
                    
                    total_cpu = 0.0
                    total_mem = 0.0
                    
                    for proc in all_procs:
                        try:
                            # interval=None makes it non-blocking, returning % since last call
                            total_cpu += proc.cpu_percent(interval=None)
                            total_mem += proc.memory_info().rss
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            # Processes might close mid-loop, just ignore them
                            pass
                    
                    cpu_usage.append(total_cpu)
                    mem_usage.append(total_mem / (1024 * 1024)) # Convert bytes to MB
                    
                    # 2. Block for 0.5 seconds to act as our polling interval
                    time.sleep(0.5)
                    print(".", end="", flush=True) 
                    
                except Exception:
                    # Catch broad exceptions (like psutil.ZombieProcess) if the main process dies mid-loop
                    break
            
            print() # Print a newline when the dots finish
            
        except Exception:
            pass # Process finished extremely quickly
            
        # FORCE the script to wait until all inherited child processes completely terminate
        process.wait()

    end_time = time.time()
    total_time = end_time - start_time
    
    # Did the process exit cleanly? (unittest returns 0 for pass, >0 for fail)
    status = "Pass" if process.returncode == 0 else "Fail"

    # Calculate Resource Averages
    avg_cpu = sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0
    max_cpu = max(cpu_usage) if cpu_usage else 0
    avg_mem = sum(mem_usage) / len(mem_usage) if mem_usage else 0
    max_mem = max(mem_usage) if mem_usage else 0

    # Parse the log file for Axe violations
    axe_scores = {"Login Page": 0, "Dashboard": 0, "Files Page": 0, "Settings Page": 0}
    current_axe_page = None
    
    try:
        with open(log_filename, "r", encoding="utf-8") as log_file:
            for line in log_file:
                # Check for Axe page header
                page_match = re.search(AXE_PAGE_PATTERN, line)
                if page_match:
                    current_axe_page = page_match.group(1).strip()
                    
                # Check for Axe violation count directly after header
                elif current_axe_page and "Ditemukan" in line:
                    count_match = re.search(AXE_COUNT_PATTERN, line)
                    if count_match:
                        axe_scores[current_axe_page] = int(count_match.group(1))
                    current_axe_page = None # Reset state
    except FileNotFoundError:
        print(f"  [Warning] Could not find log file {log_filename} to parse Axe scores.")

    # Clean up the temporary log file SAFELY
    try:
        if os.path.exists(log_filename):
            os.remove(log_filename)
    except PermissionError:
        print(f"  [Warning] Could not delete {log_filename}. A browser process is likely still holding it open. Skipping deletion.")
    except Exception as e:
        print(f"  [Warning] Error removing {log_filename}: {e}")

    print(f"[{script_name}] Iteration {iteration} finished: {status} in {total_time:.2f}s\n")

    return {
        "Script": script_name,
        "Iteration": iteration,
        "Status": status,
        "Total_Time_Sec": round(total_time, 2),
        "Avg_CPU_%": round(avg_cpu, 2),
        "Max_CPU_%": round(max_cpu, 2),
        "Avg_Mem_MB": round(avg_mem, 2),
        "Max_Mem_MB": round(max_mem, 2),
        "Axe_Login": axe_scores.get("Login Page", "N/A"),
        "Axe_Dashboard": axe_scores.get("Dashboard", "N/A"),
        "Axe_Files": axe_scores.get("Files Page", "N/A"),
        "Axe_Settings": axe_scores.get("Settings Page", "N/A"),
    }

def main():
    results = []
    
    # Run the iterations
    for script in SCRIPTS_TO_TEST:
        for i in range(1, ITERATIONS + 1):
            try:
                run_data = run_script(script, i)
                results.append(run_data)
            except Exception as e:
                print(f"\n[FATAL ERROR] Iteration {i} of {script} crashed the wrapper: {e}\n")
            
            # Brief cooldown between runs to let the server and OS settle
            time.sleep(2) 

    # Export to CSV
    if results:
        headers = results[0].keys()
        with open(REPORT_FILE, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(results)
            
        print(f"\n✅ Benchmark complete! Report saved to {REPORT_FILE}")

if __name__ == "__main__":
    main()