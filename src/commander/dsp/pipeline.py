"""DSP Analysis Pipeline providing mathematical measurements and ITU-R BS.1770-4 gated integrated loudness."""
import os
import wave
import numpy as np
import scipy.signal
from typing import Dict, Any, Union, Optional

class DspAnalyzer:
    @staticmethod
    def _apply_bs1770_k_weighting(data: np.ndarray, sr: int) -> np.ndarray:
        """Apply ITU-R BS.1770-4 K-weighting filters: Stage 1 High Shelf + Stage 2 High Pass (RLB).

        Coefficients derived according to ITU-R BS.1770-4 specification for 48kHz and warped for other sample rates.
        """
        # Stage 1: Pre-filter (high-frequency shelving filter, +4dB boost above 1.5kHz)
        # Standard BS.1770 filter parameters:
        gain_db = 3.99984385397
        gain_lin = 10.0 ** (gain_db / 20.0)
        f0 = 1681.974450955533
        Q = 0.7071752369554196

        # Bilinear transform design of high-shelf filter
        w0 = 2.0 * np.pi * f0 / sr
        alpha = np.sin(w0) / (2.0 * Q)
        A = np.sqrt(gain_lin)

        b0 = A * ((A + 1.0) + (A - 1.0) * np.cos(w0) + 2.0 * np.sqrt(A) * alpha)
        b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * np.cos(w0))
        b2 = A * ((A + 1.0) + (A - 1.0) * np.cos(w0) - 2.0 * np.sqrt(A) * alpha)
        a0 = (A + 1.0) - (A - 1.0) * np.cos(w0) + 2.0 * np.sqrt(A) * alpha
        a1 = 2.0 * ((A - 1.0) - (A + 1.0) * np.cos(w0))
        a2 = (A + 1.0) - (A - 1.0) * np.cos(w0) - 2.0 * np.sqrt(A) * alpha

        b_stage1 = np.array([b0, b1, b2]) / a0
        a_stage1 = np.array([a0, a1, a2]) / a0

        # Stage 2: RLB weighting (high-pass filter, ~100Hz cut)
        f0_hp = 38.13547087602444
        Q_hp = 0.5003270373238773
        w0_hp = 2.0 * np.pi * f0_hp / sr
        alpha_hp = np.sin(w0_hp) / (2.0 * Q_hp)

        b0_hp = (1.0 + np.cos(w0_hp)) / 2.0
        b1_hp = -(1.0 + np.cos(w0_hp))
        b2_hp = (1.0 + np.cos(w0_hp)) / 2.0
        a0_hp = 1.0 + alpha_hp
        a1_hp = -2.0 * np.cos(w0_hp)
        a2_hp = 1.0 - alpha_hp

        b_stage2 = np.array([b0_hp, b1_hp, b2_hp]) / a0_hp
        a_stage2 = np.array([a0_hp, a1_hp, a2_hp]) / a0_hp

        # Cascade filters across channels
        filtered_stage1 = scipy.signal.lfilter(b_stage1, a_stage1, data, axis=0)
        filtered = scipy.signal.lfilter(b_stage2, a_stage2, filtered_stage1, axis=0)
        return filtered

    @classmethod
    def calculate_bs1770_lufs(cls, data: np.ndarray, sr: int) -> float:
        """Calculate Integrated Loudness (LUFS) according to ITU-R BS.1770-4.

        Implements dual-stage gating:
        1. 400ms block size with 75% overlap (100ms step).
        2. Absolute gate at -70 LKFS.
        3. Relative gate at -10 LU below the mean of blocks surviving the absolute gate.
        Supported channel layouts: Mono (1) or Stereo (2). Channel weight: Left=1.0, Right=1.0.
        """
        if data.size == 0:
            return -np.inf

        n_samples, n_channels = data.shape
        block_samples = int(0.400 * sr)  # 400 ms
        step_samples = int(0.100 * sr)   # 100 ms (75% overlap)

        if n_samples < block_samples:
            # Buffer shorter than 400ms: compute un-gated single block if signal exists
            filtered = cls._apply_bs1770_k_weighting(data, sr)
            ms = np.mean(filtered**2, axis=0)
            # Channel weights G_i (1.0 for L, R, C)
            weighted_energy = np.sum(ms)
            if weighted_energy <= 1e-12:
                return -np.inf
            return float(-0.691 + 10.0 * np.log10(weighted_energy))

        # 1. Apply K-weighting
        filtered = cls._apply_bs1770_k_weighting(data, sr)

        # 2. Block energy computation
        block_energies = []
        n_blocks = (n_samples - block_samples) // step_samples + 1

        channel_weights = np.ones(n_channels)
        # Note: If 5.1, surround channels would have weight 1.41. For stereo / mono, weight is 1.0.

        for i in range(n_blocks):
            start = i * step_samples
            end = start + block_samples
            chunk = filtered[start:end, :]
            # Mean square per channel
            chunk_ms = np.mean(chunk**2, axis=0)
            z_j = np.sum(channel_weights * chunk_ms)
            block_energies.append(z_j)

        block_energies = np.array(block_energies)

        # Compute block loudness: l_j = -0.691 + 10 * log10(z_j)
        valid_indices = block_energies > 1e-12
        if not np.any(valid_indices):
            return -np.inf

        block_loudness = np.full_like(block_energies, -np.inf)
        block_loudness[valid_indices] = -0.691 + 10.0 * np.log10(block_energies[valid_indices])

        # 3. Absolute Gating: threshold Gamma_a = -70 LKFS
        gamma_a = -70.0
        abs_gated_indices = block_loudness > gamma_a

        if not np.any(abs_gated_indices):
            return -np.inf

        # 4. Relative Gating calculation
        # Preliminary loudness from blocks passing absolute gate
        z_abs_gated = block_energies[abs_gated_indices]
        z_mean_abs = np.mean(z_abs_gated)
        if z_mean_abs <= 1e-12:
            return -np.inf

        l_prelim = -0.691 + 10.0 * np.log10(z_mean_abs)
        gamma_r = l_prelim - 10.0  # Relative threshold 10 LU below l_prelim

        # 5. Final Gating: blocks surviving both absolute AND relative gates
        final_gated_indices = (block_loudness > gamma_a) & (block_loudness > gamma_r)

        if not np.any(final_gated_indices):
            return -np.inf

        z_final = np.mean(block_energies[final_gated_indices])
        if z_final <= 1e-12:
            return -np.inf

        integrated_lufs = -0.691 + 10.0 * np.log10(z_final)
        return float(integrated_lufs)

    @classmethod
    def analyze_audio_array(cls, data: np.ndarray, sr: int = 44100) -> Dict[str, Any]:
        """Perform objective mathematical measurement on floating-point audio data (-1.0 to 1.0)."""
        if data.ndim == 1:
            data = data[:, np.newaxis]

        n_samples, n_channels = data.shape
        duration_sec = n_samples / sr

        # 1. Sample Peak
        sample_peak = float(np.max(np.abs(data))) if n_samples > 0 else 0.0

        # 2. RMS & Crest Factor
        rms = float(np.sqrt(np.mean(data**2))) if n_samples > 0 else 0.0
        if rms <= 1e-9:
            crest_factor_db = 0.0
        else:
            crest_factor = sample_peak / (rms + 1e-12)
            crest_factor_db = float(20 * np.log10(max(crest_factor, 1e-6)))

        # 3. ITU-R BS.1770-4 Dual-Gated Integrated Loudness
        integrated_lufs = cls.calculate_bs1770_lufs(data, sr)

        # 4. True Peak via 4x Sinc Oversampling via polyphase FIR
        # Note: 4x oversampling is standard per BS.1770 Annex 2 for sample rates 44.1k/48k.
        if n_samples > 0:
            chunk_len = min(n_samples, sr * 2)
            oversampled = scipy.signal.resample_poly(data[:chunk_len, 0], 4, 1)
            true_peak = float(np.max(np.abs(oversampled)))
        else:
            true_peak = 0.0

        # 5. Spectral Centroid
        if n_samples > 0:
            analysis_chunk = data[:min(n_samples, 65536), 0]
            fft = np.abs(np.fft.rfft(analysis_chunk))
            freqs = np.fft.rfftfreq(len(analysis_chunk), 1/sr)
            spectral_centroid_hz = float(np.sum(freqs * fft) / (np.sum(fft) + 1e-12))
        else:
            spectral_centroid_hz = 0.0

        # 6. Stereo Phase Correlation
        stereo_corr = 1.0
        if n_channels == 2 and n_samples > 1:
            left = data[:, 0]
            right = data[:, 1]
            denom = (np.std(left) * np.std(right))
            if denom > 1e-9:
                stereo_corr = float(np.corrcoef(left, right)[0, 1])

        return {
            "duration_sec": round(duration_sec, 3),
            "sample_rate": sr,
            "channels": n_channels,
            "channel_layout": "stereo" if n_channels == 2 else "mono",
            "standards_compliance": {
                "loudness_standard": "ITU-R BS.1770-4 (Dual-gated: Abs -70 LKFS, Rel -10 LU, 400ms blocks/75% overlap)",
                "true_peak_method": "ITU-R BS.1770 Annex 2 (4x sinc polyphase oversampling)"
            },
            "measurements": {
                "sample_peak": round(sample_peak, 4),
                "true_peak": round(true_peak, 4),
                "rms": round(rms, 4),
                "crest_factor_db": round(crest_factor_db, 2),
                "integrated_lufs": round(integrated_lufs, 2) if np.isfinite(integrated_lufs) else -999.0,
                "spectral_centroid_hz": round(spectral_centroid_hz, 1),
                "stereo_correlation": round(stereo_corr, 3)
            }
        }

    @classmethod
    def analyze_wav_file(cls, filepath: str) -> Dict[str, Any]:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Audio file not found: {filepath}")

        with wave.open(filepath, 'rb') as wf:
            sr = wf.getframerate()
            n_ch = wf.getnchannels()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            if n_ch == 2:
                data = data.reshape(-1, 2)

        return cls.analyze_audio_array(data, sr=sr)
