# DSP ANALYSIS SPECIFICATION
## Subsystem: Quantitative DSP Pipeline

### 1. Mathematical Standards
1. **Sample Peak:** $\max(|x[n]|)$, calculated over all channels.
2. **True Peak (4x Sinc Oversampling):** Oversample by a factor of 4 using `scipy.signal.resample_poly` with polyphase FIR filtering to detect inter-sample peaks exceeding 0 dBFS.
3. **RMS Level:** $\sqrt{\frac{1}{N} \sum_{n=0}^{N-1} x[n]^2}$.
4. **Crest Factor (dB):** $20 \log_{10} \left( \frac{\text{Sample Peak}}{\text{RMS} + \epsilon} \right)$.
5. **ITU-R BS.1770-4 Dual-Gated Integrated Loudness:**
   - Stage 1: High-shelf pre-filter (+4dB at ~1.5kHz).
   - Stage 2: High-pass RLB filter (~100Hz).
   - Partitioning: 400 ms blocks with 75% overlap (100 ms step).
   - Absolute Gating: Exclusion of blocks below $-70\text{ LKFS}$.
   - Relative Gating: Exclusion of blocks below $\Gamma_r = L_{\text{prelim}} - 10\text{ LU}$.
   - Channel Weighting: Left = 1.0, Right = 1.0 (Supported layout: Mono and Stereo).
6. **Spectral Centroid (Hz):** $\frac{\sum_{k} f_k \cdot |X[k]|}{\sum_{k} |X[k]| + \epsilon}$.
7. **Stereo Phase Correlation:** $\rho = \frac{\sum (L - \bar{L})(R - \bar{R})}{\sqrt{\sum (L - \bar{L})^2 \sum (R - \bar{R})^2}}$, range $[-1.0, +1.0]$. For mono signals, $\rho = +1.0$.

### 2. Constraints & Principles
- All measurements are strictly mathematical and objective.
- Subjective adjectives (e.g. "warm", "muddy", "harsh", "airy") are strictly forbidden in this measurement layer.
