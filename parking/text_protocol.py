from __future__ import annotations

import json
from typing import Tuple, Optional

from .state import ParkingState


def handle_text_command(state: ParkingState, line: str) -> str:
    """Return response string (with trailing \n)."""
    line = line.strip()
    if not line:
        return "ERR EMPTY\n"
    parts = line.split()
    cmd = parts[0].upper()

    try:
        if cmd == "PING":
            return "PONG\n"

        if cmd == "LOTS":
            lots = state.list_lots()
            payload = [
                {"id": x.id, "capacity": x.capacity, "occupied": x.occupied, "free": x.free}
                for x in lots
            ]
            return json.dumps(payload, ensure_ascii=False) + "\n"

        if cmd == "AVAIL":
            if len(parts) != 2:
                return "ERR USAGE AVAIL <lotId>\n"
            free = state.availability(parts[1])
            return f"{free}\n"

        if cmd == "RESERVE":
            if len(parts) != 3:
                return "ERR USAGE RESERVE <lotId> <plate>\n"
            status, free, ts = state.reserve(parts[1], parts[2])
            return f"{status}\n"

        if cmd == "CANCEL":
            if len(parts) != 3:
                return "ERR USAGE CANCEL <lotId> <plate>\n"
            status, free, ts = state.cancel(parts[1], parts[2])
            return f"{status}\n"

        return "ERR UNKNOWN_CMD\n"
    except KeyError:
        return "ERR UNKNOWN_LOT\n"
    except ValueError as e:
        return f"ERR {e}\n"
    except Exception:
        return "ERR INTERNAL\n"
