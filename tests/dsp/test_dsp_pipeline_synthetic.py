import pytest
import numpy as np
from commander.dsp.pipeline import DspAnalyzer

def test_dsp_silence():
    """Verify DSP measurements on complete digital silence."""
    sr = 44100
    silence = np.zeros(sr, dtype=np.float32)
    res = DspAnalyzer.analyze_audio_array(silence, sr=sr)
    m = res["measurements"]
    assert m["sample_peak"] == 0.0
    assert m["rms"] == 0.0
    assert m["integrated_lufs"] < -100.0

def test_dsp_clipping_detection():
    """Verify that inter-sample true peak detects overs when clipped at 1.0."""
    sr = 44100
    t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
    # Synthesize two close high-amplitude frequencies that create inter-sample peaks
    sig = 0.95 * np.sin(2 * np.pi * 10000 * t) + 0.1 * np.sin(2 * np.pi * 10500 * t)
    sig = np.clip(sig, -1.0, 1.0).astype(np.float32)

    res = DspAnalyzer.analyze_audio_array(sig, sr=sr)
    m = res["measurements"]
    assert m["sample_peak"] <= 1.0
    assert m["true_peak"] >= 0.95

def test_dsp_multiple_sample_rates():
    """Verify DSP works accurately across 44.1kHz, 48kHz, and 96kHz."""
    for test_sr in [44100, 48000, 96000]:
        t = np.linspace(0, 0.5, int(test_sr * 0.5), endpoint=False)
        sig = 0.5 * np.sin(2 * np.pi * 1000 * t).astype(np.float32)
        res = DspAnalyzer.analyze_audio_array(sig, sr=test_sr)
        assert abs(res["measurements"]["spectral_centroid_hz"] - 1000.0) < 50.0
