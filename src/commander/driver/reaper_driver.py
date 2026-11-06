"""REAPER Native Driver implementing atomic file IPC with cross-process mutex."""
import os
import sys
import time
import json
import uuid
import tempfile
import logging
from contextlib import contextmanager
from typing import Dict, Any, Optional

from commander.driver.base_adapter import IDawAdapter
from commander.protocol.schema import CommandRequest, CommandResponse, CommanderError, ErrorCode, PROTOCOL_VERSION

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

logger = logging.getLogger("commander.driver.reaper")

class ReaperFileDriver(IDawAdapter):
    def __init__(self, ipc_dir: Optional[str] = None, poll_interval: float = 0.005):
        if ipc_dir:
            self.ipc_dir = ipc_dir
        else:
            self.ipc_dir = os.path.join(tempfile.gettempdir(), "reaper_mcp")
        self.poll_interval = poll_interval

        os.makedirs(self.ipc_dir, exist_ok=True)
        self.command_file = os.path.join(self.ipc_dir, "command.json")
        self.response_file = os.path.join(self.ipc_dir, "response.json")
        self.command_tmp = os.path.join(self.ipc_dir, "command.tmp")
        self.lock_file = os.path.join(self.ipc_dir, "server.lock")
        self.mutex_file = os.path.join(self.ipc_dir, "ipc_mutex.lock")

    @contextmanager
    def _acquire_mutex(self, timeout: float):
        """Cross-process file lock protecting request-response round-trip."""
        deadline = time.monotonic() + timeout
        fd = open(self.mutex_file, "a+")
        locked = False
        while time.monotonic() < deadline:
            try:
                if sys.platform == "win32":
                    msvcrt.locking(fd.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
                break
            except (BlockingIOError, OSError):
                time.sleep(self.poll_interval)

        if not locked:
            fd.close()
            raise CommanderError(ErrorCode.TIMEOUT, f"Failed to acquire IPC mutex within {timeout}s")
        try:
            yield
        finally:
            try:
                if sys.platform == "win32":
                    msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            fd.close()

    def is_alive(self, stale_threshold_sec: float = 30.0) -> bool:
        if not os.path.exists(self.lock_file):
            return False
        try:
            mtime = os.path.getmtime(self.lock_file)
            return (time.time() - mtime) < stale_threshold_sec
        except OSError:
            return False

    def send_command(self, request: CommandRequest, timeout: float = 10.0) -> CommandResponse:
        t0 = time.monotonic()
        with self._acquire_mutex(timeout):
            # 1. Clean prior stale response if any
            if os.path.exists(self.response_file):
                try:
                    os.remove(self.response_file)
                except OSError:
                    pass

            # 2. Write command atomically via tempfile + replace
            payload = json.dumps(request.to_dict())
            with open(self.command_tmp, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(self.command_tmp, self.command_file)

            # 3. Poll for response correlating with request.id
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if os.path.exists(self.response_file):
                    try:
                        with open(self.response_file, "r", encoding="utf-8") as f:
                            raw = f.read()
                        if raw.strip():
                            resp_dict = json.loads(raw)
                            resp_id = resp_dict.get("id")
                            # Detect stale response from abandoned prior request
                            if resp_id and resp_id != request.id:
                                try:
                                    os.remove(self.response_file)
                                except OSError:
                                    pass
                                time.sleep(self.poll_interval)
                                continue

                            # Remove response file after consumption
                            try:
                                os.remove(self.response_file)
                            except OSError:
                                pass

                            exec_time = (time.monotonic() - t0) * 1000.0
                            status = resp_dict.get("status", "ok")
                            if status == "error":
                                return CommandResponse(
                                    id=request.id,
                                    status="error",
                                    error=resp_dict.get("error", "Unknown REAPER error"),
                                    execution_time_ms=exec_time
                                )
                            return CommandResponse(
                                id=request.id,
                                status="ok",
                                result=resp_dict.get("result", resp_dict),
                                execution_time_ms=exec_time
                            )
                    except (json.JSONDecodeError, OSError):
                        pass
                time.sleep(self.poll_interval)

            raise CommanderError(ErrorCode.TIMEOUT, f"Command '{request.command}' (id: {request.id}) timed out after {timeout}s")

    def get_project_state(self) -> Dict[str, Any]:
        req = CommandRequest(command="project_get_state")
        resp = self.send_command(req, timeout=5.0)
        if resp.status != "ok":
            raise CommanderError(ErrorCode.COMMUNICATION_ERROR, resp.error or "Failed to get project state")
        return resp.result or {}
