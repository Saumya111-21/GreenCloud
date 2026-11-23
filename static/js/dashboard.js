/**
 * GreenCloud Enterprise Dashboard Controller
 * Handles real-time polling, Chart.js telemetry, tab routing,
 * workload auditing, simulation lab, and Kubernetes patch generation.
 */

// State
let isStreaming = true;
let pollTimer = null;
let currentPatchWorkloadId = "greencloud-live";
let currentPatchYaml = "";
let currentGridRegion = "india";

// Chart instances
let overviewLiveChart = null;
let overviewSavingsChart = null;
let liveFullTelemetryChart = null;
let analyticsAllocationChart = null;
let analyticsMemoryChart = null;
let greenRegionalChart = null;

// Initial Setup
document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initCharts();
  initGridRegionSelect();
  startPolling();
  loadWorkloads();
  loadSystemInfo();
  loadAdvisorData("greencloud-live");
  runSimulation(2.5);
});

// --------------------------------------------------------------------------
// Tab Routing
// --------------------------------------------------------------------------
function initTabs() {
  const navItems = document.querySelectorAll(".sidebar-nav .nav-item");
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const tabId = item.getAttribute("data-tab");
      switchTab(tabId);
    });
  });
}

function switchTab(tabId) {
  // Update sidebar active state
  document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => {
    if (item.getAttribute("data-tab") === tabId) {
      item.classList.add("active");
      const titleText = item.textContent.trim();
      document.getElementById("current-page-title").textContent = titleText;
    } else {
      item.classList.remove("active");
    }
  });

  // Switch visible tab pane
  document.querySelectorAll(".tab-pane").forEach(pane => {
    if (pane.id === tabId) {
      pane.classList.add("active");
    } else {
      pane.classList.remove("active");
    }
  });

  // Trigger chart resize on tab switch
  setTimeout(() => {
    window.dispatchEvent(new Event('resize'));
  }, 100);
}

// --------------------------------------------------------------------------
// Real-time Telemetry Polling (Every 2.5s)
// --------------------------------------------------------------------------
function startPolling() {
  fetchSnapshot();
  pollTimer = setInterval(() => {
    if (isStreaming) {
      fetchSnapshot();
    }
  }, 2500);
}

function toggleStream() {
  isStreaming = !isStreaming;
  const btn = document.getElementById("btn-toggle-stream");
  const dot = document.getElementById("collector-status-dot");
  const statusTxt = document.getElementById("collector-status-text");

  if (isStreaming) {
    btn.textContent = "Pause Stream";
    dot.style.background = "var(--emerald-primary)";
    statusTxt.textContent = "Collector Active";
  } else {
    btn.textContent = "Resume Stream";
    dot.style.background = "var(--amber-demo)";
    statusTxt.textContent = "Stream Paused";
  }
}

async function fetchSnapshot() {
  try {
    const res = await fetch("/api/snapshot");
    if (!res.ok) throw new Error("API network failure");
    const data = await res.json();
    const snap = data.snapshot;
    const history = data.history || [];

    updateHeaderEnvironment(snap);
    updateOverviewMetrics(snap);
    updateLiveTelemetryTab(snap);
    updateChartsWithHistory(history, snap);
  } catch (err) {
    const dot = document.getElementById("collector-status-dot");
    const statusTxt = document.getElementById("collector-status-text");
    if (dot && statusTxt) {
      dot.style.background = "var(--red-critical)";
      statusTxt.textContent = "Collector Disconnected";
    }
  }
}

function updateHeaderEnvironment(snap) {
  const badge = document.getElementById("env-badge");
  if (!badge) return;

  if (snap.is_container) {
    badge.className = "env-tag container";
    badge.innerHTML = `🟢 Container Cgroup (${snap.metric_source})`;
  } else {
    badge.className = "env-tag host";
    badge.innerHTML = `💻 Host System Fallback (${snap.metric_source})`;
  }

  const sampleBadge = document.getElementById("collector-sample-badge");
  if (sampleBadge) {
    sampleBadge.textContent = `#${snap.sample_count}`;
  }
}

