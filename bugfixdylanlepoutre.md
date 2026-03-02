What I Implemented

I implemented the minimal RPC layer, including length-prefixed framing, JSON request/response formatting, the server skeleton dispatcher, and a client stub with per-call timeouts.

One Bug Fix

A bug I encountered was related to improper message framing. Initially, the server assumed that a single recv() call would return a full RPC message. Under higher concurrency, messages sometimes arrived partially or were combined (TCP sticking), causing JSON decoding errors or mismatched rpcId responses.

I fixed this by implementing strict length-prefixed framing using a 4-byte big-endian header and a helper function that reads exactly the specified number of bytes before decoding the JSON payload. This ensured correct message boundaries and eliminated intermittent parsing failures.

One Design Change

Originally, RPC request handling logic was mixed directly inside the connection loop. I refactored this into a clear separation between the server skeleton (which handles decoding and dispatch) and the shared ParkingState methods. This improved modularity and made it easier to extend the RPC interface without modifying low-level networking code.