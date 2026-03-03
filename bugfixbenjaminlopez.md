What I implemented:

I implemented the multithreaded text-based parking server using threads with shared in-memory state protected by locks. The server supports LOTS, AVAIL, RESERVE, CANCEL, and PING over a newline-delimited TCP protocol. I made sure reservations could not exceed lot capacity under concurrent requests and added lazy expiration for reservation TTL. I also ran load tests and generated throughput and latency graphs from CSV data to evaluate how the server scaled with different worker counts.

One bug fix: 

A major issue occurred during stress testing where the sensor simulator failed with ConnectionRefusedError. The problem was that the server’s sensor port was not running or mismatched with the simulator’s default host/port. I fixed this by explicitly passing --host 127.0.0.1 --port 5002 to the simulator and verifying the port with lsof. I also had to clean up orphaned processes holding ports (Address already in use) using pkill, which prevented the server from restarting properly.

Design Change:

Originally, I considered increasing the thread pool size to improve performance. However, after analyzing the graphs, I observed throughput peaked around 4–8 workers and declined at 16 due to context switching and lock contention. Instead of scaling threads further, I kept the thread pool at a moderate size (16 max) and relied on proper synchronization and async decoupling of sensor updates. This design better reflects the trade-offs discussed in Chapter 3 and keeps the system stable under mixed load.



