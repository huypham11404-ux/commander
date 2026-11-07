import pytest
from tests.driver.test_cpp_daw_adapter import MockCppDawServer
from commander.driver.cpp_daw_adapter import CppDawAdapter
from commander.agent.composition_planner import CompositionPlanner

def test_end_to_end_cpp_daw_music_production_workflow():
    server = MockCppDawServer()
    server.start()
    try:
        adapter = CppDawAdapter(port=server.port)
        assert adapter.connect() is True

        # 1. Natural language prompt interpretation
        prompt = "Create a gentle nursery music arrangement with a simple melody, soft accompaniment, and a moderate tempo."
        plan = CompositionPlanner.plan_from_prompt(prompt)
        assert plan.tempo_bpm == 84.0
        assert len(plan.tracks) == 2

        # 2. Set tempo in DAW
        assert adapter.set_tempo_and_meter(bpm=plan.tempo_bpm) is True

        # 3. Create Tracks & Clips in DAW
        for trk in plan.tracks:
            t_res = adapter.create_track(name=trk["name"], instrument=trk["instrument"])
            clip_res = adapter.create_midi_clip(track_id=t_res["id"], start_beat=trk["start_beat"], length_beats=trk["length_beats"])
            note_res = adapter.insert_notes(clip_id=clip_res["id"], notes=trk["notes"])
            assert note_res["inserted_count"] == len(trk["notes"])

        # 4. Verify project state
        state = adapter.get_project_state()
        assert len(state["tracks"]) == 2
        assert len(state["clips"]) == 2
        assert state["bpm"] == 84.0

        # 5. Playback
        assert adapter.transport_play() is True
        assert adapter.get_project_state()["is_playing"] is True
        assert adapter.transport_stop() is True
        assert adapter.get_project_state()["is_playing"] is False

    finally:
        adapter.close()
        server.stop()
