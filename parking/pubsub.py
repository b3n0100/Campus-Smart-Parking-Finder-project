from __future__ import annotations

import queue
import socket
import threading
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class Subscriber:
    sub_id: int
    lot_id: str
    out_q: "queue.Queue[str]"
    sock: Optional[socket.socket] = None
    sender_thread: Optional[threading.Thread] = None
    alive: bool = True


class PubSubHub:
    """Pub/sub registry + non-blocking fan-out + back-pressure.

    Delivery approach:
    - Separate TCP connection for events (event server).
    - subscribe() via RPC returns subId.
    - client connects to event port and sends: SUB <subId>\n
    - server attaches socket to the subscription and starts a sender thread
      that drains a bounded per-subscriber queue and writes events.

    Back-pressure policy:
    - bounded per-subscriber queue; if enqueue fails (queue full), disconnect subscriber.
    """

    def __init__(self, subscriber_queue_size: int = 200):
        self._lock = threading.Lock()
        self._next_id = 1
        self._subs: Dict[int, Subscriber] = {}
        self._subscriber_queue_size = int(subscriber_queue_size)

        # Global event queue for fan-out (lot_id, event_line)
        self._event_q: "queue.Queue[Tuple[str, str]]" = queue.Queue()
        self._notifier_thread = threading.Thread(target=self._notifier_loop, name="notifier", daemon=True)
        self._notifier_thread.start()

    def subscribe(self, lot_id: str) -> int:
        with self._lock:
            sub_id = self._next_id
            self._next_id += 1
            sub = Subscriber(sub_id=sub_id, lot_id=lot_id, out_q=queue.Queue(maxsize=self._subscriber_queue_size))
            self._subs[sub_id] = sub
            return sub_id

    def unsubscribe(self, sub_id: int) -> bool:
        sub = None
        with self._lock:
            sub = self._subs.pop(int(sub_id), None)
        if not sub:
            return False
        self._disconnect(sub)
        return True

    def attach_socket(self, sub_id: int, sock: socket.socket) -> bool:
        """Attach an event socket to an existing subscription."""
        with self._lock:
            sub = self._subs.get(int(sub_id))
            if not sub or not sub.alive:
                return False
            # Replace any previous socket
            if sub.sock:
                try:
                    sub.sock.close()
                except Exception:
                    pass
            sub.sock = sock

            # Start sender thread if not running
            if not sub.sender_thread or not sub.sender_thread.is_alive():
                t = threading.Thread(target=self._sender_loop, args=(sub.sub_id,), name=f"sender-{sub.sub_id}", daemon=True)
                sub.sender_thread = t
                t.start()
            return True

    def publish(self, lot_id: str, free: int, ts_ms: int) -> None:
        event_line = f"EVENT {lot_id} {free} {ts_ms}\n"
        self._event_q.put((lot_id, event_line))

    def _notifier_loop(self) -> None:
        while True:
            lot_id, event_line = self._event_q.get()
            # Snapshot current subscribers to that lot
            with self._lock:
                targets = [s for s in self._subs.values() if s.alive and s.lot_id == lot_id]
            for sub in targets:
                # Non-blocking enqueue
                try:
                    sub.out_q.put_nowait(event_line)
                except queue.Full:
                    # back-pressure: disconnect slow subscriber
                    self._disconnect(sub)

    def _sender_loop(self, sub_id: int) -> None:
        while True:
            with self._lock:
                sub = self._subs.get(int(sub_id))
                if not sub or not sub.alive:
                    return
                sock = sub.sock
            if sock is None:
                # wait for attachment
                # small sleep-less wait via blocking get with timeout on queue is messy; just loop lightly
                try:
                    item = sub.out_q.get(timeout=0.25)
                    # If no socket yet, drop the item to avoid unbounded waiting; newest state will arrive soon.
                    continue
                except queue.Empty:
                    continue
            try:
                line = sub.out_q.get()
                sock.sendall(line.encode("utf-8"))
            except Exception:
                with self._lock:
                    sub2 = self._subs.get(int(sub_id))
                if sub2:
                    self._disconnect(sub2)
                return

    def _disconnect(self, sub: Subscriber) -> None:
        with self._lock:
            if not sub.alive:
                return
            sub.alive = False
        try:
            if sub.sock:
                sub.sock.close()
        except Exception:
            pass
