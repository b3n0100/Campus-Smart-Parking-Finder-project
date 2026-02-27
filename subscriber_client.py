from __future__ import annotations

import argparse
import socket
from parking.rpc_client import RpcClient


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--rpc-port", type=int, default=5001)
    ap.add_argument("--event-port", type=int, default=5003)
    ap.add_argument("lotId", help="Lot to subscribe to")
    args = ap.parse_args()

    rpc = RpcClient(args.host, args.rpc_port)
    sub_id = rpc.subscribe(args.lotId)
    print(f"subscribed: subId={sub_id}")
    print("Connecting to event stream...")

    with socket.create_connection((args.host, args.event_port)) as s:
        f = s.makefile("rwb", buffering=0)
        f.write(f"SUB {sub_id}\n".encode("utf-8"))
        first = f.readline()
        if not first:
            print("disconnected")
            return
        print(first.decode("utf-8", errors="replace").rstrip())
        print("Listening for EVENT lines. Ctrl+C to exit.")
        try:
            while True:
                line = f.readline()
                if not line:
                    print("(server closed connection)")
                    return
                print(line.decode("utf-8", errors="replace").rstrip())
        except KeyboardInterrupt:
            pass

    # best-effort cleanup
    try:
        rpc.unsubscribe(sub_id)
    except Exception:
        pass


if __name__ == "__main__":
    main()
