from __future__ import annotations

import argparse
import logging
import queue
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple

from parking.config import load_config
from parking.state import ParkingState
from parking.pubsub import PubSubHub
from parking.text_protocol import handle_text_command
from parking.rpc_framing import read_frame, write_frame, FramingError
from parking.rpc_server import handle_rpc_request


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("parking-server")


def serve_text(state: ParkingState, host: str, port: int, executor: ThreadPoolExecutor, backlog: int) -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(backlog)
    log.info(f"text server listening on {host}:{port}")

    def client_thread(conn: socket.socket, addr: Tuple[str, int]) -> None:
        with conn:
            f = conn.makefile("rwb", buffering=0)
            while True:
                line = f.readline()
                if not line:
                    return
                try:
                    text = line.decode("utf-8", errors="replace")
                except Exception:
                    f.write(b"ERR BAD_ENCODING\n")
                    continue
                fut = executor.submit(handle_text_command, state, text)
                resp = fut.result()
                f.write(resp.encode("utf-8"))

    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=client_thread, args=(conn, addr), daemon=True)
        t.start()


def serve_rpc(state: ParkingState, hub: PubSubHub, host: str, port: int, executor: ThreadPoolExecutor, backlog: int) -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(backlog)
    log.info(f"rpc server listening on {host}:{port}")

    def client_thread(conn: socket.socket, addr: Tuple[str, int]) -> None:
        with conn:
            while True:
                try:
                    req = read_frame(conn)
                except EOFError:
                    return
                except FramingError as e:
                    try:
                        write_frame(conn, {"rpcId": None, "result": None, "error": f"FramingError: {e}"})
                    except Exception:
                        pass
                    return
                except Exception as e:
                    return

                fut = executor.submit(handle_rpc_request, state, hub, req)
                rep = fut.result()
                try:
                    write_frame(conn, rep)
                except Exception:
                    return

    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=client_thread, args=(conn, addr), daemon=True)
        t.start()


def serve_sensors(state: ParkingState, update_q: "queue.Queue[Tuple[str,int]]", host: str, port: int, backlog: int) -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(backlog)
    log.info(f"sensor server listening on {host}:{port}")

    def client_thread(conn: socket.socket, addr: Tuple[str, int]) -> None:
        with conn:
            f = conn.makefile("rwb", buffering=0)
            while True:
                line = f.readline()
                if not line:
                    return
                text = line.decode("utf-8", errors="replace").strip()
                parts = text.split()
                if len(parts) != 3 or parts[0].upper() != "UPDATE":
                    f.write(b"ERR USAGE UPDATE <lotId> <delta>\n")
                    continue
                lot_id = parts[1]
                try:
                    delta = int(parts[2])
                except Exception:
                    f.write(b"ERR DELTA\n")
                    continue
                try:
                    update_q.put((lot_id, delta), timeout=0.25)
                    f.write(b"OK\n")
                except queue.Full:
                    f.write(b"ERR SATURATED\n")

    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=client_thread, args=(conn, addr), daemon=True)
        t.start()


def update_dispatcher(state: ParkingState, update_q: "queue.Queue[Tuple[str,int]]", executor: ThreadPoolExecutor) -> None:
    while True:
        lot_id, delta = update_q.get()
        # Apply updates in the thread pool
        executor.submit(state.apply_update, lot_id, delta)


def serve_events(hub: PubSubHub, host: str, port: int, backlog: int) -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(backlog)
    log.info(f"event server listening on {host}:{port}")

    def client_thread(conn: socket.socket, addr: Tuple[str, int]) -> None:
        # Expected first line: SUB <subId>
        with conn:
            f = conn.makefile("rwb", buffering=0)
            line = f.readline()
            if not line:
                return
            text = line.decode("utf-8", errors="replace").strip()
            parts = text.split()
            if len(parts) != 2 or parts[0].upper() != "SUB":
                f.write(b"ERR USAGE SUB <subId>\n")
                return
            try:
                sub_id = int(parts[1])
            except Exception:
                f.write(b"ERR subId\n")
                return
            ok = hub.attach_socket(sub_id, conn)
            if not ok:
                f.write(b"ERR UNKNOWN_SUB\n")
                return
            f.write(b"OK\n")
            # After this, hub sender thread owns sending; keep connection open until closed.
            while True:
                # keepalive read to detect disconnect? not required; just wait.
                b = f.readline()
                if not b:
                    return

    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=client_thread, args=(conn, addr), daemon=True)
        t.start()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json", help="Path to JSON config")
    ap.add_argument("--host", default="0.0.0.0")
    args = ap.parse_args()

    cfg = load_config(args.config)
    lots = {lc.id: lc.capacity for lc in cfg.lots}

    hub = PubSubHub(subscriber_queue_size=cfg.subscriber_queue_size)
    state = ParkingState(lots=lots, reservation_ttl_seconds=cfg.reservation_ttl_seconds)
    state.set_on_change(hub.publish)

    executor = ThreadPoolExecutor(max_workers=cfg.thread_pool_size)
    update_q: "queue.Queue[Tuple[str,int]]" = queue.Queue(maxsize=cfg.update_queue_size)

    # Threads
    threading.Thread(target=serve_text, args=(state, args.host, cfg.text_port, executor, cfg.backlog), daemon=True).start()
    threading.Thread(target=serve_rpc, args=(state, hub, args.host, cfg.rpc_port, executor, cfg.backlog), daemon=True).start()
    threading.Thread(target=serve_sensors, args=(state, update_q, args.host, cfg.sensor_port, cfg.backlog), daemon=True).start()
    threading.Thread(target=serve_events, args=(hub, args.host, cfg.event_port, cfg.backlog), daemon=True).start()
    threading.Thread(target=update_dispatcher, args=(state, update_q, executor), daemon=True).start()

    log.info("server started")
    # block forever
    threading.Event().wait()


if __name__ == "__main__":
    main()
