from __future__ import annotations

import argparse
import socket


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    args = ap.parse_args()

    with socket.create_connection((args.host, args.port)) as s:
        f = s.makefile("rwb", buffering=0)
        print("Connected. Type commands (LOTS, AVAIL A, RESERVE A PLATE, CANCEL A PLATE, PING). Ctrl+C to exit.")
        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not line:
                continue
            f.write((line + "\n").encode("utf-8"))
            resp = f.readline()
            if not resp:
                print("(disconnected)")
                return
            print(resp.decode("utf-8", errors="replace").rstrip())


if __name__ == "__main__":
    main()
