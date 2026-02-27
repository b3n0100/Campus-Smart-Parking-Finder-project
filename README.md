# Smart Parking Server (Threads + RPC + Async + Pub/Sub)

This project implements the assignment requirements:
- Multithreaded TCP server (text protocol) and a minimal RPC layer (length-prefixed JSON over TCP).
- Separate sensor update channel (async, queued).
- Publish/subscribe updates delivered over a separate event connection (non-blocking).
- Back-pressure: bounded per-subscriber queue; disconnect subscriber on overflow.
- In-memory state with synchronization; reservations expire after a configurable TTL.

## Architecture (high level)

Ports:
- Text protocol server: `text_port` (default 5000)
- RPC server: `rpc_port` (default 5001)
- Sensor updates: `sensor_port` (default 5002)
- Event stream: `event_port` (default 5003)

Concurrency:
- Each accepted TCP connection is handled by a lightweight thread that reads messages.
- Actual request processing runs in a bounded `ThreadPoolExecutor` (`thread_pool_size`).
- Sensor UPDATEs go into a bounded `update_queue` (back-pressure for sensors: `ERR SATURATED`).
- Pub/sub delivery uses:
  - a global event queue for fan-out,
  - a bounded per-subscriber outbound queue,
  - a per-subscriber sender thread that writes to the subscriber socket.

## Setup (venv)

Create venv:
```bash
python -m venv .venv
```

Activate:
- macOS/Linux:
  ```bash
  source .venv/bin/activate
  ```
- Windows:
  ```powershell
  .venv\Scripts\activate
  ```

Install:
```bash
pip install -r requirements.txt
```
(This project is **stdlib only**, so requirements.txt is intentionally empty.)

## Run the server
```bash
python server_main.py --config config.json
```

## Text protocol client (port 5000)
```bash
python text_client.py --host 127.0.0.1 --port 5000
```

Supported commands:
- `LOTS` -> JSON list of lots `{id, capacity, occupied, free}`
- `AVAIL <lotId>` -> integer free
- `RESERVE <lotId> <plate>` -> `OK | FULL | EXISTS`
- `CANCEL <lotId> <plate>` -> `OK | NOT_FOUND`
- `PING` -> `PONG`

## RPC (port 5001)

### Framing
- 4-byte length prefix, **uint32 big-endian** (`struct.pack("!I", nbytes)`)
- followed by UTF-8 JSON payload bytes

### Wire format
Request:
```json
{ "rpcId": 123, "method": "reserve", "args": ["A", "7ABC123"] }
```
Reply:
```json
{ "rpcId": 123, "result": true, "error": null }
```

Timeout policy:
- Client enforces per-RPC timeout and raises `TimeoutError`.

RPC path (as required):
`Caller → Client Stub → TCP → Server Skeleton → Method → Return → Client Stub → Caller`

### RPC CLI examples
```bash
python rpc_client_cli.py --host 127.0.0.1 --port 5001 lots
python rpc_client_cli.py --host 127.0.0.1 --port 5001 avail A
python rpc_client_cli.py --host 127.0.0.1 --port 5001 reserve A 7ABC123
```

## Sensors (port 5002)
Sensors connect and send:
- `UPDATE <lotId> <delta>` (delta like +1 or -1)

Example simulator (10 updates/sec):
```bash
python sensor_sim.py --host 127.0.0.1 --port 5002 --lot A --rate 10
```

## Pub/Sub (required)

RPC methods:
- `subscribe(lotId) -> subId`
- `unsubscribe(subId) -> bool`

Events:
- `EVENT <lotId> <free> <timestamp_ms>`

**Separate event connection**:
- After `subscribe()`, the client connects to `event_port` and sends:
  - `SUB <subId>\n`
- Server replies `OK` then streams EVENT lines.

Example subscriber:
```bash
python subscriber_client.py --host 127.0.0.1 --rpc-port 5001 --event-port 5003 A
```

Back-pressure policy:
- Each subscriber has a bounded outbound queue (`subscriber_queue_size`).
- If the queue is full, the server disconnects that subscriber to prevent blocking other work.

## Load testing (baseline)
```bash
python load_test.py --host 127.0.0.1 --port 5001 --mode avail --lot A --workers 1 --seconds 30
python load_test.py --host 127.0.0.1 --port 5001 --mode avail --lot A --workers 16 --seconds 30
python load_test.py --host 127.0.0.1 --port 5001 --mode reserve --lot A --workers 16 --seconds 30
```

## Notes / known simplifications
- RPC client supports one in-flight request at a time per `RpcClient` instance (good enough for assignment load tests if you create one client per worker thread).
- Reservation expiration is performed lazily (on access/update of a lot).
