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

# Test parameters
NUM_OPERATIONS = 1000

# 1. FILE-BASED IPC SIMULATION (Reaper-MCP model: write command -> atomic rename -> Lua poll -> write response)
def benchmark_file_ipc(n_ops: int) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd_file = os.path.join(tmpdir, "command.json")
        resp_file = os.path.join(tmpdir, "response.json")
        cmd_tmp = os.path.join(tmpdir, "command.tmp")

        latencies = []
        for i in range(n_ops):
            t0 = time.perf_counter()
            # Client writes command
            payload = json.dumps({"action": "create_track", "name": f"Track {i}", "seq": i})
            with open(cmd_tmp, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(cmd_tmp, cmd_file)

            # Simulated Lua defer poll & response (instant file read & write)
            with open(cmd_file, "r", encoding="utf-8") as f:
                data = json.loads(f.read())
            resp = json.dumps({"status": "ok", "track_id": i, "seq": data["seq"]})
            with open(resp_file, "w", encoding="utf-8") as f:
                f.write(resp)
            os.remove(cmd_file)

            # Client reads response
            with open(resp_file, "r", encoding="utf-8") as f:
                res = json.loads(f.read())
            os.remove(resp_file)

            latencies.append((time.perf_counter() - t0) * 1000.0)

        return {
            "protocol": "File-based Atomic Swap (Reaper-MCP style)",
            "operations": n_ops,
            "avg_latency_ms": statistics.mean(latencies),
            "p50_latency_ms": statistics.median(latencies),
            "p99_latency_ms": sorted(latencies)[int(n_ops * 0.99)],
            "throughput_ops_sec": n_ops / (sum(latencies) / 1000.0)
        }

# 2. LOCAL SOCKET / JSON-RPC IPC (reapy / Unix Domain Socket / Named Pipe model)
def benchmark_socket_ipc(n_ops: int) -> Dict[str, Any]:
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(1)
    port = server_sock.getsockname()[1]

    stop_event = threading.Event()

    def server_loop():
        conn, _ = server_sock.accept()
        while not stop_event.is_set():
            try:
                raw_len = conn.recv(4)
                if not raw_len:
                    break
                msg_len = int.from_bytes(raw_len, 'big')
                data = conn.recv(msg_len)
                req = json.loads(data.decode('utf-8'))

                resp = json.dumps({"jsonrpc": "2.0", "result": {"track_id": req["id"]}, "id": req["id"]}).encode('utf-8')
                conn.sendall(len(resp).to_bytes(4, 'big') + resp)
            except Exception:
                break
        conn.close()
        server_sock.close()

    t = threading.Thread(target=server_loop)
    t.start()

    # Client
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect(("127.0.0.1", port))

    latencies = []
    for i in range(n_ops):
        t0 = time.perf_counter()
        req = json.dumps({"jsonrpc": "2.0", "method": "create_track", "params": {"name": f"Track {i}"}, "id": i}).encode('utf-8')
        client_sock.sendall(len(req).to_bytes(4, 'big') + req)

        raw_len = client_sock.recv(4)
        resp_len = int.from_bytes(raw_len, 'big')
        resp_data = client_sock.recv(resp_len)
        resp = json.loads(resp_data.decode('utf-8'))
        latencies.append((time.perf_counter() - t0) * 1000.0)

    stop_event.set()
    client_sock.close()
    t.join()

    return {
        "protocol": "TCP / Local Loopback JSON-RPC (reapy/adapter style)",
        "operations": n_ops,
        "avg_latency_ms": statistics.mean(latencies),
        "p50_latency_ms": statistics.median(latencies),
        "p99_latency_ms": sorted(latencies)[int(n_ops * 0.99)],
        "throughput_ops_sec": n_ops / (sum(latencies) / 1000.0)
    }

# 3. WEBSOCKET / JSON-RPC (Modern web/desktop DAW bridge model)
async def async_ws_benchmark(n_ops: int) -> Dict[str, Any]:
    async def handler(websocket):
        async for message in websocket:
            req = json.loads(message)
            resp = json.dumps({"jsonrpc": "2.0", "result": {"success": True}, "id": req["id"]})
            await websocket.send(resp)

    server = await websockets.serve(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    latencies = []
    async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
        for i in range(n_ops):
            t0 = time.perf_counter()
            msg = json.dumps({"jsonrpc": "2.0", "method": "update_fx_param", "params": {"fx": 1, "val": 0.5}, "id": i})
            await ws.send(msg)
            res = await ws.recv()
            latencies.append((time.perf_counter() - t0) * 1000.0)

    server.close()
    await server.wait_closed()

    return {
        "protocol": "WebSocket JSON-RPC (Async UI/Commander Bridge)",
        "operations": n_ops,
        "avg_latency_ms": statistics.mean(latencies),
        "p50_latency_ms": statistics.median(latencies),
        "p99_latency_ms": sorted(latencies)[int(n_ops * 0.99)],
        "throughput_ops_sec": n_ops / (sum(latencies) / 1000.0)
    }

# 4. TRANSACTION ROLLBACK SIMULATION
def benchmark_transaction_rollback() -> Dict[str, Any]:
    """Test multi-operation atomic transaction: executes N actions, simulates a failure at action K, tests state rollback."""
    project_state = {"tracks": []}
    history = []

    def apply_action(action, state, hist):
        hist.append(json.loads(json.dumps(state))) # checkpoint snapshot
        if action["type"] == "add_track":
            state["tracks"].append({"id": action["id"], "name": action["name"]})
        elif action["type"] == "delete_track":
            state["tracks"] = [t for t in state["tracks"] if t["id"] != action["id"]]
        elif action["type"] == "faulty_action":
            raise RuntimeError("VST plugin initialization failed")

    # Transaction with 5 steps, step 4 throws exception
    tx_steps = [
        {"type": "add_track", "id": 1, "name": "Kick"},
        {"type": "add_track", "id": 2, "name": "Snare"},
        {"type": "add_track", "id": 3, "name": "HiHat"},
        {"type": "faulty_action", "id": 4, "name": "Invalid Synth"},
        {"type": "add_track", "id": 5, "name": "Bass"}
    ]

    t0 = time.perf_counter()
    initial_snapshot = json.loads(json.dumps(project_state))
    rollback_occurred = False
    try:
        for step in tx_steps:
            apply_action(step, project_state, history)
    except Exception as e:
        # Rollback to initial snapshot
        project_state = initial_snapshot
        rollback_occurred = True
    rollback_time_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "test": "Atomic Multi-Action Rollback",
        "rollback_verified": rollback_occurred and len(project_state["tracks"]) == 0,
        "rollback_time_ms": rollback_time_ms,
        "final_track_count": len(project_state["tracks"])
    }

if __name__ == "__main__":
    results = {}
    print("Running File IPC Benchmark...")
    results["file_ipc"] = benchmark_file_ipc(NUM_OPERATIONS)
    print("Running Socket JSON-RPC Benchmark...")
    results["socket_ipc"] = benchmark_socket_ipc(NUM_OPERATIONS)
    print("Running WebSocket Benchmark...")
    results["websocket_ipc"] = asyncio.run(async_ws_benchmark(NUM_OPERATIONS))
    print("Running Transaction Rollback Verification...")
    results["transaction_rollback"] = benchmark_transaction_rollback()

    with open("evidence/ipc_benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Results saved to evidence/ipc_benchmark_results.json:")
    print(json.dumps(results, indent=2))