function updateOverviewMetrics(snap) {
  const elCpuPct = document.getElementById("overview-cpu-pct");
  const elCpuM = document.getElementById("overview-cpu-m");
  const elCpuPeak = document.getElementById("overview-cpu-peak");
  const elMemPct = document.getElementById("overview-mem-pct");
  const elMemMib = document.getElementById("overview-mem-mib");
  const elMemPeak = document.getElementById("overview-mem-peak");

  if (elCpuPct) elCpuPct.textContent = `${snap.cpu_percent.toFixed(1)}%`;
  if (elCpuM) elCpuM.textContent = `${snap.cpu_used_m.toFixed(2)}m used`;
  if (elCpuPeak) elCpuPeak.textContent = `Historical Peak: ${snap.cpu_peak_m.toFixed(2)}m`;

  if (elMemPct) elMemPct.textContent = `${snap.mem_percent.toFixed(1)}%`;
  if (elMemMib) elMemMib.textContent = `${snap.mem_used_mib.toFixed(1)} MiB`;
  if (elMemPeak) elMemPeak.textContent = `Historical Peak: ${snap.mem_peak_mib.toFixed(1)} MiB`;
}

function updateLiveTelemetryTab(snap) {
  const elSource = document.getElementById("live-source-mode");
  const elIsCont = document.getElementById("live-is-container");
  const elSamples = document.getElementById("live-sample-count");
  const elPeakCpu = document.getElementById("live-peak-cpu-txt");
  const elCurrCpu = document.getElementById("live-curr-cpu-txt");
  const elPeakMem = document.getElementById("live-peak-mem-txt");
  const elCurrMem = document.getElementById("live-curr-mem-txt");
  const elCpuBar = document.getElementById("live-cpu-bar");
  const elMemBar = document.getElementById("live-mem-bar");

  if (elSource) elSource.textContent = snap.metric_source;
  if (elIsCont) elIsCont.textContent = snap.is_container ? "True (Docker/K8s)" : "False (Host/Baremetal)";
  if (elSamples) elSamples.textContent = snap.sample_count;

  if (elPeakCpu) elPeakCpu.textContent = `${snap.cpu_peak_m.toFixed(2)}m`;
  if (elCurrCpu) elCurrCpu.textContent = `Now: ${snap.cpu_used_m.toFixed(2)}m`;
  if (elPeakMem) elPeakMem.textContent = `${snap.mem_peak_mib.toFixed(1)} MiB`;
  if (elCurrMem) elCurrMem.textContent = `Now: ${snap.mem_used_mib.toFixed(1)} MiB`;

  if (elCpuBar) {
    const pct = Math.min(100, (snap.cpu_used_m / Math.max(1, snap.cpu_peak_m)) * 100);
    elCpuBar.style.width = `${pct}%`;
  }
  if (elMemBar) {
    const pct = Math.min(100, (snap.mem_used_mib / Math.max(1, snap.mem_peak_mib)) * 100);
    elMemBar.style.width = `${pct}%`;
  }
}

