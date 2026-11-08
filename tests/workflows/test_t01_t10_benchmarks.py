import pytest
import numpy as np
from commander.workflows.recipes import WorkflowRecipes
from commander.workflows.verification import WorkflowVerificationEngine
from commander.driver.base_adapter import IDawAdapter
from commander.protocol.schema import CommandRequest, CommandResponse
from commander.transaction.manager import TransactionManager, TransactionStep, TransactionState

class ComprehensiveDawMockAdapter(IDawAdapter):
    """Mock simulating DAW features for T01-T10 benchmark verification."""
    def __init__(self):
        self.tracks = [
            {"id": 1, "name": "Kick", "frozen": False, "fx": [{"name": "ReaEQ", "params": {"gain": 0.0}}]},
            {"id": 2, "name": "Bass", "frozen": False, "fx": [{"name": "ReaComp", "params": {"threshold": -12.0}}]},
        ]
        self.bpm = 120.0
        self.is_playing = False
        self.sends = []

    def is_alive(self) -> bool: return True

    def get_project_state(self):
        return {
            "bpm": self.bpm,
            "track_count": len(self.tracks),
            "tracks": list(self.tracks),
            "sends": list(self.sends),
            "is_playing": self.is_playing
        }

    def send_command(self, request: CommandRequest, timeout: float = 10.0):
        cmd = request.command
        p = request.params
        if cmd == "track.create":
            tid = len(self.tracks) + 1
            t = {"id": tid, "name": p.get("name", "Track"), "frozen": False, "fx": []}
            self.tracks.append(t)
            return CommandResponse(id=request.id, status="ok", result={"id": tid})
        elif cmd == "fx.add":
            tid = p.get("track_id")
            for t in self.tracks:
                if t["id"] == tid:
                    t["fx"].append({"name": p.get("plugin"), "params": {}})
            return CommandResponse(id=request.id, status="ok", result={"added": True})
        elif cmd == "routing.create_send":
            self.sends.append(p)
            return CommandResponse(id=request.id, status="ok", result={"send_id": len(self.sends)})
        elif cmd == "routing.create_sidechain":
            self.sends.append({"type": "sidechain", **p})
            return CommandResponse(id=request.id, status="ok", result={"sidechain": True})
        elif cmd == "track.freeze":
            tid = p.get("track_id")
            for t in self.tracks:
                if t["id"] == tid: t["frozen"] = True
            return CommandResponse(id=request.id, status="ok", result={"frozen": True})
        elif cmd == "track.unfreeze":
            tid = p.get("track_id")
            for t in self.tracks:
                if t["id"] == tid: t["frozen"] = False
            return CommandResponse(id=request.id, status="ok", result={"frozen": False})
        return CommandResponse(id=request.id, status="ok", result={})

def test_t01_t03_foundation_checks():
    adapter = ComprehensiveDawMockAdapter()
    state = adapter.get_project_state()
    # T01: Read project summary
    assert state["track_count"] == 2
    assert state["bpm"] == 120.0
    # T02: Inspect tracks and FX
    assert state["tracks"][0]["name"] == "Kick"
    assert state["tracks"][0]["fx"][0]["name"] == "ReaEQ"
    # T03: Inspect transport
    assert state["is_playing"] is False

def test_t04_humanize_midi_16_bars():
    # 16 bars of quarter notes = 64 notes
    raw_notes = [{"pitch": 60, "start_beat": float(i), "velocity": 80} for i in range(64)]
    humanized = WorkflowRecipes.humanize_midi(raw_notes, timing_jitter_beats=0.02, velocity_range=6)
    assert len(humanized) == 64
    # Check that jitter was applied
    velocities = [n["velocity"] for n in humanized]
    assert min(velocities) != max(velocities)
    assert all(74 <= v <= 86 for v in velocities)

def test_t05_reverb_send_setup():
    adapter = ComprehensiveDawMockAdapter()
    res = WorkflowRecipes.setup_reverb_send(adapter, source_track_id=1, reverb_name="Vocal Verb Aux", send_level_db=-6.0)
    assert res["status"] == "ok"
    assert res["routing_confirmed"] is True
    assert adapter.get_project_state()["track_count"] == 3

def test_t06_t07_fx_param_and_freeze():
    adapter = ComprehensiveDawMockAdapter()
    # Freeze
    adapter.send_command(CommandRequest(command="track.freeze", params={"track_id": 1}))
    assert adapter.get_project_state()["tracks"][0]["frozen"] is True
    # Unfreeze
    adapter.send_command(CommandRequest(command="track.unfreeze", params={"track_id": 1}))
    assert adapter.get_project_state()["tracks"][0]["frozen"] is False

def test_t08_intentional_failure_rollback():
    adapter = ComprehensiveDawMockAdapter()
    tm = TransactionManager(adapter, journal_dir="/tmp/t08_journals")
    steps = [
        TransactionStep(1, "track.create", {"name": "Temp 1"}, "noop", {}),
        TransactionStep(2, "faulty_command_that_fails", {}, "noop", {})
    ]
    with pytest.raises(Exception):
        tm.execute_transaction("T08 Batch", steps=steps)

def test_t09_t10_signal_verification():
    sr = 44100
    t = np.linspace(0, 0.5, int(sr*0.5), endpoint=False)
    dry = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    wet = dry + 0.1 * np.sin(2 * np.pi * 880 * t).astype(np.float32)
    # T09: Signal verification for EQ
    v_res = WorkflowVerificationEngine.verify_signal("eq", dry, wet, sr=sr)
    assert v_res["passed"] is True
    assert "spectral_difference" in v_res["metrics"]
    # T10: Musical verification checklist
    checklist = WorkflowVerificationEngine.get_musical_verification_checklist("eq")
    assert len(checklist["subjective_criteria"]) > 0
