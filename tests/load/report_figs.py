"""Turn the VPS load-test output (bench.json, load.json, stats.txt, host.txt) into figures + a summary.

    python tests/load/report_figs.py <dir with the results>
Writes docs/figs/load_*.png and <dir>/summary.json. Nothing is estimated: every number is read from the files.
"""
import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

SRC = Path(sys.argv[1])
FIGS = Path(__file__).resolve().parents[2] / "docs" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)
GREEN, DARK, MUTED, LINE, BLUE, ORANGE, RED = "#2e7d4f", "#1b3a2a", "#5f6b64", "#dfe7e2", "#2a78d6", "#eb6834", "#c0392b"
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MUTED})

bench = json.loads((SRC / "bench.json").read_text())
load = json.loads((SRC / "load.json").read_text())
host = dict(l.split(": ", 1) for l in (SRC / "host.txt").read_text().splitlines() if ": " in l)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIGS / name, dpi=200)
    plt.close(fig)


def mem_mib(s):
    v, u = re.match(r"([\d.]+)\s*([KMG]i?B)", s).groups()
    return float(v) * {"KiB": 1 / 1024, "MiB": 1, "GiB": 1024, "kB": 1 / 1000, "MB": 1, "GB": 1000}.get(u, 1)


stats = []
for line in (SRC / "stats.txt").read_text().splitlines():
    m = re.match(r"([\d.]+)\s+([\d.]+)%\s+(\S+)", line)
    if m:
        stats.append((float(m.group(1)), float(m.group(2)), mem_mib(m.group(3))))

# ---------------- 1. setup diagram
fig, ax = plt.subplots(figsize=(8, 3.3)); ax.set_xlim(0, 100); ax.set_ylim(0, 42); ax.axis("off")


def box(x, y, w, h, title, sub, fc="#eef6f0", ec=GREEN):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.5", fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h - 3, title, ha="center", va="top", weight="bold", fontsize=8.5, color=DARK)
    ax.text(x + w / 2, y + h - 7.5, sub, ha="center", va="top", fontsize=7.2, color=MUTED, linespacing=1.4)


ax.add_patch(FancyBboxPatch((1, 1), 98, 40, boxstyle="round,pad=0.2,rounding_size=2", fc="white", ec=LINE, lw=1))
ax.text(3, 38.5, f"Production VPS: {host.get('vcpus', '?')} vCPU ({host.get('cpu', '').replace(' 32-Core Processor', '')}), 8 GB RAM, shared with other services",
        fontsize=7.5, color=MUTED)
box(4, 8, 25, 24, "Load generator", "loadtest.py (asyncio + httpx)\nvirtual users, 1 s think time\nlimited to 0.5 CPU", "#fff7ec", ORANGE)
box(38, 8, 27, 24, "Test server (copy)", "same image as live\n2 Uvicorn workers, 1.2 GB\nown empty SQLite, no OTP")
box(73, 21, 23, 11, "Live AgriSense", "untouched", "#f4f6f5", MUTED)
box(73, 6, 23, 11, "docker stats", "CPU % and memory\nabout every second", "#f4f6f5", BLUE)
ax.annotate("", xy=(38, 20), xytext=(29.5, 20), arrowprops=dict(arrowstyle="->", color=DARK, lw=1.3))
ax.text(33.7, 22, "HTTP\n127.0.0.1", ha="center", fontsize=7, color=DARK)
ax.annotate("", xy=(65.5, 12), xytext=(73, 12), arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.1, ls="--"))
save(fig, "load_setup.png")

# ---------------- 2. model benchmark
names = [("crop_recommendation", "Crop (Random Forest)"), ("yield_prediction", "Yield (LightGBM)"),
         ("fertiliser", "Fertiliser (Log. Regression)"), ("leaf_disease", "Leaf disease (CNN, ONNX)")]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(8, 2.8))
y = range(len(names))
a1.barh(y, [bench[k]["mean_ms"] for k, _ in names], color=GREEN)
a1.barh(y, [bench[k]["p95_ms"] - bench[k]["mean_ms"] for k, _ in names], left=[bench[k]["mean_ms"] for k, _ in names], color="#9cc9ad")
a1.set_yticks(list(y), [l for _, l in names]); a1.invert_yaxis(); a1.set_xlabel("ms per prediction (dark: mean, light: up to p95)")
for i, (k, _) in enumerate(names):
    a1.text(bench[k]["p95_ms"] + 1, i, f"{bench[k]['mean_ms']:.1f} ms", va="center", fontsize=7)
