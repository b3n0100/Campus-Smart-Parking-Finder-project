from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class LotConfig:
    id: str
    capacity: int


@dataclass(frozen=True)
class ServerConfig:
    # Ports
    text_port: int = 5000
    rpc_port: int = 5001
    sensor_port: int = 5002
    event_port: int = 5003

    # Concurrency & queueing
    thread_pool_size: int = 16
    backlog: int = 128
    update_queue_size: int = 5000

    # Reservations & pub/sub
    reservation_ttl_seconds: int = 300
    subscriber_queue_size: int = 200

    lots: List[LotConfig] = None  # type: ignore


def load_config(path: str | Path) -> ServerConfig:
    """Load JSON config file."""
    p = Path(path)
    data: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))

    lots = [LotConfig(id=str(x["id"]), capacity=int(x["capacity"])) for x in data.get("lots", [])]
    cfg = ServerConfig(
        text_port=int(data.get("text_port", 5000)),
        rpc_port=int(data.get("rpc_port", 5001)),
        sensor_port=int(data.get("sensor_port", 5002)),
        event_port=int(data.get("event_port", 5003)),
        thread_pool_size=int(data.get("thread_pool_size", 16)),
        backlog=int(data.get("backlog", 128)),
        update_queue_size=int(data.get("update_queue_size", 5000)),
        reservation_ttl_seconds=int(data.get("reservation_ttl_seconds", 300)),
        subscriber_queue_size=int(data.get("subscriber_queue_size", 200)),
        lots=lots,
    )
    if not cfg.lots:
        raise ValueError("Config must include at least one lot in 'lots'.")
    return cfg
