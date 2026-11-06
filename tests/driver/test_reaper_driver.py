import pytest
import os
import time
import json
import threading
import tempfile
from concurrent.futures import ThreadPoolExecutor

from commander.driver.reaper_driver import ReaperFileDriver
from commander.protocol.schema import CommandRequest, CommanderError, ErrorCode

def mock_reaper_server_loop(ipc_dir: str, stop_event: threading.Event):
    """Simulates REAPER Lua defer loop polling for commands and responding."""
    cmd_file = os.path.join(ipc_dir, "command.json")
    resp_file = os.path.join(ipc_dir, "response.json")
    resp_tmp = os.path.join(ipc_dir, "response.tmp")
    lock_file = os.path.join(ipc_dir, "server.lock")

    with open(lock_file, "w") as f:
        f.write(str(time.time()))

    while not stop_event.is_set():
        if os.path.exists(cmd_file):
            try:
                with open(cmd_file, "r") as f:
                    cmd_data = json.loads(f.read())
                os.remove(cmd_file)

                cmd_name = cmd_data.get("command")
                req_id = cmd_data.get("id")

                if cmd_name == "fail_cmd":
                    resp_data = {"id": req_id, "status": "error", "error": "Simulated VST error"}
                elif cmd_name == "sleep_cmd":
                    time.sleep(0.2)
                    resp_data = {"id": req_id, "status": "ok", "result": {"slept": True}}
                else:
                    resp_data = {"id": req_id, "status": "ok", "result": {"echo": cmd_name, "track_count": 5}}

                with open(resp_tmp, "w") as f:
                    f.write(json.dumps(resp_data))
                os.replace(resp_tmp, resp_file)
            except Exception:
                pass
        time.sleep(0.002)

def test_driver_basic_command_and_heartbeat():
    with tempfile.TemporaryDirectory() as tmpdir:
        driver = ReaperFileDriver(ipc_dir=tmpdir, poll_interval=0.002)
        assert not driver.is_alive()

        stop_event = threading.Event()
        t = threading.Thread(target=mock_reaper_server_loop, args=(tmpdir, stop_event))
        t.start()

        try:
            time.sleep(0.05)
            assert driver.is_alive()

            req = CommandRequest(command="track_create", params={"name": "Violin"})
            resp = driver.send_command(req, timeout=2.0)
            assert resp.status == "ok"
            assert resp.id == req.id
            assert resp.result["echo"] == "track_create"
        finally:
            stop_event.set()
            t.join()

def test_driver_timeout_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        driver = ReaperFileDriver(ipc_dir=tmpdir, poll_interval=0.002)
        req = CommandRequest(command="hang_cmd")
        with pytest.raises(CommanderError) as exc_info:
            driver.send_command(req, timeout=0.05)
        assert exc_info.value.code == ErrorCode.TIMEOUT

def test_driver_concurrent_requests():
    """Verify that multiple concurrent threads do not corrupt IPC files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        driver = ReaperFileDriver(ipc_dir=tmpdir, poll_interval=0.002)
        stop_event = threading.Event()
        t = threading.Thread(target=mock_reaper_server_loop, args=(tmpdir, stop_event))
        t.start()

        try:
            time.sleep(0.05)
            def send_worker(i):
                req = CommandRequest(command=f"cmd_{i}", params={"idx": i})
                return driver.send_command(req, timeout=3.0)

            with ThreadPoolExecutor(max_workers=5) as pool:
                results = list(pool.map(send_worker, range(20)))

            for i, r in enumerate(results):
                assert r.status == "ok"
                assert r.result["echo"] == f"cmd_{i}"
        finally:
            stop_event.set()
            t.join()

def test_driver_stale_response_discarded():
    """Verify that an obsolete response file from an earlier request is discarded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        driver = ReaperFileDriver(ipc_dir=tmpdir, poll_interval=0.002)
        # Pre-seed a stale response
        with open(driver.response_file, "w") as f:
            f.write(json.dumps({"id": "old_abandoned_id", "status": "ok", "result": "stale"}))

        stop_event = threading.Event()
        t = threading.Thread(target=mock_reaper_server_loop, args=(tmpdir, stop_event))
        t.start()

        try:
            time.sleep(0.05)
            req = CommandRequest(command="new_cmd")
            resp = driver.send_command(req, timeout=2.0)
            assert resp.id == req.id
            assert resp.result["echo"] == "new_cmd"
        finally:
            stop_event.set()
            t.join()