a2.barh(y, [bench[k]["per_second_one_core"] for k, _ in names], color=BLUE)
a2.set_yticks(list(y), ["" for _ in names]); a2.invert_yaxis(); a2.set_xscale("log"); a2.set_xlabel("predictions per second, one core (log scale)")
for i, (k, _) in enumerate(names):
    a2.text(bench[k]["per_second_one_core"] * 1.1, i, f"{bench[k]['per_second_one_core']:,.0f}", va="center", fontsize=7)
save(fig, "load_models.png")

# ---------------- 3. endpoints: latency alone vs throughput
eps = list(load["baseline"])
short = [e.replace("GET ", "").replace("POST ", "").replace("/api/", "") for e in eps]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(8, 3))
x = range(len(eps))
a1.bar([i - 0.2 for i in x], [load["baseline"][e]["p50_ms"] for e in eps], 0.4, color=GREEN, label="one request at a time (p50)")
a1.bar([i + 0.2 for i in x], [load["throughput"][e]["p95_ms"] for e in eps], 0.4, color=ORANGE, label="8 clients, no pause (p95)")
a1.set_xticks(list(x), short, rotation=35, ha="right"); a1.set_ylabel("response time (ms)"); a1.legend(fontsize=7, frameon=False)
a2.bar(list(x), [load["throughput"][e]["rps"] for e in eps], color=BLUE)
a2.set_xticks(list(x), short, rotation=35, ha="right"); a2.set_ylabel("requests per second (8 clients)")
for i, e in enumerate(eps):
    a2.text(i, load["throughput"][e]["rps"] * 1.02, f"{load['throughput'][e]['rps']:.0f}", ha="center", fontsize=7)
save(fig, "load_endpoints.png")

# ---------------- 4. step test
st = load["step"]
fig, a1 = plt.subplots(figsize=(8, 3.2))
u = [s["users"] for s in st]
a1.bar([str(v) for v in u], [s["rps"] for s in st], color="#cfe8d7", label="requests per second")
a1.set_xlabel("simultaneous users (each pauses about 1 s between requests)"); a1.set_ylabel("requests per second")
a2 = a1.twinx(); a2.spines["right"].set_visible(True)
a2.plot([str(v) for v in u], [s["p50_ms"] for s in st], "o-", color=GREEN, label="median response")
a2.plot([str(v) for v in u], [s["p95_ms"] for s in st], "s-", color=ORANGE, label="95th percentile")
a2.axhline(2000, color=RED, ls="--", lw=1); a2.text(len(u) - 0.5, 2050, "2 s target (NFR-07)", color=RED, fontsize=7, ha="right", va="bottom")
a2.set_ylabel("response time (ms)")
h1, l1 = a1.get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
a1.legend(h1 + h2, l1 + l2, fontsize=7, frameon=False, loc="upper left")
save(fig, "load_step.png")

# ---------------- 5. resources during the step test
if stats and st:
    t0 = st[0]["t_start"] - 5
    s_in = [s for s in stats if t0 <= s[0] <= st[-1]["t_end"] + 5]
    fig, a1 = plt.subplots(figsize=(8, 2.8))
    a1.plot([s[0] - t0 for s in s_in], [s[1] for s in s_in], color=ORANGE, lw=1.2, label="CPU % (200% = both vCPUs)")
    a1.set_ylabel("CPU %"); a1.set_xlabel("seconds into the step test"); a1.set_ylim(0, max(210, max(s[1] for s in s_in) * 1.1))
    for s in st:
        a1.axvspan(s["t_start"] - t0, s["t_end"] - t0, color="#eef6f0", zorder=0)
        a1.text((s["t_start"] + s["t_end"]) / 2 - t0, a1.get_ylim()[1] * 0.93, f"{s['users']}", ha="center", fontsize=7, color=GREEN)
    a2 = a1.twinx(); a2.spines["right"].set_visible(True)
    a2.plot([s[0] - t0 for s in s_in], [s[2] for s in s_in], color=BLUE, lw=1.2, label="memory (MiB)")
    a2.set_ylabel("memory (MiB, limit 1,200)"); a2.set_ylim(0, 1250)
    h1, l1 = a1.get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
    a1.legend(h1 + h2, l1 + l2, fontsize=7, frameon=False, loc="lower right")
    save(fig, "load_resources.png")

