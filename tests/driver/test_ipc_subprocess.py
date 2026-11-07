import pytest
import os
import sys
import time
import json
import subprocess
import tempfile
from commander.driver.reaper_driver import ReaperFileDriver
from commander.protocol.schema import CommandRequest

MOCK_SERVER_CODE = """
import os, sys, time, json

ipc_dir = sys.argv[1]
cmd_file = os.path.join(ipc_dir, "command.json")
resp_file = os.path.join(ipc_dir, "response.json")
resp_tmp = os.path.join(ipc_dir, "response.tmp")
lock_file = os.path.join(ipc_dir, "server.lock")

with open(lock_file, "w") as f:
    f.write(str(time.time()))

for _ in range(500):
    if os.path.exists(cmd_file):
        try:
            with open(cmd_file, "r") as f:
                d = json.loads(f.read())
            os.remove(cmd_file)
            resp = {"id": d["id"], "status": "ok", "result": {"echo": d["command"]}}
            with open(resp_tmp, "w") as f:
                f.write(json.dumps(resp))
            os.replace(resp_tmp, resp_file)
        except Exception:
            pass
    time.sleep(0.005)
"""

def test_driver_subprocess_lifecycle():
    """Verify driver communication across genuine OS process boundaries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Launch mock server as external OS subprocess
        proc = subprocess.Popen([sys.executable, "-c", MOCK_SERVER_CODE, tmpdir])
        try:
            time.sleep(0.08) # let server start
            driver = ReaperFileDriver(ipc_dir=tmpdir, poll_interval=0.005)
            assert driver.is_alive()

            req = CommandRequest(command="ping_subprocess")
            resp = driver.send_command(req, timeout=3.0)
            assert resp.status == "ok"
            assert resp.result["echo"] == "ping_subprocess"
        finally:
            proc.terminate()
            proc.wait()
