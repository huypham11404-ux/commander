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
                    resp_data = {"id": req_id, "status": "error", "error": "Simulated error"}
                else:
                    resp_data = {"id": req_id, "status": "ok", "result": {"echo": cmd_name}}

                with open(resp_tmp, "w") as f:
                    f.write(json.dumps(resp_data))
                os.replace(resp_tmp, resp_file)
            except Exception:
                pass
        time.sleep(0.002)

def test_driver_duplicate_request_prevention():
    with tempfile.TemporaryDirectory() as tmpdir:
        driver = ReaperFileDriver(ipc_dir=tmpdir, poll_interval=0.002)
        stop_event = threading.Event()
        t = threading.Thread(target=mock_reaper_server_loop, args=(tmpdir, stop_event))
        t.start()

        try:
            req = CommandRequest(command="test_cmd", id="fixed_unique_id")
            resp = driver.send_command(req, timeout=2.0)
            assert resp.status == "ok"

            # Resending same request id should raise duplicate error
            with pytest.raises(CommanderError) as exc_info:
                driver.send_command(req, timeout=2.0)
            assert exc_info.value.code == ErrorCode.INVALID_PARAMS
        finally:
            stop_event.set()
            t.join()

def test_driver_lock_contention_and_release():
    with tempfile.TemporaryDirectory() as tmpdir:
        driver = ReaperFileDriver(ipc_dir=tmpdir, poll_interval=0.002)
        # Test that _acquire_mutex properly releases lock on error
        try:
            with driver._acquire_mutex(timeout=1.0):
                raise ValueError("Simulated unexpected failure inside lock")
        except ValueError:
            pass

        # Lock should be immediately re-acquirable
        with driver._acquire_mutex(timeout=0.5):
            assert True
