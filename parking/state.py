from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Tuple


@dataclass
class LotSnapshot:
    id: str
    capacity: int
    occupied: int
    free: int


class ParkingState:
    """Thread-safe in-memory state for parking lots and reservations.

    Policy:
    - A RESERVE immediately consumes a space (occupied += 1) until cancelled or expired.
    - CANCEL frees the space (occupied -= 1).
    - UPDATE <delta> adjusts occupied, clamped to [0, capacity].
    """

    def __init__(self, lots: Dict[str, int], reservation_ttl_seconds: int):
        self._lock = threading.Lock()
        self._ttl = int(reservation_ttl_seconds)

        self._capacity: Dict[str, int] = dict(lots)
        self._occupied: Dict[str, int] = {lot_id: 0 for lot_id in lots.keys()}
        # reservations[lotId][plate] = expires_at_epoch_seconds
        self._reservations: Dict[str, Dict[str, float]] = {lot_id: {} for lot_id in lots.keys()}

        # Called after free changes: (lotId, free, timestamp_ms)
        self._on_change: Optional[Callable[[str, int, int], None]] = None

    def set_on_change(self, cb: Callable[[str, int, int], None]) -> None:
        self._on_change = cb

    def _now(self) -> float:
        return time.time()

    def _ts_ms(self) -> int:
        return int(self._now() * 1000)

    def _expire_locked(self, lot_id: str) -> bool:
        """Expire reservations for lot_id. Returns True if free changed."""
        now = self._now()
        res = self._reservations[lot_id]
        if not res:
            return False
        expired = [plate for plate, exp in res.items() if exp <= now]
        if not expired:
            return False
        for plate in expired:
            del res[plate]
            # freeing a reservation frees a space
            self._occupied[lot_id] = max(0, self._occupied[lot_id] - 1)
        return True

    def _free_locked(self, lot_id: str) -> int:
        return max(0, self._capacity[lot_id] - self._occupied[lot_id])

    def list_lots(self) -> List[LotSnapshot]:
        with self._lock:
            changed_any = False
            for lot_id in self._capacity.keys():
                if self._expire_locked(lot_id):
                    changed_any = True
            # If expiration changed, we don't publish here to keep list_lots read-only-ish.
            return [
                LotSnapshot(
                    id=lot_id,
                    capacity=self._capacity[lot_id],
                    occupied=self._occupied[lot_id],
                    free=self._free_locked(lot_id),
                )
                for lot_id in sorted(self._capacity.keys())
            ]

    def availability(self, lot_id: str) -> int:
        with self._lock:
            self._require_lot(lot_id)
            self._expire_locked(lot_id)
            return self._free_locked(lot_id)

    def reserve(self, lot_id: str, plate: str) -> Tuple[str, int, int]:
        """Returns (status, free, timestamp_ms). status: OK|FULL|EXISTS"""
        plate = plate.strip()
        if not plate:
            raise ValueError("plate must be non-empty")
        with self._lock:
            self._require_lot(lot_id)
            changed = self._expire_locked(lot_id)

            res = self._reservations[lot_id]
            if plate in res:
                free = self._free_locked(lot_id)
                return "EXISTS", free, self._ts_ms()

            if self._occupied[lot_id] >= self._capacity[lot_id]:
                free = self._free_locked(lot_id)
                return "FULL", free, self._ts_ms()

            # consume a space
            self._occupied[lot_id] += 1
            res[plate] = self._now() + self._ttl
            free = self._free_locked(lot_id)
            ts = self._ts_ms()

        # Publish change outside lock
        if self._on_change:
            self._on_change(lot_id, free, ts)
        return "OK", free, ts

    def cancel(self, lot_id: str, plate: str) -> Tuple[str, int, int]:
        """Returns (status, free, timestamp_ms). status: OK|NOT_FOUND"""
        plate = plate.strip()
        if not plate:
            raise ValueError("plate must be non-empty")
        with self._lock:
            self._require_lot(lot_id)
            changed = self._expire_locked(lot_id)

            res = self._reservations[lot_id]
            if plate not in res:
                free = self._free_locked(lot_id)
                return "NOT_FOUND", free, self._ts_ms()

            del res[plate]
            self._occupied[lot_id] = max(0, self._occupied[lot_id] - 1)
            free = self._free_locked(lot_id)
            ts = self._ts_ms()

        if self._on_change:
            self._on_change(lot_id, free, ts)
        return "OK", free, ts

    def apply_update(self, lot_id: str, delta: int) -> Tuple[int, int]:
        """Apply sensor delta to occupied and return (free, timestamp_ms)."""
        with self._lock:
            self._require_lot(lot_id)
            self._expire_locked(lot_id)

            occ = self._occupied[lot_id] + int(delta)
            occ = min(max(0, occ), self._capacity[lot_id])
            self._occupied[lot_id] = occ
            free = self._free_locked(lot_id)
            ts = self._ts_ms()

        if self._on_change:
            self._on_change(lot_id, free, ts)
        return free, ts

    def _require_lot(self, lot_id: str) -> None:
        if lot_id not in self._capacity:
            raise KeyError(f"Unknown lotId: {lot_id}")
