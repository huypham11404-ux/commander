import asyncio
import json
import os
import time
import tempfile
import statistics
import websockets
import socket
import threading
from typing import Dict, List, Any

# Parameters
WARMUP_OPS = 100
BENCHMARK_OPS = 1000

# 1. FILE-BASED ATOMIC SWAP BENCHMARK (With Warmup & Detailed Percentiles)
def benchmark_file_ipc_rigorous(warmup: int, n_ops: int) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd_file = os.path.join(tmpdir, "command.json")
        resp_file = os.path.join(tmpdir, "response.json")
        cmd_tmp = os.path.join(tmpdir, "command.tmp")

        # Warmup (not recorded)
        for i in range(warmup):
            with open(cmd_tmp, "w", encoding="utf-8") as f:
                f.write(json.dumps({"action": "warmup", "id": i}))
            os.replace(cmd_tmp, cmd_file)
            with open(cmd_file, "r", encoding="utf-8") as f:
                d = json.loads(f.read())
            with open(resp_file, "w", encoding="utf-8") as f:
                f.write(json.dumps({"status": "ok", "id": d["id"]}))
            os.remove(cmd_file)
            with open(resp_file, "r", encoding="utf-8") as f:
                _ = json.loads(f.read())
            os.remove(resp_file)

        # Timed Sequential Run
        latencies = []
        t_start_total = time.perf_counter()
        for i in range(n_ops):
            t0 = time.perf_counter()
            with open(cmd_tmp, "w", encoding="utf-8") as f:
                f.write(json.dumps({"command": "track_create", "params": {"name": f"Trk {i}"}, "id": f"req_{i}"}))
            os.replace(cmd_tmp, cmd_file)

            # Simulated Lua bridge read & write
            with open(cmd_file, "r", encoding="utf-8") as f:
                req = json.loads(f.read())
            os.remove(cmd_file)

            with open(resp_file, "w", encoding="utf-8") as f:
                f.write(json.dumps({"status": "ok", "id": req["id"], "track_index": i}))

            with open(resp_file, "r", encoding="utf-8") as f:
                res = json.loads(f.read())
            os.remove(resp_file)
            latencies.append((time.perf_counter() - t0) * 1000.0)

        total_wall_time = time.perf_counter() - t_start_total
        sorted_lat = sorted(latencies)

        return {
            "transport": "File-based Atomic Swap (Raw filesystem transport only)",
            "warmup_requests": warmup,
            "measured_requests": n_ops,
            "execution_mode": "Sequential (1 client, 1 writer, in-memory FS cache)",
            "wall_clock_time_sec": total_wall_time,
            "latency_mean_ms": statistics.mean(latencies),
            "latency_p50_ms": statistics.median(latencies),
            "latency_p95_ms": sorted_lat[int(n_ops * 0.95)],
            "latency_p99_ms": sorted_lat[int(n_ops * 0.99)],
            "latency_max_ms": sorted_lat[-1],
            "throughput_ops_per_sec": n_ops / total_wall_time,
            "caveat": "Measures transport serialization and local OS file cache. Does NOT include REAPER's 15-33ms defer() loop tick or ReaScript execution latency."
        }

