import music21
import time
import json
from typing import Dict, Any, List

def create_stream_from_chords(chords_pitches: List[List[str]]) -> music21.stream.Score:
    score = music21.stream.Score()
    part = music21.stream.Part()
    for pitch_list in chords_pitches:
        c = music21.chord.Chord(pitch_list)
        c.quarterLength = 2.0
        part.append(c)
    score.append(part)
    return score

def test_harmonic_cases() -> Dict[str, Any]:
    test_suite = [
        # 1. Major Key: C Major (I - IV - V - I)
        {
            "name": "Standard Major (C Major)",
            "expected_key": "C major",
            "chords": [["C4", "E4", "G4"], ["F4", "A4", "C5"], ["G4", "B4", "D5"], ["C4", "E4", "G4"]]
        },
        # 2. Relative Minor: A Minor (Am - Dm - E7 - Am)
        {
            "name": "Relative Minor (A Minor)",
            "expected_key": "a minor",
            "chords": [["A3", "C4", "E4"], ["D4", "F4", "A4"], ["E4", "G#4", "B4", "D5"], ["A3", "C4", "E4"]]
        },
        # 3. Modal Interchange: C Major with Borrowed Minor iv (Fm) and bVI (Ab)
        {
            "name": "Modal Interchange / Borrowed Chords (C Major + Fm + Ab)",
            "expected_key": "C major",
            "chords": [["C4", "E4", "G4"], ["F4", "Ab4", "C5"], ["Ab3", "C4", "Eb4"], ["G4", "B4", "D5"]]
        },
        # 4. Secondary Dominant: V/V in C Major (D7 -> G7 -> C)
        {
            "name": "Secondary Dominant (D7 -> G -> C)",
            "expected_key": "C major",
            "chords": [["C4", "E4", "G4"], ["D4", "F#4", "A4", "C5"], ["G4", "B4", "D5"], ["C4", "E4", "G4"]]
        },
        # 5. Chromatic / Neapolitan Chord (N6 in C minor: Db/F -> G7 -> Cm)
        {
            "name": "Neapolitan 6th (Db/F -> G7 -> Cm)",
            "expected_key": "c minor",
            "chords": [["F3", "Ab3", "Db4"], ["G3", "B3", "D4", "F4"], ["C3", "Eb3", "G3"]]
        },
        # 6. Ambiguous Truncated Progression (Suspension & Inversions)
        {
            "name": "Suspended / Inversion Ambiguity (Csus4 -> C/E -> G/B)",
            "expected_key": "C major",
            "chords": [["C4", "F4", "G4"], ["E4", "G4", "C5"], ["B3", "D4", "G4"]]
        }
    ]

    results = []
    for case in test_suite:
        score = create_stream_from_chords(case["chords"])
        t0 = time.perf_counter()
        detected_key = score.analyze('key')
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        detected_str = f"{detected_key.tonic.name} {detected_key.mode}"
        match = (detected_str.lower() == case["expected_key"].lower())
        results.append({
            "test_case": case["name"],
            "expected_key": case["expected_key"],
            "detected_key": detected_str,
            "match": match,
            "correlation_score": round(detected_key.correlationCoefficient, 3),
            "analysis_time_ms": round(elapsed_ms, 2)
        })
    return results

def test_voice_leading_cases() -> Dict[str, Any]:
    # Test music21 voiceLeading module
    # Case A: Clear Parallel Fifths (C3-G3 moving to D3-A3)
    c1 = music21.chord.Chord(["C3", "G3"])
    c2 = music21.chord.Chord(["D3", "A3"])
    vlq_parallel = music21.voiceLeading.VoiceLeadingQuartet(c1[0], c2[0], c1[1], c2[1])
    is_parallel_fifth = vlq_parallel.parallelFifth()

    # Case B: Contrary Motion to Fifth (C3-G3 moving to B2-F#3 or G2-D3)
    c3 = music21.chord.Chord(["C3", "G3"])
    c4 = music21.chord.Chord(["A2", "E3"])
    vlq_contrary = music21.voiceLeading.VoiceLeadingQuartet(c3[0], c4[0], c3[1], c4[1])
    is_parallel_fifth_contrary = vlq_contrary.parallelFifth()

    # Case C: Voice Crossing (Soprano C4 Alto E4)
    # Soprano starts at C4, Alto starts at A3. In next chord, Soprano goes to D4, Alto jumps to F4 (crosses)
    s1, a1 = music21.note.Note("C4"), music21.note.Note("A3")
    s2, a2 = music21.note.Note("D4"), music21.note.Note("F4")
    vlq_crossing = music21.voiceLeading.VoiceLeadingQuartet(a1, a2, s1, s2)
    is_crossed = vlq_crossing.voiceCrossing()

    # Case D: Hidden / Direct Fifths (similar motion into fifth with soprano leaping)
    s3, b3 = music21.note.Note("C4"), music21.note.Note("C3")
    s4, b4 = music21.note.Note("G4"), music21.note.Note("C2")
    vlq_hidden = music21.voiceLeading.VoiceLeadingQuartet(b3, b4, s3, s4)
    is_hidden_fifth = vlq_hidden.hiddenFifth()

    return {
        "parallel_fifth_detected_correctly": bool(is_parallel_fifth),
        "false_positive_on_contrary_motion": bool(is_parallel_fifth_contrary),
        "voice_crossing_detected_correctly": bool(is_crossed),
        "hidden_fifth_detected_correctly": bool(is_hidden_fifth),
        "music21_builtin_scope": "music21 VoiceLeadingQuartet reliably detects parallel 5ths/8ths and voice crossing pairwise. However, polyphonic 4-part arrangement requires O(N^2) pairwise permutation across all active tracks and cannot resolve polyrhythmic passing tones without custom heuristic timeslicing."
    }

if __name__ == "__main__":
    report = {
        "harmonic_analysis_benchmarks": test_harmonic_cases(),
        "voice_leading_evaluation": test_voice_leading_cases()
    }
    with open("evidence/comprehensive_music_intelligence_benchmarks.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Comprehensive Music Intelligence Test Completed:")
    print(json.dumps(report, indent=2))