// --------------------------------------------------------------------------
// Chart Initialization & Rendering
// --------------------------------------------------------------------------
function initCharts() {
  const chartColorEmerald = "#10b981";
  const chartColorBlue = "#3b82f6";

  // 1. Overview Live Mini Stream Chart
  const ctxOverview = document.getElementById("overviewLiveChart")?.getContext("2d");
  if (ctxOverview) {
    overviewLiveChart = new Chart(ctxOverview, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "CPU Used (m)",
            borderColor: chartColorEmerald,
            backgroundColor: "rgba(16, 185, 129, 0.1)",
            borderWidth: 2,
            tension: 0.3,
            fill: true,
            data: []
          },
          {
            label: "Memory (MiB)",
            borderColor: chartColorBlue,
            borderWidth: 1.5,
            borderDash: [4, 4],
            tension: 0.3,
            data: [],
            yAxisID: "y1"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#9ca3af", font: { size: 11 } } } },
        scales: {
          x: { display: false },
          y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#6b7280" } },
          y1: { position: "right", grid: { drawOnChartArea: false }, ticks: { color: "#6b7280" } }
        }
      }
    });
  }

  // 2. Overview Savings Comparison Chart
  const ctxSavings = document.getElementById("overviewSavingsChart")?.getContext("2d");
  if (ctxSavings) {
    overviewSavingsChart = new Chart(ctxSavings, {
      type: "bar",
      data: {
        labels: ["Monthly Cost ($)", "Carbon (kg CO2e)", "CPU Request (m)"],
        datasets: [
          {
            label: "Before Optimization",
            backgroundColor: "rgba(239, 68, 68, 0.7)",
            data: [4.90, 0.12, 100]
          },
          {
            label: "Right-Sized (Recommended)",
            backgroundColor: "rgba(16, 185, 129, 0.8)",
            data: [0.80, 0.04, 10]
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#9ca3af" } } },
        scales: {
          x: { ticks: { color: "#9ca3af" } },
          y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#6b7280" } }
        }
      }
    });
  }

  // 3. Live Full Telemetry Stream Chart
  const ctxLiveFull = document.getElementById("liveFullTelemetryChart")?.getContext("2d");
  if (ctxLiveFull) {
    liveFullTelemetryChart = new Chart(ctxLiveFull, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "CPU Usage (%)",
            borderColor: chartColorEmerald,
            backgroundColor: "rgba(16, 185, 129, 0.15)",
            borderWidth: 2,
            tension: 0.25,
            fill: true,
            data: []
          },
          {
            label: "Memory Usage (%)",
            borderColor: chartColorBlue,
            borderWidth: 2,
            tension: 0.25,
            data: []
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#9ca3af" } } },
        scales: {
          x: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#6b7280", maxTicksLimit: 8 } },
          y: { min: 0, max: 100, grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#6b7280" } }
        }
      }
    });
  }

  // 4. Analytics: Allocated vs Used CPU
  const ctxAnalyticsAlloc = document.getElementById("analyticsAllocationChart")?.getContext("2d");
  if (ctxAnalyticsAlloc) {
    analyticsAllocationChart = new Chart(ctxAnalyticsAlloc, {
      type: "bar",
      data: {
        labels: ["greencloud-live", "auth-service", "analytics-worker", "redis-cache"],
        datasets: [
          { label: "CPU Request (Allocated m)", backgroundColor: "#374151", data: [100, 500, 200, 150] },
          { label: "Measured Peak CPU (m)", backgroundColor: "#10b981", data: [2.0, 115.0, 385.0, 88.0] }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#9ca3af" } } },
        scales: {
          x: { ticks: { color: "#9ca3af" } },
          y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#6b7280" } }
        }
      }
    });
  }

  // 5. Analytics: Memory Allocation
  const ctxAnalyticsMem = document.getElementById("analyticsMemoryChart")?.getContext("2d");
  if (ctxAnalyticsMem) {
    analyticsMemoryChart = new Chart(ctxAnalyticsMem, {
      type: "bar",
      data: {
        labels: ["greencloud-live", "auth-service", "analytics-worker", "redis-cache"],
        datasets: [
          { label: "RAM Request (MiB)", backgroundColor: "#1e3a8a", data: [64, 1024, 512, 512] },
          { label: "Measured Peak RAM (MiB)", backgroundColor: "#60a5fa", data: [45, 250, 960, 310] }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#9ca3af" } } },
        scales: {
          x: { ticks: { color: "#9ca3af" } },
          y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#6b7280" } }
        }
      }
    });
  }

  // 6. Regional Carbon Comparison Chart
  const ctxRegional = document.getElementById("greenRegionalChart")?.getContext("2d");
  if (ctxRegional) {
    greenRegionalChart = new Chart(ctxRegional, {
      type: "bar",
      data: {
        labels: ["Renewable", "Nordics", "EU Central", "US East", "Global", "India"],
        datasets: [
          {
            label: "Monthly kg CO2e / workload",
            backgroundColor: ["#10b981", "#34d399", "#60a5fa", "#f59e0b", "#f97316", "#ef4444"],
            data: [0.003, 0.008, 0.04, 0.07, 0.08, 0.12]
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#9ca3af" } },
          y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#6b7280" } }
        }
      }
    });
  }
}

function updateChartsWithHistory(history, snap) {
  if (!history || history.length === 0) return;

  const labels = history.map((_, i) => `${i + 1}s`);
  const cpuMSeries = history.map(h => h.cpu_used_m || 0);
  const memMibSeries = history.map(h => h.mem_used_mib || 0);
  const cpuPctSeries = history.map(h => h.cpu_percent || 0);
  const memPctSeries = history.map(h => h.mem_percent || 0);

  // Update Overview Mini Live Chart
  if (overviewLiveChart) {
    overviewLiveChart.data.labels = labels;
    overviewLiveChart.data.datasets[0].data = cpuMSeries;
    overviewLiveChart.data.datasets[1].data = memMibSeries;
    overviewLiveChart.update("none");
  }

  // Update Full Telemetry Chart
  if (liveFullTelemetryChart) {
    liveFullTelemetryChart.data.labels = labels;
    liveFullTelemetryChart.data.datasets[0].data = cpuPctSeries;
    liveFullTelemetryChart.data.datasets[1].data = memPctSeries;
    liveFullTelemetryChart.update("none");
  }
}

// --------------------------------------------------------------------------
// Workload Explorer
// --------------------------------------------------------------------------
async function loadWorkloads() {
  try {
    const res = await fetch("/api/workloads");
    const data = await res.json();

    renderOverviewWorkloads(data);
    renderWorkloadExplorer(data);
  } catch (err) {
    console.error("Failed to load workloads", err);
  }
}

function renderOverviewWorkloads(data) {
  const tbody = document.getElementById("overview-workload-tbody");
  if (!tbody) return;

  const allWorkloads = [data.live_workload, ...data.demo_workloads];
  tbody.innerHTML = allWorkloads.map(w => {
    const badgeClass = w.is_simulated ? "badge-demo" : "badge-live";
    const badgeText = w.is_simulated ? "DEMO" : "LIVE";
    return `
      <tr>
        <td><span class="badge ${badgeClass}">${badgeText}</span></td>
        <td><strong>${w.name}</strong></td>
        <td><code>${w.namespace}</code></td>
        <td>${w.replicas}</td>
        <td>${w.metrics.cpu_used_m.toFixed(1)}m / ${w.cpu_request_m}m</td>
        <td>${w.metrics.mem_used_mib.toFixed(0)}MiB / ${w.mem_request_mib}MiB</td>
        <td><span class="delta-good">${w.status}</span></td>
        <td>
          <button class="btn-secondary" style="padding: 4px 10px; font-size: 0.75rem;" onclick="openPatchModal('${w.id}')">
            Review Patch
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

function renderWorkloadExplorer(data) {
  const liveContainer = document.getElementById("live-workload-container");
  const demoContainer = document.getElementById("demo-workloads-container");

  // Render LIVE Workload
  if (liveContainer && data.live_workload) {
    const lw = data.live_workload;
    liveContainer.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
        <div>
          <h4 style="font-size: 1.05rem; color: #fff;">${lw.name}</h4>
          <p style="font-size: 0.8rem; color: var(--text-muted);">${lw.description}</p>
        </div>
        <span class="badge badge-live">GENUINE MEASUREMENT</span>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 16px;">
        <div style="background: rgba(0,0,0,0.25); padding: 10px; border-radius: var(--radius-md);">
          <div style="font-size: 0.72rem; color: var(--text-muted);">Current CPU</div>
          <div style="font-size: 1.1rem; font-weight: 700; color: #fff;">${lw.metrics.cpu_used_m.toFixed(2)}m</div>
          <div style="font-size: 0.72rem; color: var(--emerald-light);">Peak: ${lw.metrics.cpu_peak_m.toFixed(2)}m</div>
        </div>

        <div style="background: rgba(0,0,0,0.25); padding: 10px; border-radius: var(--radius-md);">
          <div style="font-size: 0.72rem; color: var(--text-muted);">Current RAM</div>
          <div style="font-size: 1.1rem; font-weight: 700; color: #fff;">${lw.metrics.mem_used_mib.toFixed(1)} MiB</div>
          <div style="font-size: 0.72rem; color: #93c5fd;">Peak: ${lw.metrics.mem_peak_mib.toFixed(1)} MiB</div>
        </div>

        <div style="background: rgba(0,0,0,0.25); padding: 10px; border-radius: var(--radius-md);">
          <div style="font-size: 0.72rem; color: var(--text-muted);">Configured Request</div>
          <div style="font-size: 1.1rem; font-weight: 700; color: #fff;">${lw.cpu_request_m}m / ${lw.mem_request_mib}Mi</div>
          <div style="font-size: 0.72rem; color: var(--text-muted);">${lw.replicas} replicas</div>
        </div>

        <div style="background: rgba(0,0,0,0.25); padding: 10px; border-radius: var(--radius-md);">
          <div style="font-size: 0.72rem; color: var(--text-muted);">Collector Mode</div>
          <div style="font-size: 0.95rem; font-weight: 600; color: #fff;">${lw.metric_source}</div>
          <div style="font-size: 0.72rem; color: var(--text-muted);">${lw.is_container ? "Container" : "Host"}</div>
        </div>
      </div>

      <div style="display: flex; gap: 10px;">
        <button class="btn-primary" onclick="inspectInAdvisor('${lw.id}')">Audit in Advisor</button>
        <button class="btn-secondary" onclick="openPatchModal('${lw.id}')">Generate Safe K8s Patch</button>
      </div>
    `;
  }

  // Render DEMO Workloads
  if (demoContainer && data.demo_workloads) {
    demoContainer.innerHTML = data.demo_workloads.map(dw => {
      return `
        <div class="card" style="border-top: 3px solid var(--amber-demo);">
          <div class="card-header" style="margin-bottom: 8px;">
            <strong style="color: #fff; font-size: 0.92rem;">${dw.name}</strong>
            <span class="badge badge-demo">SIMULATED</span>
          </div>
          <p style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 12px; height: 36px; overflow: hidden;">${dw.description}</p>
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px; font-size: 0.8rem;">
            <div style="background: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px;">
              <span style="color: var(--text-dark);">CPU Peak:</span>
              <strong style="display: block; color: #fff;">${dw.metrics.cpu_peak_m}m</strong>
            </div>
            <div style="background: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px;">
              <span style="color: var(--text-dark);">RAM Peak:</span>
              <strong style="display: block; color: #fff;">${dw.metrics.mem_peak_mib} MiB</strong>
            </div>
          </div>

          <div style="display: flex; gap: 8px;">
            <button class="btn-primary" style="flex: 1; justify-content: center; font-size: 0.75rem;" onclick="inspectInAdvisor('${dw.id}')">Audit</button>
            <button class="btn-secondary" style="flex: 1; font-size: 0.75rem;" onclick="openPatchModal('${dw.id}')">K8s Patch</button>
          </div>
        </div>
      `;
    }).join("");
  }
}

// --------------------------------------------------------------------------
// Intelligent Advisor View
// --------------------------------------------------------------------------
function inspectInAdvisor(workloadId) {
  const sel = document.getElementById("advisor-workload-select");
  if (sel) sel.value = workloadId;
  switchTab("tab-advisor");
  loadAdvisorData(workloadId);
}

async function loadAdvisorData(workloadId) {
  const container = document.getElementById("advisor-content");
  if (!container) return;

  container.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-muted);">Analyzing workload telemetry and safety margins...</div>`;

  try {
    const res = await fetch("/api/audit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workload_id: workloadId,
        grid_region: currentGridRegion
      })
    });
    const audit = await res.json();
    renderAdvisorAudit(audit);
  } catch (err) {
    container.innerHTML = `<div class="alert-box alert-warning">Failed to load audit: ${err.message}</div>`;
  }
}

