from __future__ import annotations

import socket
import threading
import time
from typing import Any, Dict, Optional, List

from .rpc_framing import read_frame, write_frame


class TimeoutError(Exception):
    pass


class RpcClient:
    """Minimal RPC client stub with per-call timeouts."""

    def __init__(self, host: str, port: int, default_timeout: float = 2.0):
        self.host = host
        self.port = int(port)
        self.default_timeout = float(default_timeout)
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._next_id = 1

    def connect(self) -> None:
        if self._sock:
            return
        s = socket.create_connection((self.host, self.port), timeout=self.default_timeout)
        s.settimeout(None)  # we implement timeouts at RPC level
        self._sock = s

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
        self._sock = None

    def call(self, method: str, args: List[Any], timeout: Optional[float] = None) -> Any:
        self.connect()
        assert self._sock is not None
        to = self.default_timeout if timeout is None else float(timeout)

        with self._lock:
            rpc_id = self._next_id
            self._next_id += 1
            write_frame(self._sock, {"rpcId": rpc_id, "method": method, "args": args})

            # Wait for the matching reply (simple single-inflight model).
            # For the assignment, this is enough; can be extended to multiplex if desired.
            end = time.time() + to
            while True:
                remaining = end - time.time()
                if remaining <= 0:
                    raise TimeoutError(f"RPC {method} timed out after {to:.2f}s")
                # implement a timeout on socket read by temporarily setting timeout
                self._sock.settimeout(remaining)
                try:
                    rep = read_frame(self._sock)
                finally:
                    self._sock.settimeout(None)

                if rep.get("rpcId") != rpc_id:
                    # unexpected; ignore
                    continue
                if rep.get("error"):
                    return rep  # allow caller to inspect error string
                return rep.get("result")

    # Convenience methods
    def getLots(self, timeout: Optional[float] = None):
        return self.call("getLots", [], timeout=timeout)

    def getAvailability(self, lot_id: str, timeout: Optional[float] = None) -> int:
        return int(self.call("getAvailability", [lot_id], timeout=timeout))

    def reserve(self, lot_id: str, plate: str, timeout: Optional[float] = None):
        return self.call("reserve", [lot_id, plate], timeout=timeout)

    def cancel(self, lot_id: str, plate: str, timeout: Optional[float] = None):
        return self.call("cancel", [lot_id, plate], timeout=timeout)

    def subscribe(self, lot_id: str, timeout: Optional[float] = None) -> int:
        return int(self.call("subscribe", [lot_id], timeout=timeout))

    def unsubscribe(self, sub_id: int, timeout: Optional[float] = None) -> bool:
        return bool(self.call("unsubscribe", [int(sub_id)], timeout=timeout))
