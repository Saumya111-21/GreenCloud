"""
Unit and integration tests for the Non-Blocking Background Metrics Collector.
Verifies thread-safety, environment detection, non-blocking performance,
rolling history, and peak tracking.
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor

from engine.collector import (
    MetricsCollector,
    CollectorSnapshot,
    detect_runtime_environment,
    get_collector,
    SOURCE_HOST,
    SOURCE_CGROUP_V2,
    SOURCE_CGROUP_V1,
)
from engine.advisor import analyze_and_recommend, run_full_audit
from engine.models import WorkloadSpec


def test_runtime_environment_detection():
    """Verify runtime environment detection identifies host system on Windows."""
    source, is_container = detect_runtime_environment()
    assert source in (SOURCE_HOST, SOURCE_CGROUP_V2, SOURCE_CGROUP_V1)
    assert isinstance(is_container, bool)


def test_collector_lifecycle_and_idempotency():
    """Verify that collector starts, avoids duplicate threads, and stops gracefully."""
    collector = MetricsCollector(sampling_interval_sec=0.2)
    assert not collector.is_running()

    collector.start()
    assert collector.is_running()
    thread_id = collector._thread.ident

    # Call start() again: should be idempotent and not create a new thread
    collector.start()
    assert collector.is_running()
    assert collector._thread.ident == thread_id

    collector.stop()
    assert not collector.is_running()


def test_non_blocking_response_time():
    """Verify get_snapshot() returns in <5ms without blocking."""
    collector = MetricsCollector(sampling_interval_sec=0.2)
    collector.start()
    time.sleep(0.3)  # Wait for at least one sample

    start = time.perf_counter()
    snapshot = collector.get_snapshot()
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    collector.stop()

    assert elapsed_ms < 5.0, f"Snapshot took {elapsed_ms:.2f}ms, expected < 5ms"
    assert isinstance(snapshot, CollectorSnapshot)
    assert snapshot.mem_used_mib > 0
    assert snapshot.sample_count >= 1


def test_rolling_history_and_peak_tracking():
    """Verify historical rolling window and peak tracking."""
    collector = MetricsCollector(sampling_interval_sec=0.2, max_history_len=15)
    collector.start()
    time.sleep(0.7)  # Accumulate ~3 samples

    history = collector.get_history(limit=10)
    snapshot = collector.get_snapshot()
    collector.stop()

    assert len(history) >= 2
    assert snapshot.cpu_peak_m >= snapshot.cpu_used_m
    assert snapshot.mem_peak_mib >= snapshot.mem_used_mib
    assert snapshot.sample_count >= len(history)


def test_thread_safety_under_concurrent_access():
    """Verify concurrent reads from multiple threads while sampling is active."""
    collector = MetricsCollector(sampling_interval_sec=0.1)
    collector.start()

    errors = []

    def reader_task():
        try:
            for _ in range(50):
                snap = collector.get_snapshot()
                hist = collector.get_history()
                assert snap.timestamp > 0
                assert isinstance(hist, list)
                time.sleep(0.005)
        except Exception as e:
            errors.append(e)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(reader_task) for _ in range(10)]
        for f in futures:
            f.result()

    collector.stop()
    assert len(errors) == 0, f"Encountered thread safety errors: {errors}"


def test_collector_adapter_to_advisor():
    """Verify get_resource_metrics() feeds cleanly into the right-sizing and carbon engine."""
    collector = MetricsCollector(sampling_interval_sec=0.2)
    collector.start()
    time.sleep(0.3)

    metrics = collector.get_resource_metrics()
    collector.stop()

    assert metrics.is_simulated is False
    assert metrics.cpu_peak_m >= metrics.cpu_used_m
    assert metrics.mem_peak_mib >= metrics.mem_used_mib

    spec = WorkloadSpec(name="live-test", replicas=1, cpu_request_m=100, cpu_limit_m=200, mem_request_mib=128, mem_limit_mib=256)
    rec = analyze_and_recommend(spec, metrics)
    assert rec.status in ("CRITICAL_OVERPROVISIONED", "OVERPROVISIONED", "OPTIMAL", "UNDERPROVISIONED_WARNING", "CRITICAL_UNDERPROVISIONED")

    audit = run_full_audit(spec, metrics)
    assert audit.current_cost.monthly_cost_usd > 0
    assert audit.current_carbon.monthly_carbon_kg > 0
