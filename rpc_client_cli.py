from __future__ import annotations

import argparse
import json
from parking.rpc_client import RpcClient


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5001)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("lots")
    p_av = sub.add_parser("avail")
    p_av.add_argument("lotId")

    p_r = sub.add_parser("reserve")
    p_r.add_argument("lotId")
    p_r.add_argument("plate")

    p_c = sub.add_parser("cancel")
    p_c.add_argument("lotId")
    p_c.add_argument("plate")

    p_s = sub.add_parser("subscribe")
    p_s.add_argument("lotId")

    p_u = sub.add_parser("unsubscribe")
    p_u.add_argument("subId", type=int)

    args = ap.parse_args()
    cli = RpcClient(args.host, args.port)

    if args.cmd == "lots":
        print(json.dumps(cli.getLots(), indent=2))
    elif args.cmd == "avail":
        print(cli.getAvailability(args.lotId))
    elif args.cmd == "reserve":
        rep = cli.reserve(args.lotId, args.plate)
        print(rep)
    elif args.cmd == "cancel":
        rep = cli.cancel(args.lotId, args.plate)
        print(rep)
    elif args.cmd == "subscribe":
        sub_id = cli.subscribe(args.lotId)
        print(sub_id)
    elif args.cmd == "unsubscribe":
        print(cli.unsubscribe(args.subId))


if __name__ == "__main__":
    main()