# ---------------- 6. spike
sp = load["spike"]
ev = sp["events"]
end = int(max(e[0] for e in ev)) + 1
per = [[] for _ in range(end + 1)]
for t, l, ok in ev:
    per[int(t)].append((l, ok))
sec = list(range(end + 1))
fig, a1 = plt.subplots(figsize=(8, 2.9))
a1.bar(sec, [len(p) for p in per], color="#cfe8d7", width=1.0, label="requests completed per second")
a1.bar(sec, [sum(1 for _, ok in p if not ok) for p in per], color=RED, width=1.0, label="failed")
a1.set_xlabel("seconds"); a1.set_ylabel("requests per second")
a2 = a1.twinx(); a2.spines["right"].set_visible(True)
p95 = [sorted(l for l, ok in p if ok)[int(len([1 for _, ok in p if ok]) * 0.95) - 1] if sum(1 for _, ok in p if ok) else None for p in per]
a2.plot([s for s, v in zip(sec, p95) if v is not None], [v for v in p95 if v is not None], color=ORANGE, lw=1.3, label="95th percentile (ms)")
a2.set_ylabel("response time (ms)")
for name, a, b in sp["phases"]:
    a1.axvline(a, color=MUTED, lw=0.6, ls=":")
    a1.text((a + b) / 2, a1.get_ylim()[1] * 0.95, name, ha="center", fontsize=7.5, color=DARK)
h1, l1 = a1.get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
a1.legend(h1 + h2, l1 + l2, fontsize=7, frameon=False, loc="center left")
save(fig, "load_spike.png")

# ---------------- summary numbers for the report
ok_steps = [s for s in st if (s["p95_ms"] or 1e9) <= 2000 and s["error_rate"] < 0.01]
spike_ev = [(t, l, ok) for t, l, ok in ev if sp["phases"][1][1] <= t < sp["phases"][1][2]]
after = [(t, l, ok) for t, l, ok in ev if t >= sp["phases"][2][1] + 5]
lat_spike = sorted(l for _, l, ok in spike_ev if ok)
lat_after = sorted(l for _, l, ok in after if ok)
summary = {
    "host": host, "bench": bench,
    "capacity_users_p95_under_2s": ok_steps[-1]["users"] if ok_steps else 0,
    "capacity_rps_at_that_point": ok_steps[-1]["rps"] if ok_steps else 0,
    "max_users_tested": st[-1]["users"], "step": st,
    "peak_cpu_percent": max((s[1] for s in stats), default=None),
    "peak_mem_mib": round(max((s[2] for s in stats), default=0), 1),
    "spike": {"requests": len(spike_ev), "errors": sum(1 for *_, ok in spike_ev if not ok),
              "p95_ms": lat_spike[int(len(lat_spike) * 0.95) - 1] if lat_spike else None,
              "after_p95_ms": lat_after[int(len(lat_after) * 0.95) - 1] if lat_after else None},
    "baseline": load["baseline"], "throughput": load["throughput"],
    "total_requests": sum(v["requests"] for v in load["baseline"].values()) + sum(v["requests"] for v in load["throughput"].values())
    + sum(s["requests"] for s in st) + len(ev),
    "total_errors": sum(v["errors"] for v in load["baseline"].values()) + sum(v["errors"] for v in load["throughput"].values())
    + sum(s["errors"] for s in st) + sum(1 for *_, ok in ev if not ok),
}
(SRC / "summary.json").write_text(json.dumps(summary, indent=1))
print(json.dumps({k: summary[k] for k in ("capacity_users_p95_under_2s", "capacity_rps_at_that_point", "max_users_tested",
                                          "peak_cpu_percent", "peak_mem_mib", "spike", "total_requests", "total_errors")}, indent=1))
