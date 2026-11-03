from flask import Flask, jsonify
import psutil

app = Flask(__name__)

@app.route("/")
def home():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent
    return f"""
    <h1>GreenCloud Dashboard</h1>
    <p>CPU usage: {cpu}%</p>
    <p>Memory usage: {memory}%</p>
    <p>Refresh the page to see new numbers.</p>
    """

@app.route("/metrics")
def metrics():
    return jsonify(
        cpu_percent=psutil.cpu_percent(interval=1),
        memory_percent=psutil.virtual_memory().percent,
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)