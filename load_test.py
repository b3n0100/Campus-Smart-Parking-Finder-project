from __future__ import annotations

import argparse
import statistics
import threading
import time
from typing import List, Tuple

from parking.rpc_client import RpcClient, TimeoutError


def worker(host: str, port: int, mode: str, lot_id: str, plate_prefix: str, stop_at: float, out: List[float], err: List[int]) -> None:
    cli = RpcClient(host, port, default_timeout=2.0)
    i = 0
    while time.time() < stop_at:
        t0 = time.perf_counter()
        try:
            if mode == "avail":
                _ = cli.getAvailability(lot_id, timeout=2.0)
            elif mode == "reserve":
                plate = f"{plate_prefix}{i}"
                rep = cli.reserve(lot_id, plate, timeout=2.0)
                # rep can be bool result or dict with error if server returns error
            else:
                raise ValueError("mode must be avail|reserve")
        except Exception:
            err.append(1)
        finally:
            dt = time.perf_counter() - t0
            out.append(dt)
            i += 1


def summarize(samples: List[float]) -> Tuple[float, float]:
    if not samples:
        return 0.0, 0.0
    med = statistics.median(samples)
    p95 = statistics.quantiles(samples, n=20)[18]  # approximate 95th
    return med, p95


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5001, help="RPC port")
    ap.add_argument("--mode", choices=["avail", "reserve"], default="avail")
    ap.add_argument("--lot", default="A")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seconds", type=int, default=30)
    args = ap.parse_args()

    stop_at = time.time() + args.seconds
    threads = []
    samples: List[float] = []
    errors: List[int] = []

    for w in range(args.workers):
        t = threading.Thread(
            target=worker,
            args=(args.host, args.port, args.mode, args.lot, f"W{w}-", stop_at, samples, errors),
            daemon=True,
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    med, p95 = summarize(samples)
    total = len(samples)
    errn = len(errors)
    ok = total - errn
    dur = args.seconds
    throughput = ok / dur if dur > 0 else 0.0
    print(f"mode={args.mode} workers={args.workers} seconds={args.seconds}")
    print(f"requests={total} ok={ok} errors={errn} throughput_ok={throughput:.1f} req/s")
    print(f"latency_median={med*1000:.2f} ms  latency_p95={p95*1000:.2f} ms")


if __name__ == "__main__":
    main()
