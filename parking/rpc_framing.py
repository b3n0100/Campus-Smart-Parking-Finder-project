from __future__ import annotations

import json
import socket
import struct
from typing import Any, Dict


class FramingError(Exception):
    pass


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise EOFError("socket closed")
        buf.extend(chunk)
    return bytes(buf)


def read_frame(sock: socket.socket, max_size: int = 2_000_000) -> Dict[str, Any]:
    """Read one length-prefixed JSON frame."""
    header = _recv_exact(sock, 4)
    (length,) = struct.unpack("!I", header)  # big-endian uint32
    if length <= 0 or length > max_size:
        raise FramingError(f"Invalid frame length: {length}")
    payload = _recv_exact(sock, length)
    try:
        obj = json.loads(payload.decode("utf-8"))
    except Exception as e:
        raise FramingError(f"Invalid JSON payload: {e}") from e
    if not isinstance(obj, dict):
        raise FramingError("Frame payload must be a JSON object")
    return obj


def write_frame(sock: socket.socket, obj: Dict[str, Any]) -> None:
    payload = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    header = struct.pack("!I", len(payload))
    sock.sendall(header + payload)
