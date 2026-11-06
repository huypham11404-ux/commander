import pytest
import os
import tempfile
import numpy as np

from commander.driver.base_adapter import IDawAdapter
from commander.protocol.schema import CommandRequest, CommandResponse
from commander.transaction.manager import TransactionManager, TransactionStep
from commander.agent.permissions import PermissionPolicyEngine, PermissionLevel, RiskLevel
from commander.agent.tool_registry import ToolRegistry, ToolDefinition
from commander.agent.runtime import AgentRuntime
from commander.intelligence.harmony_engine import HarmonyContextEngine
from commander.dsp.pipeline import DspAnalyzer
from commander.storage.session_memory import ProjectSessionMemory

class MockIntegrationReaperAdapter(IDawAdapter):
    def __init__(self):
        self.tracks = {}
        self.next_id = 1

    def is_alive(self) -> bool:
        return True

    def get_project_state(self):
        return {"track_count": len(self.tracks), "tracks": list(self.tracks.values())}

    def send_command(self, request: CommandRequest, timeout: float = 10.0):
        cmd = request.command
        params = request.params
        if cmd == "track_create":
            tid = self.next_id
            self.next_id += 1
            self.tracks[tid] = {"id": tid, "name": params.get("name", "Track")}
            return CommandResponse(id=request.id, status="ok", result={"track_id": tid})
        elif cmd == "track_delete":
            tid = params.get("track_id")
            if tid in self.tracks:
                del self.tracks[tid]
            return CommandResponse(id=request.id, status="ok", result={"deleted": tid})
        return CommandResponse(id=request.id, status="ok", result={})

def test_full_system_lifecycle_orchestration():
    """Test full system loop: Music intelligence analysis -> Permission Gate -> Transaction Execution -> DSP Feedback -> Session memory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Setup subsystems
        adapter = MockIntegrationReaperAdapter()
        tx_mgr = TransactionManager(adapter, journal_dir=os.path.join(tmpdir, "journals"))
        policy = PermissionPolicyEngine(PermissionLevel.PROPOSED_CHANGE)
        registry = ToolRegistry()
        session_mem = ProjectSessionMemory(tmpdir)

        # 2. Register tools
        registry.register_tool(ToolDefinition(
            name="track_create",
            version="1.0",
            description="Create track",
            risk_level=RiskLevel.MEDIUM,
            idempotent=False,
            handler=lambda p: adapter.send_command(CommandRequest(command="track_create", params=p)).result
        ))

        runtime = AgentRuntime(registry, policy, transaction_mgr=tx_mgr)

        # 3. Step A: Music Intelligence analysis on full progression input (C -> Fm -> Ab -> G)
        harmony_eng = HarmonyContextEngine()
        h_res = harmony_eng.analyze_chords_and_key([
            ["C4", "E4", "G4"],
            ["F4", "Ab4", "C5"],
            ["Ab3", "C4", "Eb4"],
            ["G4", "B4", "D5"]
        ])
        assert h_res["estimated_key"] == "C major"
        assert h_res["modal_interchange_detected"] is True
        session_mem.update_musical_context(key=h_res["estimated_key"], bpm=72.0)

        # 4. Step B: Propose batch actions (Adding 2 tracks: Violin I, Violin II)
        plan_steps = [
            {"tool": "track_create", "params": {"name": "Violin I"}, "compensating_tool": "track_delete", "compensating_params": {"track_id": 1}},
            {"tool": "track_create", "params": {"name": "Violin II"}, "compensating_tool": "track_delete", "compensating_params": {"track_id": 2}}
        ]

        # In PROPOSED_CHANGE mode, unapproved execution fails
        with pytest.raises(Exception):
            runtime.execute_atomic_batch(description="Add Violin Section", steps=plan_steps)

        # User approves proposal
        proposal_id = "prop_string_section_01"
        policy.approve_proposal(proposal_id)

        # Execute approved batch
        batch_res = runtime.execute_atomic_batch(
            description="Add Violin Section",
            steps=plan_steps,
            proposal_id=proposal_id
        )
        assert batch_res["state"] == "COMMITTED"
        assert adapter.get_project_state()["track_count"] == 2

        # 5. Step C: DSP Analysis on rendered stem
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        audio = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        dsp_res = DspAnalyzer.analyze_audio_array(audio, sr=sr)
        assert dsp_res["measurements"]["sample_peak"] > 0.49

        # Record message in session memory
        session_mem.append_message("assistant", f"Violin section created in {h_res['estimated_key']}. Peak: {dsp_res['measurements']['sample_peak']} dBFS.")
        assert len(session_mem.data["conversation_history"]) == 1
