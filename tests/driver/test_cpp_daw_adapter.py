import pytest
import socket
import threading
import json
from commander.driver.cpp_daw_adapter import CppDawAdapter
from commander.protocol.schema import CommandRequest, CommanderError

class MockCppDawServer:
    def __init__(self, host="127.0.0.1", port=0):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.bind((host, port))
        self.server_sock.listen(1)
        self.port = self.server_sock.getsockname()[1]
        self.stop_event = threading.Event()
        self.tracks = []
        self.clips = []
        self.bpm = 120.0
        self.is_playing = False

    def start(self):
        self.thread = threading.Thread(target=self._run)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        try:
            self.server_sock.close()
        except Exception:
            pass
        self.thread.join()

    def _run(self):
        while not self.stop_event.is_set():
            try:
                conn, _ = self.server_sock.accept()
                while not self.stop_event.is_set():
                    raw_len = conn.recv(4)
                    if not raw_len:
                        break
                    msg_len = int.from_bytes(raw_len, "big")
                    body = conn.recv(msg_len)
                    req = json.loads(body.decode("utf-8"))

                    cmd = req.get("command")
                    p = req.get("params", {})
                    req_id = req.get("id")

                    if cmd == "ping":
                        resp = {"id": req_id, "status": "ok", "result": {"pong": True}}
                    elif cmd == "project.get_state":
                        resp = {"id": req_id, "status": "ok", "result": {
                            "bpm": self.bpm,
                            "tracks": self.tracks,
                            "clips": self.clips,
                            "is_playing": self.is_playing
                        }}
                    elif cmd == "track.create":
                        tid = len(self.tracks) + 1
                        t = {"id": tid, "name": p.get("name", "Track"), "instrument": p.get("instrument")}
                        self.tracks.append(t)
                        resp = {"id": req_id, "status": "ok", "result": t}
                    elif cmd == "clip.create":
                        cid = len(self.clips) + 1
                        c = {"id": cid, "track_id": p.get("track_id"), "start_beat": p.get("start_beat"), "notes": []}
                        self.clips.append(c)
                        resp = {"id": req_id, "status": "ok", "result": c}
                    elif cmd == "notes.insert_batch":
                        cid = p.get("clip_id")
                        notes = p.get("notes", [])
                        for c in self.clips:
                            if c["id"] == cid:
                                c["notes"].extend(notes)
                        resp = {"id": req_id, "status": "ok", "result": {"inserted_count": len(notes)}}
                    elif cmd == "transport.play":
                        self.is_playing = True
                        resp = {"id": req_id, "status": "ok", "result": {"playing": True}}
                    elif cmd == "transport.stop":
                        self.is_playing = False
                        resp = {"id": req_id, "status": "ok", "result": {"playing": False}}
                    elif cmd == "transport.set_tempo":
                        self.bpm = p.get("bpm", 120.0)
                        resp = {"id": req_id, "status": "ok", "result": {"bpm": self.bpm}}
                    else:
                        resp = {"id": req_id, "status": "ok", "result": {"ack": cmd}}

                    payload = json.dumps(resp).encode("utf-8")
                    conn.sendall(len(payload).to_bytes(4, "big") + payload)
            except Exception:
                break

def test_cpp_daw_adapter_full_crud():
    server = MockCppDawServer()
    server.start()
    try:
        adapter = CppDawAdapter(port=server.port)
        assert adapter.connect() is True
        assert adapter.is_alive() is True

        # 1. Project state
        state = adapter.get_project_state()
        assert state["bpm"] == 120.0
        assert len(state["tracks"]) == 0

        # 2. Set tempo
        assert adapter.set_tempo_and_meter(bpm=88.0) is True

        # 3. Create Tracks
        t1 = adapter.create_track("Melody (Music Box)", instrument="SineToneSynth")
        assert t1["id"] == 1
        t2 = adapter.create_track("Accompaniment (Celesta)", instrument="SineToneSynth")
        assert t2["id"] == 2

        # 4. Create Clip & Insert Notes
        clip = adapter.create_midi_clip(track_id=1, start_beat=0.0, length_beats=16.0, name="Verse Melody")
        assert clip["id"] == 1

        notes = [
            {"pitch": 72, "start_beat": 0.0, "duration_beats": 1.0, "velocity": 75},
            {"pitch": 76, "start_beat": 1.0, "duration_beats": 1.0, "velocity": 75},
            {"pitch": 79, "start_beat": 2.0, "duration_beats": 2.0, "velocity": 75}
        ]
        res_notes = adapter.insert_notes(clip_id=clip["id"], notes=notes)
        assert res_notes["inserted_count"] == 3

        # 5. Transport Play & Stop
        assert adapter.transport_play() is True
        assert adapter.get_project_state()["is_playing"] is True
        assert adapter.transport_stop() is True
        assert adapter.get_project_state()["is_playing"] is False

    finally:
        adapter.close()
        server.stop()
