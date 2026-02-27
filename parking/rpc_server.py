from __future__ import annotations

from typing import Any, Dict, List

from .state import ParkingState
from .pubsub import PubSubHub


def handle_rpc_request(state: ParkingState, hub: PubSubHub, req: Dict[str, Any]) -> Dict[str, Any]:
    """RPC skeleton: dispatch request -> state/hub -> reply."""
    rpc_id = req.get("rpcId")
    method = req.get("method")
    args = req.get("args", [])

    reply: Dict[str, Any] = {"rpcId": rpc_id, "result": None, "error": None}

    try:
        if not isinstance(rpc_id, int):
            raise ValueError("rpcId must be int")
        if not isinstance(method, str):
            raise ValueError("method must be str")
        if not isinstance(args, list):
            raise ValueError("args must be list")

        if method == "getLots":
            lots = state.list_lots()
            reply["result"] = [
                {"id": x.id, "capacity": x.capacity, "occupied": x.occupied, "free": x.free}
                for x in lots
            ]
            return reply

        if method == "getAvailability":
            lot_id = str(args[0])
            reply["result"] = int(state.availability(lot_id))
            return reply

        if method == "reserve":
            lot_id = str(args[0])
            plate = str(args[1])
            status, free, ts = state.reserve(lot_id, plate)
            reply["result"] = (status == "OK")
            reply["error"] = None if status == "OK" else status
            return reply

        if method == "cancel":
            lot_id = str(args[0])
            plate = str(args[1])
            status, free, ts = state.cancel(lot_id, plate)
            reply["result"] = (status == "OK")
            reply["error"] = None if status == "OK" else status
            return reply

        if method == "subscribe":
            lot_id = str(args[0])
            sub_id = hub.subscribe(lot_id)
            reply["result"] = int(sub_id)
            return reply

        if method == "unsubscribe":
            sub_id = int(args[0])
            reply["result"] = bool(hub.unsubscribe(sub_id))
            return reply

        raise ValueError(f"Unknown method: {method}")

    except Exception as e:
        reply["error"] = str(e)
        reply["result"] = None
        return reply
