# GreenCloud 🌿
### Enterprise Cloud Resource Monitoring, Intelligent Optimization & Sustainability Platform

[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-emerald.svg)](https://flask.palletsprojects.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-v1.28+-326ce5.svg)](https://kubernetes.io/)
[![Prometheus](https://img.shields.io/badge/Prometheus-OpenMetrics-orange.svg)](https://prometheus.io/)
[![Tests](https://img.shields.io/badge/Tests-39%20Passed%20%7C%200%20Failed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)]()

GreenCloud is a cloud-native infrastructure monitoring, FinOps cost estimation, and carbon footprint optimization platform. It monitors containerized and host workloads in real time, diagnoses over-provisioned cloud reservations, and generates safe, administrator-approved Kubernetes optimization patches to reduce cloud spend and carbon emissions.

---

## 📑 Table of Contents
1. [The Problem: Cloud Waste & Carbon Emissions](#the-problem-cloud-waste--carbon-emissions)
2. [Platform Architecture](#platform-architecture)
3. [Key Capabilities & Features](#key-capabilities--features)
4. [Scientific Formulas & Mathematical Foundations](#scientific-formulas--mathematical-foundations)
5. [Directory Structure](#directory-structure)
6. [Quick Start & Running Guide](#quick-start--running-guide)
   - [A. Running Locally on Windows/Linux/macOS](#a-running-locally-on-windows)
   - [B. Running in Docker Container](#b-running-in-docker-container)
   - [C. Deploying to Kubernetes (Docker Desktop / Kind)](#c-deploying-to-kubernetes)
   - [D. Prometheus Scraping & Integration](#d-prometheus-scraping--integration)
7. [Automated Verification & Test Suite](#automated-verification--test-suite)
8. [Academic Viva & Presentation Defense Guide](#academic-viva--presentation-defense-guide)

---

## 1. The Problem: Cloud Waste & Carbon Emissions

In modern cloud computing, developers routinely over-provision Kubernetes resource requests (CPU and Memory) to avoid latency spikes and Out-Of-Memory (OOMKill) crashes. Industry studies (Gartner, CNCF) show that average cloud container utilization hovers between **6% and 14%**.

* **Financial Waste (FinOps)**: Cloud providers bill tenants based on *reserved capacity* (requests), not actual usage. Over-provisioning wastes billions of dollars annually.
* **Environmental Impact (Green Computing)**: Idle allocated servers still consume substantial baseline electrical power (~50–60% of peak wattage), producing unnecessary greenhouse gas emissions ($CO_2e$).
* **GreenCloud Solution**: A lightweight platform that tracks real historical peak demand, adds configurable safety buffers, estimates energy & carbon reduction, and generates declarative Kubernetes YAML patches without mutating live clusters automatically.

---

## 2. Platform Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   GreenCloud Platform                                  │
│                                                                                        │
│   ┌────────────────────────────────┐         ┌─────────────────────────────────────┐   │
│   │   Multi-Environment Telemetry  │         │     Intelligent Right-Sizing        │   │
│   │      Background Collector      │         │           Advisor Engine            │   │
│   │  (Linux Cgroup v2, Cgroup v1,  │────────>│    (Peak-Aware CPU + Memory Buffer, │   │
│   │      or Host OS Fallback)      │         │     OOM Prevention, Risk Tiers)     │   │
│   └────────────────────────────────┘         └─────────────────────────────────────┘   │
│                   │                                             │                      │
│                   ▼                                             ▼                      │
│   ┌────────────────────────────────┐         ┌─────────────────────────────────────┐   │
│   │   Sustainability & Carbon      │         │     Safe Optimization Generator     │   │
│   │            Engine              │         │  (Declarative K8s YAML Patch with   │   │
│   │   (SPECpower curves, PUE,      │         │   Human Administrator Review Gate)  │   │
│   │    Regional Grid Intensities)  │         └─────────────────────────────────────┘   │
│   └────────────────────────────────┘                            │                      │
│                   │                                             │                      │
│                   ▼                                             ▼                      │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │                     Modern Enterprise Single-Page Dashboard                    │   │
│   │   (Dark Charcoal, Emerald Accents, Chart.js Streaming Telemetry, 8 Views)      │   │
│   └────────────────────────────────────────────────────────────────────────────────┘   │
│                   │                                             │                      │
│                   ▼                                             ▼                      │
│   ┌────────────────────────────────┐         ┌─────────────────────────────────────┐   │
│   │    Native Prometheus Exporter  │         │      Hardened Kubernetes Manifests  │   │
│   │   (/metrics - OpenMetrics Text │         │     (Non-Root SecurityContext, HPA, │   │
│   │    Format + JSON Negotiation)  │         │      Liveness & Readiness Probes)   │   │
│   └────────────────────────────────┘         └─────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Key Capabilities & Features

1. **Non-Blocking Observability**:
   - Uses an asynchronous daemon thread sampling counters periodically.
   - Dashboard endpoints (`/`, `/api/snapshot`, `/metrics`) respond in **$< 2\text{ ms}$** (eliminating synchronous `time.sleep()` freezes).
2. **Universal Environment Compatibility**:
   - Detects Linux **Cgroup v2** (`/sys/fs/cgroup/cpu.stat`), **Cgroup v1** (`/sys/fs/cgroup/cpu/cpuacct.usage`), or falls back safely to **Host System Metrics** on Windows and bare-metal environments.
3. **Dual-Resource Peak-Aware Right-Sizing**:
   - Optimizes both **CPU** (millicores) and **Memory** (MiB).
   - Enforces configurable safety buffers (default: 25% CPU buffer, 30% Memory buffer).
   - Memory limits are locked at least $32\text{ MiB}$ above requests to eliminate OOMKilled evictions.
4. **Safe Optimization Policy**:
   - Never applies modifications automatically. Generates clean, declarative Kubernetes Deployment patches for administrator inspection and manual application.
5. **Scientific Carbon Footprint & FinOps Modeling**:
   - Computes dynamic power consumption in **Watts**, energy in **kWh/month**, and operational carbon in **$\text{kg } CO_2e/\text{month}$**.
   - Supports regional grid carbon emission factors (India, US East, US West, EU Central, Nordics, and 100% Renewable).
   - Visualizes real-world EPA equivalents (mature trees required for annual offset, and passenger car miles avoided).
6. **Strict Live vs. Demo Workload Separation**:
   - The genuine monitored host/container is marked with a green `[LIVE]` badge.
   - Demonstration workloads (`auth-service`, `analytics-worker`, `redis-cache`) are marked with amber `[DEMO]` badges. Simulated metrics are never misrepresented as real cluster telemetry.
7. **Interactive Simulation Laboratory**:
   - A reactive slider ($1.0\times$ to $6.0\times$) enables real-time capacity stress-testing and demonstrates how advisor recommendations dynamically adapt under heavy bursts.
8. **Genuine Prometheus Exporter**:
   - Serves native Prometheus OpenMetrics text format at `/metrics` with standard `# HELP` and `# TYPE` declarations. Supports content negotiation for JSON clients.
9. **Hardened Kubernetes Manifests**:
   - Pod runs as dedicated non-root user `appuser` (`UID 10001`).
   - `livenessProbe` and `readinessProbe` on `/api/snapshot`.
   - `HorizontalPodAutoscaler` (HPA) configured for 2 to 5 replicas.

---

## 4. Scientific Formulas & Mathematical Foundations

### A. Power Consumption Model (SPECpower & Cloud Carbon Footprint Standard)
$$\text{Workload Power (Watts)} = \left[ P_{\text{cpu}} + P_{\text{ram}} \right] \times \text{PUE} \times \text{Replicas}$$

Where:
* $P_{\text{cpu}} = \text{cores} \times \left( P_{\text{idle}} + \text{utilization\_ratio} \times (P_{\text{max}} - P_{\text{idle}}) \right)$
  * $P_{\text{idle}} = 0.75 \text{ Watts/core}$ (base server idle draw per vCPU)
  * $P_{\text{max}} = 3.50 \text{ Watts/core}$ (peak power draw at 100% load)
* $P_{\text{ram}} = \text{RAM (GB)} \times 0.38 \text{ Watts/GB}$
* $\text{PUE}$ (Power Usage Effectiveness) = $1.20$ for public hyperscale clouds (AWS/GCP), $1.50$ for private data centers.

### B. Energy & Operational Carbon Emissions (GHG Protocol Scope 2)
$$\text{Monthly Energy (kWh)} = \frac{\text{Power (Watts)} \times 730 \text{ hours}}{1000}$$
$$\text{Monthly Carbon (kg } CO_2e) = \frac{\text{Monthly Energy (kWh)} \times I_{\text{grid}}}{1000}$$

Where $I_{\text{grid}}$ is the regional grid carbon intensity in $\text{gCO}_2e/\text{kWh}$:
* **India Central Grid**: $710 \text{ gCO}_2e/\text{kWh}$
* **Global Average**: $440 \text{ gCO}_2e/\text{kWh}$
* **US East (Virginia Cloud Corridor)**: $379 \text{ gCO}_2e/\text{kWh}$
* **EU Central Average**: $230 \text{ gCO}_2e/\text{kWh}$
* **Nordics (Hydro/Nuclear)**: $45 \text{ gCO}_2e/\text{kWh}$
* **Certified 100% Renewable**: $15 \text{ gCO}_2e/\text{kWh}$

### C. Right-Sizing Headroom Formulas
$$\text{Recommended CPU Request (m)} = \max\left(10\text{m}, \lceil \text{Peak CPU (m)} \times (1.0 + \text{safety\_margin}_{\text{cpu}}) \rceil\right)$$
$$\text{Recommended RAM Request (MiB)} = \max\left(32\text{MiB}, \lceil \text{Peak RAM (MiB)} \times (1.0 + \text{safety\_margin}_{\text{mem}}) \rceil\right)$$
$$\text{Recommended RAM Limit (MiB)} = \max\left(\text{RAM Request} + 32\text{MiB}, \lceil \text{Peak RAM} \times 1.5 \rceil\right)$$

---

## 5. Directory Structure

```
greencloud/
├── backup/                                 # Safe backups of original configurations
│   ├── advisor.py.bak
│   ├── app.py.bak
│   ├── deployment.yaml.bak
│   ├── Dockerfile.bak
│   ├── README.md.bak
│   ├── requirements.txt.bak
│   └── service.yaml.bak
├── engine/                                 # Core Calculation & Telemetry Engines
│   ├── __init__.py                         # Package exports
│   ├── models.py                           # Typed dataclasses (WorkloadSpec, CarbonEstimate, etc.)
│   ├── collector.py                        # Non-blocking Cgroup & Host background collector
│   ├── advisor.py                          # Intelligent right-sizing & K8s patch engine
│   ├── carbon.py                           # Energy & Carbon Footprint calculation engine
│   ├── cost.py                             # FinOps cloud billing estimation engine
│   └── prometheus.py                       # Native Prometheus text exporter & validator
├── kubernetes/                             # Hardened Kubernetes Resources
│   ├── hpa.yaml                            # Horizontal Pod Autoscaler (2-5 replicas)
│   └── prometheus-scrape-config.yaml       # Prometheus scrape config & ServiceMonitor
├── static/                                 # Frontend Assets
│   ├── css/
│   │   └── dashboard.css                   # Enterprise dark theme & glassmorphism stylesheet
│   └── js/
│       └── dashboard.js                    # Telemetry streaming, Chart.js, tabs, simulation
├── templates/                              # HTML Templates
│   └── dashboard.html                      # Enterprise Single-Page Dashboard (8 views)
├── tests/                                  # Comprehensive Automated Test Suite (39 Tests)
│   ├── __init__.py
│   ├── test_advisor.py                     # Advisor logic & edge-case unit tests
│   ├── test_carbon.py                      # Carbon & energy calculation tests
│   ├── test_collector.py                   # Background sampler, thread safety & lifecycle
│   ├── test_cost.py                        # Cloud billing & FinOps tests
│   ├── test_dashboard_apis.py              # REST API & HTML template integration tests
│   ├── test_flask_integration.py          # Non-blocking latency & route verification
│   ├── test_prometheus.py                  # OpenMetrics syntax & K8s manifest validation
│   ├── test_verification.py                # End-to-end sample input calculation tests
│   └── run_sample_audit.py                 # Standalone demonstration audit script
├── .gitignore                              # Git exclusion rules
├── .vscode/settings.json                   # Python interpreter & language server configuration
├── advisor.py                              # Backward-compatible facade adapter
├── app.py                                  # Flask server & REST API controller
├── deployment.yaml                         # Hardened Kubernetes Deployment
├── Dockerfile                              # Multi-stage container build with non-root user
├── requirements.txt                        # Version-pinned dependencies
├── service.yaml                            # Kubernetes LoadBalancer service
└── README.md                               # Project documentation & presentation guide
```

---

## 6. Quick Start & Running Guide

### A. Running Locally on Windows / Linux / macOS

1. Ensure Python 3.12 or newer is installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the GreenCloud server:
   ```bash
   python app.py
   ```
4. Open your web browser:
   [**http://localhost:5000**](http://localhost:5000)

### B. Running in Docker Container

1. Build the production Docker container:
   ```bash
   docker build -t greencloud:v5 .
   ```
2. Run the container:
   ```bash
   docker run -d -p 5000:5000 --name greencloud-app greencloud:v5
   ```
3. Open `http://localhost:5000` in your browser.

### C. Deploying to Kubernetes (Docker Desktop / Kind)

1. Apply the hardened deployment and load balancer service:
   ```bash
   kubectl apply -f deployment.yaml
   kubectl apply -f service.yaml
   ```
2. (Optional) Apply Horizontal Pod Autoscaler:
   ```bash
   kubectl apply -f kubernetes/hpa.yaml
   ```
3. Verify running pods and probes:
   ```bash
   kubectl get pods -l app=greencloud
   kubectl get svc greencloud-service
   ```
4. Open `http://localhost:8080` to access the service.

### D. Prometheus Scraping & Integration

GreenCloud's `/metrics` endpoint is natively scrapeable by Prometheus:

```bash
# Verify Prometheus text format
curl -s http://localhost:5000/metrics
```

To configure Prometheus, include this block in your `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'greencloud'
    scrape_interval: 5s
    metrics_path: /metrics
    static_configs:
      - targets: ['localhost:5000']
```

---

## 7. Automated Verification & Test Suite

The project includes **39 automated tests** covering unit calculations, thread safety, concurrency, API endpoints, and Kubernetes manifest validation.

Run the test suite:
```bash
pytest tests/ -v
```

Expected output:
```text
============================= test session starts =============================
collected 39 items

tests/test_advisor.py::test_legacy_advise_backward_compatibility PASSED  [  2%]
tests/test_advisor.py::test_zero_division_protection PASSED              [  5%]
tests/test_advisor.py::test_overprovisioned_workload_recommendation PASSED [  7%]
tests/test_advisor.py::test_underprovisioned_workload_protection PASSED  [ 10%]
tests/test_advisor.py::test_healthy_optimal_workload PASSED              [ 12%]
tests/test_carbon.py::test_calculate_power_watts_scaling PASSED          [ 15%]
tests/test_carbon.py::test_regional_carbon_intensities PASSED            [ 17%]
tests/test_carbon.py::test_pue_impact PASSED                             [ 20%]
tests/test_collector.py::test_runtime_environment_detection PASSED       [ 23%]
tests/test_collector.py::test_collector_lifecycle_and_idempotency PASSED [ 25%]
tests/test_collector.py::test_non_blocking_response_time PASSED          [ 28%]
tests/test_collector.py::test_rolling_history_and_peak_tracking PASSED   [ 30%]
tests/test_collector.py::test_thread_safety_under_concurrent_access PASSED [ 33%]
tests/test_collector.py::test_collector_adapter_to_advisor PASSED        [ 35%]
tests/test_cost.py::test_cloud_cost_calculation PASSED                   [ 38%]
tests/test_cost.py::test_multi_replica_cost PASSED                       [ 41%]
tests/test_dashboard_apis.py::test_dashboard_html_rendering PASSED       [ 43%]
tests/test_dashboard_apis.py::test_api_workloads_separation PASSED       [ 46%]
tests/test_dashboard_apis.py::test_api_audit_live_and_demo PASSED        [ 48%]
tests/test_dashboard_apis.py::test_api_simulate_traffic_spike PASSED     [ 51%]
tests/test_dashboard_apis.py::test_api_system_info PASSED                [ 53%]
tests/test_dashboard_apis.py::test_api_patch_download PASSED             [ 56%]
tests/test_flask_integration.py::test_flask_home_is_non_blocking PASSED  [ 58%]
tests/test_flask_integration.py::test_flask_metrics_endpoint_prometheus_and_json PASSED [ 61%]
tests/test_flask_integration.py::test_flask_api_snapshot PASSED          [ 64%]
tests/test_flask_integration.py::test_multiple_requests_do_not_duplicate_threads PASSED [ 66%]
tests/test_prometheus.py::test_prometheus_formatting_and_validation PASSED [ 69%]
tests/test_prometheus.py::test_prometheus_scrape_endpoint PASSED         [ 71%]
tests/test_prometheus.py::test_kubernetes_deployment_hardening PASSED    [ 74%]
tests/test_prometheus.py::test_kubernetes_service_annotations PASSED     [ 76%]
tests/test_prometheus.py::test_kubernetes_hpa_manifest PASSED            [ 79%]
tests/test_prometheus.py::test_dockerfile_hardening PASSED               [ 82%]
tests/test_verification.py::test_cpu_optimization_right_sizing PASSED    [ 84%]
tests/test_verification.py::test_memory_optimization_right_sizing PASSED [ 87%]
tests/test_verification.py::test_division_by_zero_all_fields PASSED      [ 89%]
tests/test_verification.py::test_carbon_calculations_sample_inputs PASSED [ 92%]
tests/test_verification.py::test_cost_estimation_sample_inputs PASSED    [ 94%]
tests/test_verification.py::test_original_app_compatibility PASSED       [ 97%]
tests/test_verification.py::test_full_audit_consistency PASSED           [100%]

============================= 39 passed in 4.26s ==============================
```

---

## 8. Academic Viva & Presentation Defense Guide

Frequently asked questions and technical answers for your project evaluation:

### Q1: What makes GreenCloud different from standard Kubernetes metrics-server or Prometheus?
> **Answer:** `metrics-server` and Prometheus only provide raw telemetry (e.g. "pod X uses 40m CPU"). They do not interpret efficiency, calculate financial waste, or estimate carbon emissions. GreenCloud sits on top of telemetry to calculate **PUE-adjusted power draw (Watts)**, **regional grid emissions ($gCO_2e$)**, and **FinOps dollar savings**, converting numbers into actionable, peak-aware Kubernetes right-sizing patches.

### Q2: Why does GreenCloud use historical peak measurements instead of average CPU utilization?
> **Answer:** Right-sizing based purely on average utilization is dangerous in production. If a pod averages 5% CPU but spikes to 80% during API calls, cutting its allocation to 10% causes CPU throttling, timeouts, or Out-Of-Memory (OOMKill) crashes. GreenCloud analyzes historical peak consumption and applies a **25% CPU and 30% Memory safety margin** to safeguard service reliability.

### Q3: How was the 2-second HTTP page freeze solved?
> **Answer:** In initial prototypes, CPU sampling called synchronous `time.sleep(1)` inside the request handler, freezing Flask's single thread. GreenCloud implements a non-blocking background daemon thread in `engine/collector.py`. Telemetry is continuously sampled asynchronously in memory; HTTP requests simply read the latest thread-safe snapshot in **$<2\text{ ms}$**.

### Q4: How is container telemetry read across different platforms?
> **Answer:** GreenCloud automatically checks the runtime environment:
> 1. In modern Linux / Kubernetes containers: Reads **Cgroup v2** (`/sys/fs/cgroup/cpu.stat` and `memory.current`).
> 2. In legacy Linux containers: Reads **Cgroup v1** (`/sys/fs/cgroup/cpu/cpuacct.usage` and `memory.usage_in_bytes`).
> 3. Outside containers (e.g. Windows development laptop): Falls back safely to non-blocking host OS metrics via `psutil`, clearly tagging telemetry with `metric_source: host_system` so the user is never misled.

### Q5: Is Kind a public cloud?
> **Answer:** No. **Kind** stands for *Kubernetes IN Docker*. It runs local containerized nodes on a personal computer for local integration testing. In GreenCloud, Kind and Docker Desktop are local testing environments. Real public cloud environments refer to managed services such as AWS EKS, Google Cloud GKE, or Azure AKS.

### Q6: Why does GreenCloud require administrator approval instead of auto-scaling resources directly?
> **Answer:** In enterprise production systems, automatically mutating CPU and memory requests causes rolling pod restarts, dropping active connections. GreenCloud adheres to a **Safe Optimization Policy**: recommendations are formulated into standard declarative Kubernetes Deployment patches for administrator review and controlled deployment.

---

## 9. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
