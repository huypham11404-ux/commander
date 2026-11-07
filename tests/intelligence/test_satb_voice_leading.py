import pytest
from commander.intelligence.harmony_engine import HarmonyContextEngine

def test_satb_clean_bach_style_chorale_progression():
    """Test standard clean SATB progression without parallel fifths or octaves."""
    engine = HarmonyContextEngine()
    # Progression: I -> IV -> V -> I in C Major
    soprano = ["C5", "C5", "B4", "C5"]
    alto    = ["G4", "A4", "G4", "E4"]
    tenor   = ["E4", "F4", "D4", "G4"]
    bass    = ["C3", "F3", "G3", "C3"]

    res = engine.analyze_satb_voice_leading(soprano, alto, tenor, bass)
    assert res["is_clean"] is True
    assert res["total_violations"] == 0

def test_satb_parallel_fifth_detection_between_tenor_and_bass():
    """Test that a parallel fifth between Tenor and Bass is caught while Soprano-Alto are clean."""
    engine = HarmonyContextEngine()
    # Step 0 to 1 has Bass C3->D3 and Tenor G3->A3 (Parallel 5th!)
    soprano = ["E5", "F5"]
    alto    = ["C5", "D5"]
    tenor   = ["G3", "A3"]
    bass    = ["C3", "D3"]

    res = engine.analyze_satb_voice_leading(soprano, alto, tenor, bass)
    assert res["is_clean"] is False
    assert any(v["type"] == "PARALLEL_FIFTH" for v in res["violations"])
    assert any(v["voices"] == ("Tenor", "Bass") for v in res["violations"])
