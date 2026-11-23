"""
Integration tests for Flask application and non-blocking background collector.
"""

import time
import pytest
from app import app, collector

@pytest.fixture
def client():
    """Flask test client fixture."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_flask_home_is_non_blocking(client):
    """Verify that visiting '/' responds in <50ms without the former 2-second freeze."""
    # Ensure collector is running
    collector.start()
    time.sleep(0.1)

    start = time.perf_counter()
    response = client.get("/")
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    assert response.status_code == 200
    assert elapsed_ms < 100.0, f"Request took {elapsed_ms:.2f}ms, expected < 100ms"
    assert b"GreenCloud" in response.data
    assert b"Dashboard" in response.data
    assert b"CPU" in response.data
    assert b"Advice" in response.data or b"Advisor" in response.data

def test_flask_metrics_endpoint_prometheus_and_json(client):
    """Verify /metrics returns Prometheus format by default, and JSON when requested."""
    # 1. Prometheus Text Format (Default / Scraped by Prometheus)
    res_prom = client.get("/metrics")
    assert res_prom.status_code == 200
    assert "text/plain" in res_prom.content_type
    prom_text = res_prom.data.decode("utf-8")
    assert "# HELP greencloud_up" in prom_text
    assert "greencloud_up" in prom_text
    assert "greencloud_cpu_used_millicores" in prom_text
    assert "greencloud_power_consumption_watts" in prom_text

    # 2. JSON Format (via content negotiation or format parameter)
    res_json = client.get("/metrics?format=json")
    assert res_json.status_code == 200
    data = res_json.get_json()
    assert "cpu_percent" in data
    assert "memory_percent" in data
    assert "metric_source" in data
    assert "is_container" in data
    assert isinstance(data["cpu_percent"], (int, float))
    assert isinstance(data["memory_percent"], (int, float))

def test_flask_api_snapshot(client):
    """Verify /api/snapshot returns snapshot and rolling history."""
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    data = response.get_json()
    assert "snapshot" in data
    assert "history" in data
    assert isinstance(data["history"], list)

def test_multiple_requests_do_not_duplicate_threads(client):
    """Verify that sending multiple concurrent requests does not spawn extra background threads."""
    import threading
    initial_threads = threading.active_count()

    for _ in range(20):
        res = client.get("/")
        assert res.status_code == 200

    after_threads = threading.active_count()
    assert after_threads == initial_threads, f"Thread count grew from {initial_threads} to {after_threads}"
