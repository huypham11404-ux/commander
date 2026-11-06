import pytest
import numpy as np
from commander.dsp.pipeline import DspAnalyzer

def test_dsp_pure_sine_wave():
    """Verify DSP measurements on a known 0dBFS peak, 1kHz sine wave."""
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    sine = np.sin(2 * np.pi * 1000 * t).astype(np.float32)

    res = DspAnalyzer.analyze_audio_array(sine, sr=sr)
    m = res["measurements"]

    # Sample peak should be ~1.0
    assert abs(m["sample_peak"] - 1.0) < 0.01
    # RMS of unit sine wave is 1/sqrt(2) = ~0.7071
    assert abs(m["rms"] - 0.7071) < 0.02
    # Crest factor of sine wave is 20*log10(sqrt(2)) = ~3.01 dB
    assert abs(m["crest_factor_db"] - 3.01) < 0.3
    # Spectral centroid should be near 1000 Hz
    assert abs(m["spectral_centroid_hz"] - 1000.0) < 50.0

def test_dsp_stereo_phase_correlation():
    """Verify stereo correlation: +1.0 for mono, -1.0 for out-of-phase."""
    sr = 44100
    t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
    sig = np.sin(2 * np.pi * 440 * t).astype(np.float32)

    # In-phase stereo
    stereo_in = np.column_stack([sig, sig])
    res_in = DspAnalyzer.analyze_audio_array(stereo_in, sr=sr)
    assert abs(res_in["measurements"]["stereo_correlation"] - 1.0) < 0.01

    # Out-of-phase stereo
    stereo_out = np.column_stack([sig, -sig])
    res_out = DspAnalyzer.analyze_audio_array(stereo_out, sr=sr)
    assert abs(res_out["measurements"]["stereo_correlation"] - (-1.0)) < 0.01
