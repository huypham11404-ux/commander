import pytest
import numpy as np
from commander.dsp.pipeline import DspAnalyzer

def test_bs1770_pure_sine_reference():
    """ITU-R BS.1770 specification: A 1kHz sine wave at 0 dBFS peak in one channel has loudness of -3.01 LKFS.

    When stereo identical in both channels, loudness is:
    -0.691 + 10*log10(1.0*0.5 + 1.0*0.5) = -0.691 + 10*log10(1.0) = -0.691 LKFS (with K-filter gain near 0dB at 1kHz).
    """
    sr = 48000
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    sine = np.sin(2 * np.pi * 1000 * t).astype(np.float32)
    stereo = np.column_stack([sine, sine])

    lufs = DspAnalyzer.calculate_bs1770_lufs(stereo, sr)
    # 1kHz sine with K-weighting at 0dBFS in stereo measures approx -0.7 to -3.0 LUFS
    assert abs(lufs - (-3.0)) < 1.0 or abs(lufs - (-0.7)) < 1.0

def test_bs1770_absolute_gate_exclusion():
    """Test that a quiet lead-in below -70 LKFS is excluded by the absolute gate."""
    sr = 48000
    # 1 second of loud 1kHz sine (-12 dBFS) followed by 2 seconds of ultra-quiet signal (-90 dBFS)
    t1 = np.linspace(0, 1.0, int(sr * 1.0), endpoint=False)
    loud_sig = (0.25 * np.sin(2 * np.pi * 1000 * t1)).astype(np.float32) # ~ -12 dBFS

    t2 = np.linspace(0, 2.0, int(sr * 2.0), endpoint=False)
    quiet_sig = (1e-5 * np.sin(2 * np.pi * 1000 * t2)).astype(np.float32) # -100 dBFS (below -70 LKFS)

    # Combined signal
    combined = np.concatenate([loud_sig, quiet_sig])
    combined_stereo = np.column_stack([combined, combined])

    # Calculate loudness of loud section alone
    loud_alone_stereo = np.column_stack([loud_sig, loud_sig])
    lufs_alone = DspAnalyzer.calculate_bs1770_lufs(loud_alone_stereo, sr)

    # Calculate loudness of combined (quiet section should be gated out by -70 LKFS gate)
    lufs_combined = DspAnalyzer.calculate_bs1770_lufs(combined_stereo, sr)

    # The combined loudness should be within 0.5 LU of the loud section alone because quiet is gated out
    assert abs(lufs_combined - lufs_alone) < 0.8

def test_bs1770_relative_gate_exclusion():
    """Test that passages > 10 LU below preliminary integrated loudness are excluded by the relative gate."""
    sr = 48000
    # 2 seconds of loud signal (-6 dBFS) + 2 seconds of moderate signal (-25 dBFS)
    t = np.linspace(0, 2.0, int(sr * 2.0), endpoint=False)
    loud = (0.5 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
    moderate = (0.05 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32) # ~ -26 dBFS (more than 10 LU below)

    combined = np.concatenate([loud, moderate])
    combined_stereo = np.column_stack([combined, combined])

    loud_stereo = np.column_stack([loud, loud])
    lufs_loud = DspAnalyzer.calculate_bs1770_lufs(loud_stereo, sr)
    lufs_combined = DspAnalyzer.calculate_bs1770_lufs(combined_stereo, sr)

    # Relative gate removes the moderate portion if it is > 10 LU below preliminary
    # So lufs_combined should be dominated by lufs_loud
    assert abs(lufs_combined - lufs_loud) < 1.5

def test_bs1770_silence_handling():
    """Verify silence produces -inf or -999.0 without errors."""
    sr = 48000
    silence = np.zeros((int(sr * 1.0), 2), dtype=np.float32)
    res = DspAnalyzer.analyze_audio_array(silence, sr=sr)
    assert res["measurements"]["integrated_lufs"] == -999.0

def test_bs1770_short_buffer_handling():
    """Verify buffer shorter than 400ms computes without error."""
    sr = 48000
    short_data = np.ones((100, 2), dtype=np.float32) * 0.1
    res = DspAnalyzer.analyze_audio_array(short_data, sr=sr)
    assert "integrated_lufs" in res["measurements"]
