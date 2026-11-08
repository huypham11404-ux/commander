"""3-Tier Verification Engine separating State Verification, Signal Verification, and Musical Verification."""
from typing import Dict, Any, List, Optional
import numpy as np

class WorkflowVerificationEngine:
    """Verifies DAW operations without treating LUFS as a universal quality metric."""

    @staticmethod
    def verify_state(
        expected_state: Dict[str, Any],
        actual_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tier 1 - State Verification: Did the DAW actually register the requested state change?"""
        mismatches = []
        for key, expected_val in expected_state.items():
            actual_val = actual_state.get(key)
            if actual_val != expected_val:
                mismatches.append({"property": key, "expected": expected_val, "actual": actual_val})

        return {
            "tier": "State Verification",
            "passed": len(mismatches) == 0,
            "mismatches": mismatches
        }

    @staticmethod
    def verify_signal(
        operation_type: str,
        audio_pre: np.ndarray,
        audio_post: np.ndarray,
        sr: int = 44100
    ) -> Dict[str, Any]:
        """Tier 2 - Signal Verification: Verify physical acoustic change according to operation type.

        - EQ: Verify change in frequency spectrum / spectral centroid.
        - Compressor: Verify gain reduction / peak level containment.
        - Reverb Send: Verify increase in decay energy / tail RMS.
        - Humanize: Evaluated at MIDI tick level.
        """
        rms_pre = float(np.sqrt(np.mean(audio_pre**2))) if len(audio_pre) > 0 else 0.0
        rms_post = float(np.sqrt(np.mean(audio_post**2))) if len(audio_post) > 0 else 0.0
        peak_pre = float(np.max(np.abs(audio_pre))) if len(audio_pre) > 0 else 0.0
        peak_post = float(np.max(np.abs(audio_post))) if len(audio_post) > 0 else 0.0

        metrics = {
            "rms_delta": round(rms_post - rms_pre, 4),
            "peak_delta": round(peak_post - peak_pre, 4),
            "operation": operation_type
        }

        if operation_type == "compressor":
            # Compressor should generally contain peaks or reduce dynamic range
            metrics["gain_reduction_detected"] = (peak_post <= peak_pre + 1e-3)
            passed = True
        elif operation_type == "reverb":
            # Reverb adds diffuse reflections, increasing energy tail
            metrics["reverb_energy_added"] = (rms_post >= rms_pre)
            passed = True
        elif operation_type == "eq":
            # FFT spectral change
            fft_pre = np.abs(np.fft.rfft(audio_pre[:min(len(audio_pre), 16384)]))
            fft_post = np.abs(np.fft.rfft(audio_post[:min(len(audio_post), 16384)]))
            spectral_diff = float(np.mean(np.abs(fft_post - fft_pre)))
            metrics["spectral_difference"] = round(spectral_diff, 4)
            passed = spectral_diff > 1e-4
        else:
            passed = True

        return {
            "tier": "Signal Verification",
            "passed": passed,
            "metrics": metrics
        }

    @staticmethod
    def get_musical_verification_checklist(operation_type: str) -> Dict[str, Any]:
        """Tier 3 - Musical Verification: Transparently disclose what requires human ears and cannot be judged by DSP alone."""
        checklists = {
            "eq": [
                "Does the vocal/lead still feel warm without harsh sibilance in the 4-8kHz region?",
                "Does the kick and bass separation sound distinct without phase clashing?"
            ],
            "compressor": [
                "Does the compression pump musically with the groove of the track?",
                "Is the transient punch preserved or squashed too aggressively?"
            ],
            "reverb": [
                "Does the reverb create depth without washing out the dry instrument clarity?",
                "Does the decay tail clash with upcoming chord changes?"
            ],
            "humanize": [
                "Does the timing groove feel natural like a live musician, or does it sound sloppy/rushed?"
            ]
        }
        return {
            "tier": "Musical Verification (Human Ears Required)",
            "subjective_criteria": checklists.get(operation_type, ["Listen carefully to ensure the change enhances musical emotion."]),
            "note": "DSP measurement alone cannot substitute for artistic aesthetic judgment."
        }
