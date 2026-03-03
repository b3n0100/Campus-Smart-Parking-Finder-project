import pandas as pd
import matplotlib.pyplot as plt

# Load CSV
df = pd.read_csv("results.csv")

# ---------- AVAIL THROUGHPUT ----------
plt.figure()
avail = df[df["mode"] == "avail"]

for scenario in avail["scenario"].unique():
    subset = avail[avail["scenario"] == scenario].sort_values("workers")
    plt.plot(subset["workers"],
             subset["throughput_rps"],
             marker="o",
             label=scenario)

plt.xlabel("Workers")
plt.ylabel("Throughput (req/s)")
plt.title("AVAIL Throughput vs Workers")
plt.xticks([1,4,8,16])
plt.legend()
plt.tight_layout()
plt.savefig("avail_throughput.png", dpi=200)
plt.close()


# ---------- AVAIL LATENCY ----------
plt.figure()
baseline_avail = avail[avail["scenario"] == "baseline"].sort_values("workers")

plt.plot(baseline_avail["workers"],
         baseline_avail["median_ms"],
         marker="o",
         label="Median (baseline)")

plt.plot(baseline_avail["workers"],
         baseline_avail["p95_ms"],
         marker="o",
         label="P95 (baseline)")

plt.xlabel("Workers")
plt.ylabel("Latency (ms)")
plt.title("AVAIL Latency vs Workers (Baseline)")
plt.xticks([1,4,8,16])
plt.legend()
plt.tight_layout()
plt.savefig("avail_latency.png", dpi=200)
plt.close()


# ---------- RESERVE THROUGHPUT ----------
plt.figure()
reserve = df[df["mode"] == "reserve"]

for scenario in reserve["scenario"].unique():
    subset = reserve[reserve["scenario"] == scenario].sort_values("workers")
    plt.plot(subset["workers"],
             subset["throughput_rps"],
             marker="o",
             label=scenario)

plt.xlabel("Workers")
plt.ylabel("Throughput (req/s)")
plt.title("RESERVE Throughput vs Workers")
plt.legend()
plt.tight_layout()
plt.savefig("reserve_throughput.png", dpi=200)
plt.close()


# ---------- RESERVE LATENCY ----------
plt.figure()
baseline_reserve = reserve[reserve["scenario"] == "baseline"].sort_values("workers")

plt.plot(baseline_reserve["workers"],
         baseline_reserve["median_ms"],
         marker="o",
         label="Median (baseline)")

plt.plot(baseline_reserve["workers"],
         baseline_reserve["p95_ms"],
         marker="o",
         label="P95 (baseline)")

plt.xlabel("Workers")
plt.ylabel("Latency (ms)")
plt.title("RESERVE Latency vs Workers (Baseline)")
plt.legend()
plt.tight_layout()
plt.savefig("reserve_latency.png", dpi=200)
plt.close()

print("Plots saved successfully.")