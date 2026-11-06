import pytest
from commander.intelligence.harmony_engine import HarmonyContextEngine
from commander.intelligence.midi_parser import MidiAnalyzer

def test_modal_interchange_resolution():
    """Verify that HarmonyContextEngine correctly identifies C Major even with borrowed Fm and Ab."""
    engine = HarmonyContextEngine()
    # Progression: C -> Fm -> Ab -> G
    progression = [
        ["C4", "E4", "G4"],
        ["F4", "Ab4", "C5"],
        ["Ab3", "C4", "Eb4"],
        ["G4", "B4", "D5"]
    ]
    res = engine.analyze_chords_and_key(progression)
    # Raw music21 falsely claims C minor
    assert res["raw_music21_key"] == "C minor"
    # Refined engine correctly identifies C major with modal interchange
    assert res["estimated_key"] == "C major"
    assert res["modal_interchange_detected"] is True

def test_voice_leading_distinguishes_contrary_motion():
    engine = HarmonyContextEngine()
    # Parallel fifth: C3-G3 -> D3-A3 (same upward direction)
    res_parallel = engine.check_voice_leading(["C3", "D3"], ["G3", "A3"])
    assert res_parallel["is_clean"] is False
    assert res_parallel["violations"][0]["type"] == "PARALLEL_FIFTH"

    # Contrary motion to fifth: Voice A moves down (C3 -> A2), Voice B moves up (G3 -> E4)
    # Voice leading is contrary (mot_a < 0 and mot_b > 0), not parallel!
    res_contrary = engine.check_voice_leading(["C3", "A2"], ["G3", "E4"])
    assert res_contrary["is_clean"] is True

def test_midi_parser():
    res = MidiAnalyzer.parse_midi("experiments/sample_progression.mid")
    assert res["track_count"] == 2
    assert res["duration_sec"] > 0
    assert len(res["tracks"][0]["notes"]) > 0
