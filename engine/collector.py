"""
Non-Blocking Background Metrics Collector for GreenCloud.
Supports Windows, Linux, Docker, and Kubernetes environments.
Detects Cgroup v2, Cgroup v1, and provides a host-level fallback.
Thread-safe, non-blocking, and maintains rolling historical measurements.
"""

import os
import sys
import time
import threading
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Tuple
import psutil

from .models import ResourceMetrics

# Environment metric sources
SOURCE_CGROUP_V2 = "cgroup_v2"
SOURCE_CGROUP_V1 = "cgroup_v1"
SOURCE_HOST = "host_system"


@dataclass
class CollectorSnapshot:
    """Instantaneous snapshot of system or container resource usage."""
    timestamp: float
    cpu_percent: float             # Normalized CPU utilization percentage (0 - 100%)
    cpu_used_m: float              # Consumed CPU in millicores (1000m = 1 vCPU)
    cpu_peak_m: float              # Historical peak CPU consumed in millicores
    mem_used_mib: float            # Consumed memory in MiB
    mem_peak_mib: float            # Historical peak memory in MiB
    mem_percent: float             # Memory utilization percentage
    metric_source: str             # 'cgroup_v2', 'cgroup_v1', or 'host_system'
    is_container: bool             # True if reading container cgroups, False if host fallback
    sample_count: int              # Total samples recorded so far
    cpu_limit_m: Optional[int] = None
    mem_limit_mib: Optional[int] = None
    system_load_avg: Optional[float] = None
    is_simulated: bool = False     # Explicitly flags real vs simulated data

    def to_dict(self) -> dict:
        return asdict(self)


def detect_runtime_environment() -> Tuple[str, bool]:
    """
    Detects whether the application is running inside a container with Cgroup v2 or v1,
    or on a bare-metal/VM host system (such as Windows, macOS, or uncontainerized Linux).
    Returns (metric_source, is_container).
    """
    # Check Cgroup v2 (Unified hierarchy)
    if os.path.exists("/sys/fs/cgroup/cpu.stat"):
        try:
            with open("/sys/fs/cgroup/cpu.stat", "r") as f:
                content = f.read(256)
                if "usage_usec" in content:
                    return SOURCE_CGROUP_V2, True
        except (OSError, PermissionError):
            pass

    # Check Cgroup v1 (Legacy controller hierarchy)
    if os.path.exists("/sys/fs/cgroup/cpu/cpuacct.usage"):
        try:
            with open("/sys/fs/cgroup/cpu/cpuacct.usage", "r") as f:
                val = f.read(64).strip()
                if val.isdigit():
                    return SOURCE_CGROUP_V1, True
        except (OSError, PermissionError):
            pass

    # Host fallback (Windows, macOS, bare Linux without container cgroups)
    return SOURCE_HOST, False