function renderAdvisorAudit(audit) {
  const container = document.getElementById("advisor-content");
  if (!container) return;

  const rec = audit.recommendation;
  const isOptimal = rec.status === "OPTIMAL";
  const isCritical = rec.status.includes("CRITICAL");
  const statusColor = isOptimal ? "var(--emerald-light)" : (isCritical ? "var(--red-critical)" : "var(--amber-demo)");

  // Update Green Tab values as well
  updateGreenTab(audit);

  container.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.2); padding: 16px; border-radius: var(--radius-md); margin-bottom: 20px;">
      <div>
        <div style="font-size: 0.78rem; color: var(--text-muted); text-transform: uppercase;">Optimization Diagnostic</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: ${statusColor};">${rec.status}</div>
        <div style="font-size: 0.82rem; color: var(--text-muted); margin-top: 2px;">${rec.summary}</div>
      </div>
      <div style="text-align: right;">
        <span class="badge" style="background: rgba(255,255,255,0.08); font-size: 0.8rem; margin-bottom: 4px;">Risk Level: ${rec.risk_level}</span>
        <div style="font-size: 0.75rem; color: var(--text-dark);">Action Required: <strong>${rec.action_required ? "YES" : "NO"}</strong></div>
      </div>
    </div>

    <div class="metrics-grid-3" style="margin-bottom: 20px;">
      <div class="card" style="background: rgba(0,0,0,0.25);">
        <span class="card-title">CPU Right-Sizing</span>
        <div style="display: flex; justify-content: space-between; margin: 12px 0 6px;">
          <span style="color: var(--text-muted);">Current Request:</span>
          <strong>${rec.current_cpu_request_m}m</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
          <span style="color: var(--emerald-light);">Recommended:</span>
          <strong style="color: var(--emerald-light);">${rec.recommended_cpu_request_m}m</strong>
        </div>
        <div style="display: flex; justify-content: space-between;">
          <span style="color: var(--text-dark);">Safety Limit:</span>
          <span>${rec.recommended_cpu_limit_m}m</span>
        </div>
      </div>

      <div class="card" style="background: rgba(0,0,0,0.25);">
        <span class="card-title">Memory Right-Sizing</span>
        <div style="display: flex; justify-content: space-between; margin: 12px 0 6px;">
          <span style="color: var(--text-muted);">Current Request:</span>
          <strong>${rec.current_mem_request_mib} MiB</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
          <span style="color: #93c5fd;">Recommended:</span>
          <strong style="color: #93c5fd;">${rec.recommended_mem_request_mib} MiB</strong>
        </div>
        <div style="display: flex; justify-content: space-between;">
          <span style="color: var(--text-dark);">OOM Safety Limit:</span>
          <span>${rec.recommended_mem_limit_mib} MiB</span>
        </div>
      </div>

      <div class="card" style="background: rgba(0,0,0,0.25);">
        <span class="card-title">Projected Monthly Savings</span>
        <div style="display: flex; justify-content: space-between; margin: 12px 0 6px;">
          <span style="color: var(--text-muted);">Monthly FinOps:</span>
          <strong class="delta-good">Save $${audit.monthly_cost_saved_usd.toFixed(2)} (${audit.cost_savings_pct.toFixed(1)}%)</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
          <span style="color: var(--text-muted);">Carbon Abatement:</span>
          <strong class="delta-good">-${audit.monthly_carbon_saved_kg.toFixed(2)} kg CO2e (${audit.carbon_savings_pct.toFixed(1)}%)</strong>
        </div>
        <div style="display: flex; justify-content: space-between;">
          <span style="color: var(--text-dark);">Replica Tuning:</span>
          <span>${rec.current_replicas} &rarr; ${rec.recommended_replicas} pods</span>
        </div>
      </div>
    </div>

    <div class="card" style="background: rgba(0,0,0,0.2); margin-bottom: 20px;">
      <span class="card-title" style="margin-bottom: 12px; display: block;">Engineering Recommendations & Justification</span>
      <ul style="padding-left: 20px; font-size: 0.88rem; color: #e5e7eb; display: flex; flex-direction: column; gap: 8px;">
        ${rec.tips.map(t => `<li>${t}</li>`).join("")}
      </ul>
    </div>

    <button class="btn-primary" onclick="openPatchModal('${rec.workload_name}')">
      View Safe Kubernetes Patch YAML &rarr;
    </button>
  `;
}

// --------------------------------------------------------------------------
// Green Efficiency Tab Updates
// --------------------------------------------------------------------------
function updateGreenTab(audit) {
  const elWatts = document.getElementById("green-watts-val");
  const elKwh = document.getElementById("green-kwh-val");
  const elIntensity = document.getElementById("green-intensity-val");
  const elTrees = document.getElementById("green-trees-val");
  const elMiles = document.getElementById("green-miles-val");

  if (elWatts) elWatts.textContent = audit.current_carbon.power_watts.toFixed(2);
  if (elKwh) elKwh.textContent = audit.current_carbon.monthly_energy_kwh.toFixed(2);
  if (elIntensity) elIntensity.textContent = audit.current_carbon.carbon_intensity_g_per_kwh;
  if (elTrees) elTrees.textContent = `${audit.current_carbon.trees_offset_equivalent.toFixed(1)} Trees / yr`;
  if (elMiles) elMiles.textContent = `${audit.current_carbon.car_miles_equivalent.toFixed(1)} Miles`;

  // Update Overview Carbon Box as well
  const elOvCarbon = document.getElementById("overview-carbon-val");
  const elOvCost = document.getElementById("overview-cost-val");
  if (elOvCarbon) elOvCarbon.textContent = audit.current_carbon.monthly_carbon_kg.toFixed(2);
  if (elOvCost) elOvCost.textContent = `$${audit.current_cost.monthly_cost_usd.toFixed(2)}`;
}

function initGridRegionSelect() {
  const sel = document.getElementById("grid-region-select");
  if (sel) {
    sel.addEventListener("change", (e) => {
      currentGridRegion = e.target.value;
      const advSel = document.getElementById("advisor-workload-select");
      const currentWorkload = advSel ? advSel.value : "greencloud-live";
      loadAdvisorData(currentWorkload);
    });
  }
}

// --------------------------------------------------------------------------
// Simulation Laboratory
// --------------------------------------------------------------------------
async function runSimulation(multiplierVal) {
  const mult = parseFloat(multiplierVal);
  const badge = document.getElementById("sim-multiplier-badge");
  const burstBadge = document.getElementById("sim-burst-badge");
  if (badge) badge.textContent = `${mult.toFixed(1)}x Load`;
  if (burstBadge) burstBadge.textContent = `${mult.toFixed(1)}x Burst`;

  try {
    const res = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workload_id: "auth-service",
        traffic_multiplier: mult,
        grid_region: currentGridRegion
      })
    });
    const sim = await res.json();
    renderSimulationResults(sim);
  } catch (err) {
    console.error("Simulation error", err);
  }
}

function renderSimulationResults(sim) {
  const bBox = document.getElementById("sim-baseline-box");
  const sBox = document.getElementById("sim-burst-box");
  if (!bBox || !sBox) return;

  const base = sim.baseline_audit;
  const burst = sim.burst_audit;

  bBox.innerHTML = `
    <div>CPU Consumption: <strong>${base.metrics.cpu_used_m.toFixed(1)}m</strong> (Peak: ${base.metrics.cpu_peak_m}m)</div>
    <div>RAM Consumption: <strong>${base.metrics.mem_used_mib.toFixed(1)} MiB</strong></div>
    <div>Power Draw: <strong>${base.current_carbon.power_watts.toFixed(2)} W</strong></div>
    <div>Monthly Carbon: <strong>${base.current_carbon.monthly_carbon_kg.toFixed(2)} kg CO2e</strong></div>
    <div>Status: <span class="delta-good">${base.recommendation.status}</span></div>
  `;

  sBox.innerHTML = `
    <div>CPU Consumption: <strong style="color: var(--amber-demo);">${burst.metrics.cpu_used_m.toFixed(1)}m</strong> (+${sim.delta.cpu_used_increase_m}m)</div>
    <div>RAM Consumption: <strong style="color: var(--amber-demo);">${burst.metrics.mem_used_mib.toFixed(1)} MiB</strong> (+${sim.delta.mem_used_increase_mib}MiB)</div>
    <div>Power Draw: <strong style="color: #fff;">${burst.current_carbon.power_watts.toFixed(2)} W</strong> (+${sim.delta.power_increase_watts} W)</div>
    <div>Monthly Carbon: <strong style="color: #fff;">${burst.current_carbon.monthly_carbon_kg.toFixed(2)} kg CO2e</strong> (+${sim.delta.carbon_increase_kg} kg)</div>
    <div>Dynamic Status: <span style="color: var(--red-critical); font-weight: 700;">${burst.recommendation.status}</span></div>
    <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 4px;">Dynamic Safety Advice: ${burst.recommendation.tips[0] || 'Monitor headroom'}</div>
  `;
}

// --------------------------------------------------------------------------
// System Diagnostics Tab
// --------------------------------------------------------------------------
async function loadSystemInfo() {
  try {
    const res = await fetch("/api/system-info");
    const sys = await res.json();
    const tbody = document.getElementById("system-info-tbody");
    if (!tbody) return;

    tbody.innerHTML = `
      <tr><td>Host Platform</td><td><strong>${sys.platform}</strong></td></tr>
      <tr><td>Python Runtime</td><td>${sys.python_version}</td></tr>
      <tr><td>CPU Cores</td><td>${sys.cpu_count_logical} Logical (${sys.cpu_count_physical} Physical)</td></tr>
      <tr><td>Total System RAM</td><td>${sys.total_memory_gb} GB (${sys.available_memory_gb} GB Available)</td></tr>
      <tr><td>Telemetry Metric Source</td><td><code>${sys.metric_source}</code> (is_container: ${sys.is_container})</td></tr>
      <tr><td>Background Collector</td><td><span class="badge badge-live">RUNNING</span> (#${sys.collector_sample_count} samples)</td></tr>
      <tr><td>System Uptime</td><td>${sys.uptime}</td></tr>
    `;

    const elC2 = document.getElementById("sys-cgroup-v2-status");
    const elC1 = document.getElementById("sys-cgroup-v1-status");
    if (elC2) elC2.innerHTML = sys.cgroup_v2_exists ? `<span style="color: var(--emerald-light);">DETECTED (Linux Kernel)</span>` : `<span style="color: var(--text-dark);">Not Found (Windows/Host Fallback)</span>`;
    if (elC1) elC1.innerHTML = sys.cgroup_v1_exists ? `<span style="color: var(--emerald-light);">DETECTED</span>` : `<span style="color: var(--text-dark);">Not Found</span>`;
  } catch (err) {
    console.error("Failed to load system info", err);
  }
}

// --------------------------------------------------------------------------
// Safe Optimization K8s Patch Modal
// --------------------------------------------------------------------------
async function openPatchModal(workloadId) {
  currentPatchWorkloadId = workloadId || "greencloud-live";
  const modal = document.getElementById("patch-modal");
  const codeBox = document.getElementById("patch-yaml-code");
  const summaryBox = document.getElementById("patch-summary-box");

  if (!modal || !codeBox) return;

  codeBox.textContent = "# Generating declarative optimization patch...";
  modal.classList.add("open");

  try {
    const res = await fetch("/api/audit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workload_id: currentPatchWorkloadId })
    });
    const audit = await res.json();
    const rec = audit.recommendation;

    currentPatchYaml = rec.k8s_patch_yaml;
    codeBox.textContent = rec.k8s_patch_yaml;

    if (summaryBox) {
      summaryBox.innerHTML = `
        <div>Workload: <strong>${rec.workload_name}</strong></div>
        <div>CPU: <strong>${rec.current_cpu_request_m}m &rarr; ${rec.recommended_cpu_request_m}m</strong></div>
        <div>RAM: <strong>${rec.current_mem_request_mib}Mi &rarr; ${rec.recommended_mem_request_mib}Mi</strong></div>
        <div style="color: var(--emerald-light);">Est. Savings: <strong>$${audit.monthly_cost_saved_usd.toFixed(2)}/mo</strong></div>
      `;
    }
  } catch (err) {
    codeBox.textContent = `# Error generating patch: ${err.message}`;
  }
}

function closePatchModal() {
  const modal = document.getElementById("patch-modal");
  if (modal) modal.classList.remove("open");
}

function copyPatchToClipboard() {
  if (!currentPatchYaml) return;
  navigator.clipboard.writeText(currentPatchYaml).then(() => {
    alert("Kubernetes Optimization Patch copied to clipboard!");
  }).catch(() => {
    alert("Please select and copy the text manually.");
  });
}

function downloadPatchYaml() {
  window.location.href = `/api/patch/${currentPatchWorkloadId}`;
}
