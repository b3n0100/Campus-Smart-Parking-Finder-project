from __future__ import annotations

import argparse
import random
import socket
import time


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5002)
    ap.add_argument("--lot", required=True, help="Lot id to update")
    ap.add_argument("--rate", type=float, default=10.0, help="Updates per second")
    ap.add_argument("--jitter", type=float, default=0.2, help="Random sleep jitter fraction")
    args = ap.parse_args()

    interval = 1.0 / max(0.1, args.rate)

    with socket.create_connection((args.host, args.port)) as s:
        f = s.makefile("rwb", buffering=0)
        print(f"Sending UPDATE to {args.lot} at ~{args.rate}/sec")
        while True:
            try:
                # random walk: +1 or -1
                delta = random.choice([1, -1])
                f.write(f"UPDATE {args.lot} {delta}\n".encode("utf-8"))
                _ = f.readline()  # OK/ERR
                sleep = interval * random.uniform(1 - args.jitter, 1 + args.jitter)
                time.sleep(max(0.0, sleep))
            except KeyboardInterrupt:
                return


if __name__ == "__main__":
    main()