class MetricsCollector:
    """
    Thread-safe background metrics collector.
    Periodically samples system/container resources in a lightweight daemon thread.
    HTTP requests access the latest snapshot instantly without blocking.
    """
    def __init__(self, sampling_interval_sec: float = 1.0, max_history_len: int = 60):
        self.sampling_interval_sec = max(0.2, sampling_interval_sec)
        self.max_history_len = max(10, max_history_len)

        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

        self.metric_source, self.is_container = detect_runtime_environment()

        # Rolling history and peaks
        self._history: deque = deque(maxlen=self.max_history_len)
        self._peak_cpu_m: float = 0.0
        self._peak_mem_mib: float = 0.0
        self._sample_count: int = 0

        # CPU cgroup counters for delta calculation
        self._last_cpu_raw_time: Optional[float] = None
        self._last_timestamp: Optional[float] = None

        # Process handle for process-specific measurements
        self._process = psutil.Process()
        # Initialize psutil cpu percent baseline
        try:
            self._process.cpu_percent(interval=None)
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

        # Initial baseline snapshot
        self._latest_snapshot: CollectorSnapshot = self._create_initial_snapshot()

    def _create_initial_snapshot(self) -> CollectorSnapshot:
        """Creates a safe baseline snapshot prior to the first sampling interval."""
        mem = psutil.virtual_memory()
        mem_used_mib = round(mem.used / (1024.0 * 1024.0), 2)
        return CollectorSnapshot(
            timestamp=time.time(),
            cpu_percent=0.0,
            cpu_used_m=0.0,
            cpu_peak_m=0.0,
            mem_used_mib=mem_used_mib,
            mem_peak_mib=mem_used_mib,
            mem_percent=round(mem.percent, 1),
            metric_source=self.metric_source,
            is_container=self.is_container,
            sample_count=0,
            is_simulated=False
        )

    # -----------------------------------------------------------------------
    # Cgroup reading helpers
    # -----------------------------------------------------------------------
    def _read_cgroup_v2_cpu_usec(self) -> Optional[int]:
        """Reads cumulative CPU usage in microseconds from cgroup v2."""
        try:
            with open("/sys/fs/cgroup/cpu.stat", "r") as f:
                for line in f:
                    if line.startswith("usage_usec"):
                        return int(line.split()[1])
        except (OSError, ValueError, IndexError, PermissionError):
            pass
        return None

    def _read_cgroup_v1_cpu_nsec(self) -> Optional[int]:
        """Reads cumulative CPU usage in nanoseconds from cgroup v1."""
        try:
            with open("/sys/fs/cgroup/cpu/cpuacct.usage", "r") as f:
                return int(f.read().strip())
        except (OSError, ValueError, PermissionError):
            pass
        return None

    def _read_cgroup_memory_mib(self) -> Tuple[Optional[float], Optional[float], Optional[int]]:
        """
        Reads container memory usage and limit in MiB.
        Returns (used_mib, percent, limit_mib).
        """
        try:
            # Cgroup v2
            if self.metric_source == SOURCE_CGROUP_V2:
                with open("/sys/fs/cgroup/memory.current", "r") as f:
                    used_bytes = int(f.read().strip())
                limit_bytes = None
                if os.path.exists("/sys/fs/cgroup/memory.max"):
                    with open("/sys/fs/cgroup/memory.max", "r") as f:
                        max_str = f.read().strip()
                        if max_str != "max" and max_str.isdigit():
                            limit_bytes = int(max_str)
                used_mib = round(used_bytes / (1024.0 * 1024.0), 2)
                limit_mib = round(limit_bytes / (1024.0 * 1024.0)) if limit_bytes else None
                pct = round((used_bytes / limit_bytes) * 100.0, 1) if limit_bytes and limit_bytes > 0 else 0.0
                return used_mib, pct, limit_mib

            # Cgroup v1
            if self.metric_source == SOURCE_CGROUP_V1:
                with open("/sys/fs/cgroup/memory/memory.usage_in_bytes", "r") as f:
                    used_bytes = int(f.read().strip())
                limit_bytes = None
                with open("/sys/fs/cgroup/memory/memory.limit_in_bytes", "r") as f:
                    lim = int(f.read().strip())
                    if lim < 9223372036854771712:  # Not unlimited
                        limit_bytes = lim
                used_mib = round(used_bytes / (1024.0 * 1024.0), 2)
                limit_mib = round(limit_bytes / (1024.0 * 1024.0)) if limit_bytes else None
                pct = round((used_bytes / limit_bytes) * 100.0, 1) if limit_bytes and limit_bytes > 0 else 0.0
                return used_mib, pct, limit_mib

        except (OSError, ValueError, PermissionError):
            pass
        return None, None, None

    # -----------------------------------------------------------------------
    # Sampling cycle
    # -----------------------------------------------------------------------
    def _sample_once(self) -> CollectorSnapshot:
        """Takes a single measurement of CPU and Memory usage across environments."""
        now = time.time()
        cpu_used_m = 0.0
        cpu_percent = 0.0
        mem_used_mib = 0.0
        mem_percent = 0.0
        cpu_limit_m = None
        mem_limit_mib = None

        # 1. Attempt Cgroup sampling if in container
        if self.is_container:
            cgroup_success = False
            raw_cpu_time = None

            if self.metric_source == SOURCE_CGROUP_V2:
                usec = self._read_cgroup_v2_cpu_usec()
                if usec is not None:
                    raw_cpu_time = usec / 1_000_000.0  # seconds
                    cgroup_success = True

            elif self.metric_source == SOURCE_CGROUP_V1:
                nsec = self._read_cgroup_v1_cpu_nsec()
                if nsec is not None:
                    raw_cpu_time = nsec / 1_000_000_000.0  # seconds
                    cgroup_success = True

            if cgroup_success and raw_cpu_time is not None:
                if self._last_cpu_raw_time is not None and self._last_timestamp is not None:
                    delta_t = max(0.001, now - self._last_timestamp)
                    delta_cpu = max(0.0, raw_cpu_time - self._last_cpu_raw_time)
                    # Fraction of core utilized
                    core_utilization = delta_cpu / delta_t
                    cpu_used_m = round(core_utilization * 1000.0, 2)
                    cpu_percent = round(core_utilization * 100.0, 1)

                self._last_cpu_raw_time = raw_cpu_time
                self._last_timestamp = now

                # Read container memory
                c_mem_mib, c_pct, c_lim_mib = self._read_cgroup_memory_mib()
                if c_mem_mib is not None:
                    mem_used_mib = c_mem_mib
                    mem_percent = c_pct if c_pct is not None else 0.0
                    mem_limit_mib = c_lim_mib

        # 2. Host fallback (or fallback if container cgroup read failed)
        if cpu_used_m == 0.0 and mem_used_mib == 0.0:
            # Use non-blocking psutil
            try:
                cpu_percent = round(psutil.cpu_percent(interval=None), 1)
                cpu_cores = psutil.cpu_count(logical=True) or 1
                # Convert system CPU percent to approximate millicores
                cpu_used_m = round((cpu_percent / 100.0) * cpu_cores * 1000.0, 2)

                mem = psutil.virtual_memory()
                mem_used_mib = round(mem.used / (1024.0 * 1024.0), 2)
                mem_percent = round(mem.percent, 1)
                mem_limit_mib = round(mem.total / (1024.0 * 1024.0))
            except Exception:
                pass

        # Update historical peaks and sample counts
        with self._lock:
            self._sample_count += 1
            self._peak_cpu_m = max(self._peak_cpu_m, cpu_used_m)
            self._peak_mem_mib = max(self._peak_mem_mib, mem_used_mib)

            snapshot = CollectorSnapshot(
                timestamp=now,
                cpu_percent=cpu_percent,
                cpu_used_m=cpu_used_m,
                cpu_peak_m=round(self._peak_cpu_m, 2),
                mem_used_mib=mem_used_mib,
                mem_peak_mib=round(self._peak_mem_mib, 2),
                mem_percent=mem_percent,
                metric_source=self.metric_source,
                is_container=self.is_container,
                sample_count=self._sample_count,
                cpu_limit_m=cpu_limit_m,
                mem_limit_mib=mem_limit_mib,
                is_simulated=False
            )
            self._history.append(snapshot.to_dict())
            self._latest_snapshot = snapshot

        return snapshot

    def _worker_loop(self):
        """Background thread loop that periodically samples metrics."""
        while not self._stop_event.is_set():
            try:
                self._sample_once()
            except Exception:
                pass
            # Interruptible sleep: wakes up immediately if stop is requested
            self._stop_event.wait(timeout=self.sampling_interval_sec)

    # -----------------------------------------------------------------------
    # Lifecycle management (Thread-safe, Idempotent)
    # -----------------------------------------------------------------------
    def start(self):
        """Starts the background metrics collection thread idempotently."""
        with self._lock:
            if self._running:
                return  # Avoid duplicate background collector threads
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._worker_loop,
                name="GreenCloudMetricsCollector",
                daemon=True  # Terminates cleanly with main process
            )
            self._running = True
            self._thread.start()

    def stop(self, timeout_sec: float = 2.0):
        """Stops the collector thread gracefully."""
        with self._lock:
            if not self._running:
                return
            self._stop_event.set()
            self._running = False
            thread = self._thread

        if thread and thread.is_alive():
            thread.join(timeout=timeout_sec)

    def is_running(self) -> bool:
        """Returns True if the background collector thread is active."""
        with self._lock:
            return self._running and (self._thread is not None and self._thread.is_alive())

    # -----------------------------------------------------------------------
    # Data Accessors (Non-Blocking, <1ms response)
    # -----------------------------------------------------------------------
    def get_snapshot(self) -> CollectorSnapshot:
        """
        Instantly returns the most recent metrics snapshot without blocking.
        Execution time is typically < 0.1ms.
        """
        with self._lock:
            return self._latest_snapshot

    def get_history(self, limit: int = 60) -> List[dict]:
        """Returns the recent rolling history of measurements for charting."""
        with self._lock:
            samples = list(self._history)
            return samples[-limit:]

    def get_resource_metrics(self) -> ResourceMetrics:
        """
        Adapts the current collected metrics into an engine ResourceMetrics model
        ready for the right-sizing and carbon advisor.
        """
        snapshot = self.get_snapshot()
        return ResourceMetrics(
            cpu_used_m=snapshot.cpu_used_m,
            cpu_peak_m=max(snapshot.cpu_peak_m, snapshot.cpu_used_m, 1.0),
            mem_used_mib=snapshot.mem_used_mib,
            mem_peak_mib=max(snapshot.mem_peak_mib, snapshot.mem_used_mib, 16.0),
            timestamp=snapshot.timestamp,
            sample_count=snapshot.sample_count,
            is_simulated=False  # Actual measurement, never simulated
        )

    def reset_peaks(self):
        """Resets historical peaks (e.g. for a new monitoring window)."""
        with self._lock:
            snap = self._latest_snapshot
            self._peak_cpu_m = snap.cpu_used_m
            self._peak_mem_mib = snap.mem_used_mib


# ---------------------------------------------------------------------------
# Global Singleton Accessor
# ---------------------------------------------------------------------------
_GLOBAL_COLLECTOR: Optional[MetricsCollector] = None
_INIT_LOCK = threading.Lock()

def get_collector() -> MetricsCollector:
    """
    Returns the process-wide MetricsCollector singleton.
    Thread-safe and initialized on first access.
    """
    global _GLOBAL_COLLECTOR
    with _INIT_LOCK:
        if _GLOBAL_COLLECTOR is None:
            _GLOBAL_COLLECTOR = MetricsCollector(sampling_interval_sec=1.0)
            _GLOBAL_COLLECTOR.start()
        return _GLOBAL_COLLECTOR
