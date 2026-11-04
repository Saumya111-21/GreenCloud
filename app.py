from flask import Flask, jsonify
import psutil
from advisor import advise

app = Flask(__name__)

CPU_REQUEST_M = 100  # what we reserved in deployment.yaml
REPLICAS = 2

def get_advice():
    cpu_percent = psutil.cpu_percent(interval=1)
    # convert whole-machine percent to a rough "millicores used" value
    cpu_used_m = cpu_percent / 100 * psutil.cpu_count() * 1000
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