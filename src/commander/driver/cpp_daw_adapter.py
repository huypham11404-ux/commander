"""Independent C++ DAW Adapter implementing IDawAdapter via versioned JSON-RPC over local socket / IPC."""
import socket
import json
import time
import logging
from typing import Dict, Any, Optional, List

from commander.driver.base_adapter import IDawAdapter
from commander.protocol.schema import CommandRequest, CommandResponse, CommanderError, ErrorCode, PROTOCOL_VERSION

logger = logging.getLogger("commander.driver.cpp_daw")

class CppDawAdapter(IDawAdapter):
    """Adapter connecting Commander to our independently developed C++ DAW via local socket / IPC."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9988, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.default_timeout = timeout
        self.client_sock: Optional[socket.socket] = None

    def connect(self) -> bool:
        """Establish connection with the running C++ DAW instance."""
        try:
            self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_sock.settimeout(self.default_timeout)
            self.client_sock.connect((self.host, self.port))
            return True
        except Exception as e:
            logger.warning("Could not connect to C++ DAW at %s:%d: %s", self.host, self.port, e)
            self.client_sock = None
            return False

    def close(self):
        if self.client_sock:
            try:
                self.client_sock.close()
            except Exception:
                pass
            self.client_sock = None

    def is_alive(self) -> bool:
        """Ping C++ DAW engine to verify availability."""
        try:
            req = CommandRequest(command="ping")
            resp = self.send_command(req, timeout=1.0)
            return resp.status == "ok"
        except Exception:
            return False

    def send_command(self, request: CommandRequest, timeout: float = 10.0) -> CommandResponse:
        """Send length-prefixed JSON command to C++ DAW and await response."""
        t0 = time.perf_counter()

        # If not connected, attempt connection
        if not self.client_sock:
            if not self.connect():
                raise CommanderError(
                    ErrorCode.REAPER_NOT_RUNNING,
                    f"C++ DAW is not running or unreachable at {self.host}:{self.port}"
                )

        try:
            payload = json.dumps(request.to_dict()).encode("utf-8")
            # 4-byte big-endian length prefix
            msg = len(payload).to_bytes(4, byteorder="big") + payload
            self.client_sock.settimeout(timeout)
            self.client_sock.sendall(msg)

            # Read 4-byte response length
            raw_len = self._recv_exact(4)
            if not raw_len:
                raise CommanderError(ErrorCode.COMMUNICATION_ERROR, "DAW closed connection unexpectedly.")
            resp_len = int.from_bytes(raw_len, byteorder="big")

            # Read response body
            raw_body = self._recv_exact(resp_len)
            resp_dict = json.loads(raw_body.decode("utf-8"))

            exec_time = (time.perf_counter() - t0) * 1000.0
            status = resp_dict.get("status", "ok")

            if status == "error":
                return CommandResponse(
                    id=request.id,
                    status="error",
                    error=resp_dict.get("error", "Unknown C++ DAW error"),
                    execution_time_ms=exec_time
                )

            return CommandResponse(
                id=request.id,
                status="ok",
                result=resp_dict.get("result", resp_dict),
                execution_time_ms=exec_time
            )

        except socket.timeout:
            self.close()
            raise CommanderError(ErrorCode.TIMEOUT, f"Command '{request.command}' timed out after {timeout}s")
        except Exception as e:
            self.close()
            raise CommanderError(ErrorCode.COMMUNICATION_ERROR, f"C++ DAW socket error: {e}")

    def _recv_exact(self, n: int) -> bytes:
        data = bytearray()
        while len(data) < n:
            packet = self.client_sock.recv(n - len(data))
            if not packet:
                break
            data.extend(packet)
        return bytes(data)

    def get_project_state(self) -> Dict[str, Any]:
        req = CommandRequest(command="project.get_state")
        resp = self.send_command(req)
        if resp.status != "ok":
            raise CommanderError(ErrorCode.COMMUNICATION_ERROR, resp.error or "Failed to query project state")
        return resp.result or {}

    # High-level C++ DAW domain operations
    def create_track(self, name: str, instrument: Optional[str] = None) -> Dict[str, Any]:
        req = CommandRequest(command="track.create", params={"name": name, "instrument": instrument})
        resp = self.send_command(req)
        if resp.status != "ok":
            raise CommanderError(ErrorCode.COMMUNICATION_ERROR, resp.error or f"Failed to create track {name}")
        return resp.result or {}

    def rename_track(self, track_id: int, new_name: str) -> bool:
        req = CommandRequest(command="track.rename", params={"track_id": track_id, "name": new_name})
        resp = self.send_command(req)
        return resp.status == "ok"

    def set_tempo_and_meter(self, bpm: float, numerator: int = 4, denominator: int = 4) -> bool:
        req = CommandRequest(command="transport.set_tempo", params={"bpm": bpm, "numerator": numerator, "denominator": denominator})
        resp = self.send_command(req)
        return resp.status == "ok"

    def create_midi_clip(self, track_id: int, start_beat: float, length_beats: float, name: str = "Clip") -> Dict[str, Any]:
        req = CommandRequest(command="clip.create", params={
            "track_id": track_id,
            "start_beat": start_beat,
            "length_beats": length_beats,
            "name": name
        })
        resp = self.send_command(req)
        if resp.status != "ok":
            raise CommanderError(ErrorCode.COMMUNICATION_ERROR, resp.error or "Failed to create MIDI clip")
        return resp.result or {}

    def insert_notes(self, clip_id: int, notes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Insert notes: each note dict has {pitch: int, start_beat: float, duration_beats: float, velocity: int}."""
        req = CommandRequest(command="notes.insert_batch", params={
            "clip_id": clip_id,
            "notes": notes
        })
        resp = self.send_command(req)
        if resp.status != "ok":
            raise CommanderError(ErrorCode.COMMUNICATION_ERROR, resp.error or "Failed to insert notes")
        return resp.result or {}

    def transport_play(self) -> bool:
        req = CommandRequest(command="transport.play")
        resp = self.send_command(req)
        return resp.status == "ok"

    def transport_stop(self) -> bool:
        req = CommandRequest(command="transport.stop")
        resp = self.send_command(req)
        return resp.status == "ok"

    def save_project(self, filepath: Optional[str] = None) -> bool:
        req = CommandRequest(command="project.save", params={"filepath": filepath})
        resp = self.send_command(req)
        return resp.status == "ok"
