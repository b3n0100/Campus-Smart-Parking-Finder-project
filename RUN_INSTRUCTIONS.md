# Running the Smart Parking Server

## 1. Setup Virtual Environment

From inside the project directory:

### Create venv

``` bash
python -m venv .venv
```

### Activate

**macOS / Linux**

``` bash
source .venv/bin/activate
```

**Windows (PowerShell)**

``` powershell
.venv\Scripts\activate
```

------------------------------------------------------------------------

## 2. Install Dependencies

This project uses only the Python standard library.

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

## 3. Start the Server

``` bash
python server_main.py --config config.json
```

You should see:

    text server listening on 0.0.0.0:5000
    rpc server listening on 0.0.0.0:5001
    sensor server listening on 0.0.0.0:5002
    event server listening on 0.0.0.0:5003
    server started

Leave this terminal running.

------------------------------------------------------------------------

# Testing the System

Open **new terminals** for each test below.

------------------------------------------------------------------------

## Test 1 --- Text Protocol Client

``` bash
python text_client.py
```

Try:

    LOTS
    AVAIL A
    RESERVE A CAR1
    CANCEL A CAR1
    PING

------------------------------------------------------------------------

## Test 2 --- RPC Client

List lots:

``` bash
python rpc_client_cli.py lots
```

Check availability:

``` bash
python rpc_client_cli.py avail A
```

Reserve:

``` bash
python rpc_client_cli.py reserve A CAR1
```

Cancel:

``` bash
python rpc_client_cli.py cancel A CAR1
```

------------------------------------------------------------------------

## Test 3 --- Pub/Sub (Event Streaming)

### Step 1: Start Subscriber

``` bash
python subscriber_client.py A
```

### Step 2: Trigger Changes

In another terminal:

``` bash
python rpc_client_cli.py reserve A TEST1
```

You should see:

    EVENT A <free> <timestamp>

------------------------------------------------------------------------

## Test 4 --- Sensor Simulator (Async Updates)

Simulate 10 updates per second:

``` bash
python sensor_sim.py --lot A --rate 10
```

Subscribers will begin receiving frequent `EVENT` messages.

------------------------------------------------------------------------

## Test 5 --- Load Testing

Availability benchmark:

``` bash
python load_test.py --mode avail --workers 4 --seconds 30
```

Reserve benchmark:

``` bash
python load_test.py --mode reserve --workers 16 --seconds 30
```
