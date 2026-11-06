"""Harmony Context Engine resolving music21's modal interchange and voice leading limitations."""
import music21
from typing import Dict, Any, List, Optional

class HarmonyContextEngine:
    def __init__(self, style_mode: str = "modern"):
        self.style_mode = style_mode # "modern" or "classical"

    def analyze_chords_and_key(self, chord_pitches_list: List[List[str]]) -> Dict[str, Any]:
        """Analyze a progression with modal interchange awareness."""
        score = music21.stream.Score()
        part = music21.stream.Part()
        for p_list in chord_pitches_list:
            c = music21.chord.Chord(p_list)
            c.quarterLength = 2.0
            part.append(c)
        score.append(part)

        # 1. Base music21 estimation
        raw_key = score.analyze('key')
        raw_tonic = raw_key.tonic.name
        raw_mode = raw_key.mode

        # 2. Heuristic Context Refinement: check starting/ending tonic stability
        # Modal Interchange rule: If starting chord is C Major triad and progression contains Fm / Ab,
        # Krumhansl-Schmuckler biases towards C minor due to Ab and Eb pitch weights.
        # But tonic center is established by root of first chord and strong functional cadence.
        first_chord = music21.chord.Chord(chord_pitches_list[0]) if chord_pitches_list else None
        last_chord = music21.chord.Chord(chord_pitches_list[-1]) if chord_pitches_list else None

        refined_tonic = raw_tonic
        refined_mode = raw_mode
        modal_interchange_detected = False

        if first_chord and first_chord.isMajorTriad():
            first_root = first_chord.root().name
            if raw_mode == "minor" and raw_tonic == first_root:
                # Potential borrowed minor chords in a major tonic
                refined_tonic = first_root
                refined_mode = "major"
                modal_interchange_detected = True

        chord_analysis = []
        for i, p_list in enumerate(chord_pitches_list):
            c = music21.chord.Chord(p_list)
            chord_analysis.append({
                "step": i,
                "pitches": p_list,
                "root": c.root().name if c.root() else None,
                "common_name": c.commonName,
                "quality": c.quality
            })

        return {
            "raw_music21_key": f"{raw_tonic} {raw_mode}",
            "estimated_key": f"{refined_tonic} {refined_mode}",
            "confidence": round(raw_key.correlationCoefficient, 3),
            "modal_interchange_detected": modal_interchange_detected,
            "chord_details": chord_analysis
        }

    def check_voice_leading(self, part_a: List[str], part_b: List[str]) -> Dict[str, Any]:
        """Check voice leading between two voices pairwise, handling contrary motion properly."""
        if len(part_a) != len(part_b) or len(part_a) < 2:
            return {"violations": [], "summary": "Insufficient notes to analyze"}

        violations = []
        for i in range(len(part_a) - 1):
            n1_a = music21.note.Note(part_a[i])
            n2_a = music21.note.Note(part_a[i+1])
            n1_b = music21.note.Note(part_b[i])
            n2_b = music21.note.Note(part_b[i+1])

            # Measure interval 1 and interval 2
            int1 = music21.interval.Interval(noteStart=n1_a, noteEnd=n1_b)
            int2 = music21.interval.Interval(noteStart=n2_a, noteEnd=n2_b)

            # Check parallel fifth: both are fifths (mod 12 == 7) AND motion is in same direction
            mot_a = n2_a.pitch.ps - n1_a.pitch.ps
            mot_b = n2_b.pitch.ps - n1_b.pitch.ps

            if int1.generic.mod7 == 5 and int2.generic.mod7 == 5:
                # Only a parallel fifth if moving in the same direction!
                if (mot_a > 0 and mot_b > 0) or (mot_a < 0 and mot_b < 0):
                    violations.append({
                        "step": i,
                        "type": "PARALLEL_FIFTH",
                        "voice_a": [part_a[i], part_a[i+1]],
                        "voice_b": [part_b[i], part_b[i+1]]
                    })

            # Check parallel octave
            if int1.generic.mod7 == 1 and int2.generic.mod7 == 1 and int1.cents != 0:
                if (mot_a > 0 and mot_b > 0) or (mot_a < 0 and mot_b < 0):
                    violations.append({
                        "step": i,
                        "type": "PARALLEL_OCTAVE",
                        "voice_a": [part_a[i], part_a[i+1]],
                        "voice_b": [part_b[i], part_b[i+1]]
                    })

        return {
            "violations_count": len(violations),
            "violations": violations,
            "is_clean": len(violations) == 0
        }