# 2. LOCAL LOOPBACK TCP SOCKET (JSON-RPC)
def benchmark_socket_ipc_rigorous(warmup: int, n_ops: int) -> Dict[str, Any]:
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(1)
    port = server_sock.getsockname()[1]

    stop_event = threading.Event()
    def srv():
        conn, _ = server_sock.accept()
        while not stop_event.is_set():
            try:
                raw_len = conn.recv(4)
                if not raw_len: break
                msg_len = int.from_bytes(raw_len, 'big')
                data = conn.recv(msg_len)
                req = json.loads(data.decode('utf-8'))
                resp = json.dumps({"jsonrpc": "2.0", "result": {"idx": req["id"]}, "id": req["id"]}).encode('utf-8')
                conn.sendall(len(resp).to_bytes(4, 'big') + resp)
            except Exception:
                break
        conn.close()
        server_sock.close()

    t = threading.Thread(target=srv)
    t.start()

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect(("127.0.0.1", port))

    # Warmup
    for i in range(warmup):
        req = json.dumps({"jsonrpc": "2.0", "method": "warmup", "id": i}).encode('utf-8')
        client_sock.sendall(len(req).to_bytes(4, 'big') + req)
        l = int.from_bytes(client_sock.recv(4), 'big')
        _ = client_sock.recv(l)

    latencies = []
    t_start_total = time.perf_counter()
    for i in range(n_ops):
        t0 = time.perf_counter()
        req = json.dumps({"jsonrpc": "2.0", "method": "track_create", "params": {"name": f"Trk {i}"}, "id": i}).encode('utf-8')
        client_sock.sendall(len(req).to_bytes(4, 'big') + req)
        l = int.from_bytes(client_sock.recv(4), 'big')
        resp = json.loads(client_sock.recv(l).decode('utf-8'))
        latencies.append((time.perf_counter() - t0) * 1000.0)

    total_wall_time = time.perf_counter() - t_start_total
    stop_event.set()
    client_sock.close()
    t.join()

    sorted_lat = sorted(latencies)
    return {
        "transport": "TCP Socket JSON-RPC (Loopback 127.0.0.1)",
        "warmup_requests": warmup,
        "measured_requests": n_ops,
        "execution_mode": "Sequential (Single persistent connection)",
        "wall_clock_time_sec": total_wall_time,
        "latency_mean_ms": statistics.mean(latencies),
        "latency_p50_ms": statistics.median(latencies),
        "latency_p95_ms": sorted_lat[int(n_ops * 0.95)],
        "latency_p99_ms": sorted_lat[int(n_ops * 0.99)],
        "latency_max_ms": sorted_lat[-1],
        "throughput_ops_per_sec": n_ops / total_wall_time,
        "caveat": "Measures loopback socket serialization. Does not include DAW audio thread dispatch or plugin load overhead."
    }

# 3. WEBSOCKET JSON-RPC (UI Bridge)
async def async_ws_benchmark_rigorous(warmup: int, n_ops: int) -> Dict[str, Any]:
    async def handler(websocket):
        async for message in websocket:
            req = json.loads(message)
            resp = json.dumps({"jsonrpc": "2.0", "result": {"success": True}, "id": req["id"]})
            await websocket.send(resp)

    server = await websockets.serve(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
        # Warmup
        for i in range(warmup):
            await ws.send(json.dumps({"jsonrpc": "2.0", "method": "warmup", "id": i}))
            _ = await ws.recv()

        latencies = []
        t_start_total = time.perf_counter()
        for i in range(n_ops):
            t0 = time.perf_counter()
            await ws.send(json.dumps({"jsonrpc": "2.0", "method": "set_param", "params": {"fx": 1, "val": 0.5}, "id": i}))
            _ = await ws.recv()
            latencies.append((time.perf_counter() - t0) * 1000.0)

        total_wall_time = time.perf_counter() - t_start_total

    server.close()
    await server.wait_closed()
    sorted_lat = sorted(latencies)
    return {
        "transport": "WebSocket JSON-RPC (Tauri/Browser UI Bridge)",
        "warmup_requests": warmup,
        "measured_requests": n_ops,
        "execution_mode": "Sequential async request-response over persistent ws connection",
        "wall_clock_time_sec": total_wall_time,
        "latency_mean_ms": statistics.mean(latencies),
        "latency_p50_ms": statistics.median(latencies),
        "latency_p95_ms": sorted_lat[int(n_ops * 0.95)],
        "latency_p99_ms": sorted_lat[int(n_ops * 0.99)],
        "latency_max_ms": sorted_lat[-1],
        "throughput_ops_per_sec": n_ops / total_wall_time,
        "caveat": "Measures asyncio event loop and WebSocket framing. Does not include DOM rendering in WebView."
    }

if __name__ == "__main__":
    res = {
        "benchmark_metadata": {
            "date": "2026-11-06",
            "environment": "Linux container x86_64, Python 3.12.3",
            "methodology": "Microbenchmark of transport serialization and IPC channel only"
        },
        "file_ipc": benchmark_file_ipc_rigorous(WARMUP_OPS, BENCHMARK_OPS),
        "socket_ipc": benchmark_socket_ipc_rigorous(WARMUP_OPS, BENCHMARK_OPS),
        "websocket_ipc": asyncio.run(async_ws_benchmark_rigorous(WARMUP_OPS, BENCHMARK_OPS))
    }
    with open("evidence/rigorous_ipc_benchmarks.json", "w") as f:
        json.dump(res, f, indent=2)
    print("Rigorous IPC Benchmarks Completed:")
    print(json.dumps(res, indent=2))
