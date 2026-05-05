import subprocess
import psutil
import time

SCRIPT = ""

for i in range(1, 21):
    print(f"Running iteration {i}...")

    # Start process
    process = subprocess.Popen(["python", SCRIPT])

    p = psutil.Process(process.pid)

    cpu_usage = []
    mem_usage = []

    # Monitor while running
    while process.poll() is None:
        try:
            cpu = p.cpu_percent(interval=0.5)
            mem = p.memory_info().rss / (1024 * 1024)  # MB

            cpu_usage.append(cpu)
            mem_usage.append(mem)
        except psutil.NoSuchProcess:
            break

    # Calculate averages
    avg_cpu = sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0
    avg_mem = sum(mem_usage) / len(mem_usage) if mem_usage else 0

    # Save report
    with open(f"report_{i}.txt", "w") as f:
        f.write(f"Iteration: {i}\n")
        f.write(f"Average CPU Usage: {avg_cpu:.2f}%\n")
        f.write(f"Average Memory Usage: {avg_mem:.2f} MB\n")
        f.write(f"Max Memory Usage: {max(mem_usage) if mem_usage else 0:.2f} MB\n")

    print(f"Iteration {i} done.\n")