"""Harmony Context Engine resolving music21's modal interchange and voice leading limitations, with style profiles and instrument range checks."""
import music21
from typing import Dict, Any, List, Optional

INSTRUMENT_RANGES = {
    "Violin": (55, 103),  # G3 - G7
    "Viola": (48, 91),   # C3 - G6
    "Cello": (36, 76),   # C2 - E5
    "Double Bass": (28, 67), # E1 - G4
    "Piano": (21, 108),  # A0 - C8
    "Bass Guitar": (28, 67) # E1 - G4
}

class HarmonyContextEngine:
    def __init__(self, style_mode: str = "modern"):
        self.style_mode = style_mode # "modern" or "classical"

    def analyze_chords_and_key(self, chord_pitches_list: List[List[str]]) -> Dict[str, Any]:
        """Analyze a chord progression with modal interchange awareness."""
        score = music21.stream.Score()
        part = music21.stream.Part()
        for p_list in chord_pitches_list:
            c = music21.chord.Chord(p_list)
            c.quarterLength = 2.0
            part.append(c)
        score.append(part)

        # 1. Base music21 key estimation
        raw_key = score.analyze('key')
        raw_tonic = raw_key.tonic.name
        raw_mode = raw_key.mode

        # 2. Heuristic Context Refinement
        first_chord = music21.chord.Chord(chord_pitches_list[0]) if chord_pitches_list else None
        refined_tonic = raw_tonic
        refined_mode = raw_mode
        modal_interchange_detected = False

        if first_chord and first_chord.isMajorTriad():
            first_root = first_chord.root().name
            if raw_mode == "minor" and raw_tonic == first_root:
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
                "quality": c.quality,
                "inversion": c.inversion()
            })

        return {
            "raw_music21_key": f"{raw_tonic} {raw_mode}",
            "estimated_key": f"{refined_tonic} {refined_mode}",
            "confidence": round(raw_key.correlationCoefficient, 3),
            "modal_interchange_detected": modal_interchange_detected,
            "chord_details": chord_analysis
        }

    def check_voice_leading(self, part_a: List[str], part_b: List[str]) -> Dict[str, Any]:
        """Check voice leading pairwise, distinguishing contrary, similar, parallel, and oblique motion."""
        if len(part_a) != len(part_b) or len(part_a) < 2:
            return {"violations": [], "summary": "Insufficient notes to analyze"}

        violations = []
        motion_types = []

        for i in range(len(part_a) - 1):
            n1_a = music21.note.Note(part_a[i])
            n2_a = music21.note.Note(part_a[i+1])
            n1_b = music21.note.Note(part_b[i])
            n2_b = music21.note.Note(part_b[i+1])

            int1 = music21.interval.Interval(noteStart=n1_a, noteEnd=n1_b)
            int2 = music21.interval.Interval(noteStart=n2_a, noteEnd=n2_b)

            mot_a = n2_a.pitch.ps - n1_a.pitch.ps
            mot_b = n2_b.pitch.ps - n1_b.pitch.ps

            # Classify motion
            if mot_a == 0 and mot_b == 0:
                m_type = "NO_MOTION"
            elif mot_a == 0 or mot_b == 0:
                m_type = "OBLIQUE"
            elif (mot_a > 0 and mot_b < 0) or (mot_a < 0 and mot_b > 0):
                m_type = "CONTRARY"
            elif mot_a == mot_b:
                m_type = "PARALLEL"
            else:
                m_type = "SIMILAR"
            motion_types.append(m_type)

            # Check parallel fifth: interval is 5th/12th AND motion is parallel or similar in same direction
            if int1.generic.mod7 == 5 and int2.generic.mod7 == 5:
                if (mot_a > 0 and mot_b > 0) or (mot_a < 0 and mot_b < 0):
                    violations.append({
                        "step": i,
                        "type": "PARALLEL_FIFTH",
                        "motion": m_type,
                        "voice_a": [part_a[i], part_a[i+1]],
                        "voice_b": [part_b[i], part_b[i+1]]
                    })

            # Check parallel octave
            if int1.generic.mod7 == 1 and int2.generic.mod7 == 1 and int1.cents != 0:
                if (mot_a > 0 and mot_b > 0) or (mot_a < 0 and mot_b < 0):
                    violations.append({
                        "step": i,
                        "type": "PARALLEL_OCTAVE",
                        "motion": m_type,
                        "voice_a": [part_a[i], part_a[i+1]],
                        "voice_b": [part_b[i], part_b[i+1]]
                    })

            # Check voice crossing
            if n1_a.pitch.ps <= n1_b.pitch.ps and n2_a.pitch.ps > n2_b.pitch.ps:
                violations.append({
                    "step": i,
                    "type": "VOICE_CROSSING",
                    "voice_a": [part_a[i], part_a[i+1]],
                    "voice_b": [part_b[i], part_b[i+1]]
                })

        return {
            "violations_count": len(violations),
            "violations": violations,
            "motion_types": motion_types,
            "is_clean": len(violations) == 0
        }

    @staticmethod
    def validate_instrument_range(instrument_name: str, pitches: List[str]) -> Dict[str, Any]:
        """Validate whether notes fall within physical playable range of instrument."""
        if instrument_name not in INSTRUMENT_RANGES:
            return {"valid": True, "note": f"No range constraints defined for {instrument_name}"}

        min_p, max_p = INSTRUMENT_RANGES[instrument_name]
        out_of_range = []
        for p in pitches:
            n = music21.note.Note(p)
            if n.pitch.midi < min_p or n.pitch.midi > max_p:
                out_of_range.append({"pitch": p, "midi": n.pitch.midi})

        return {
            "valid": len(out_of_range) == 0,
            "instrument": instrument_name,
            "range": (min_p, max_p),
            "out_of_range_notes": out_of_range
        }
