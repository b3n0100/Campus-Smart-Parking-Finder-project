## What I Implemented
I implemented the async sensors, pub/sub events, and added portions to help with back pressure. 

## One Bug Fix
A bug I fixed during this project was slow subscribers would block the socket.sendall() call, causing threads to build up and freeze the server. I fixed this by making each subscriber have a cap on how many calls they could make in the queue, as well as making worker threads only enqueue events instead of forcing a run.

## One Design Change
I added a seperate connection just for events instead of mixing it with the RPC connection. This stopped an async event delivery from blocking the RPC request response flow.