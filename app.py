from flask import Flask, jsonify
import psutil
from advisor import advise

app = Flask(__name__)

CPU_REQUEST_M = 100  # what we reserved in deployment.yaml
REPLICAS = 2

import time

def read_cpu_usec():
    # the container's own CPU time, in microseconds
    try:
        with open("/sys/fs/cgroup/cpu.stat") as f:
            for line in f:
                if line.startswith("usage_usec"):
                    return int(line.split()[1])
    except FileNotFoundError:
        pass
    return None

def get_advice():
    start = read_cpu_usec()
    time.sleep(1)
    end = read_cpu_usec()
    if start is None or end is None:
        return 0.0, ["Could not read container CPU usage here."]
    cpu_used_m = (end - start) / 1000  # microseconds per second -> millicores
    return advise(REPLICAS, cpu_used_m, CPU_REQUEST_M, max(cpu_used_m, 1))

@app.route("/")
def home():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent
    utilization, tips = get_advice()
    tips_html = "".join(f"<li>{t}</li>" for t in tips)
    return f"""
    <h1>GreenCloud Dashboard</h1>
    <p>CPU usage: {cpu}%</p>
    <p>Memory usage: {memory}%</p>
    <h2>Advice</h2>
    <p>Utilization of reserved CPU: {utilization:.2f}%</p>
    <ul>{tips_html}</ul>
    """

@app.route("/metrics")
def metrics():
    return jsonify(
        cpu_percent=psutil.cpu_percent(interval=1),
        memory_percent=psutil.virtual_memory().percent,
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)