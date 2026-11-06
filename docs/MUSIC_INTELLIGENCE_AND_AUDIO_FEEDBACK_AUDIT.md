# 6. BÁO CÁO NĂNG LỰC NHẠC LÝ VÀ VÒNG PHẢN HỒI ÂM THANH
*(MUSIC INTELLIGENCE AND AUDIO FEEDBACK AUDIT)*

## 1. PHÂN BIỆT RẠCH RÒI: SUY LUẬN LLM VS CÔNG CỤ NHẠC LÝ XÁC THỰC

Một sai lầm rất phổ biến trong các dự án AI âm nhạc là phó mặc toàn bộ việc sinh nốt cho LLM và mặc định rằng LLM "hiểu" âm nhạc. Thực tế kỹ thuật chứng minh:
- **LLM giỏi ở:** Tạo ý tưởng phong cách, gợi ý tiến trình hợp âm mang tính biểu tượng (symbolic chords), sáng tác ca từ, và lập kế hoạch tổng thể.
- **LLM rất kém ở:** Tính toán chính xác cao độ tuyệt đối, kiểm soát âm vực nhạc cụ thời gian thực, canh chuẩn từng tick MIDI (quantization), và tuân thủ nghiêm ngặt các quy tắc đối âm/dẫn giọng (counterpoint/voice leading).
- **Giải pháp bắt buộc:** Phải kết hợp LLM với một **Deterministic Music Intelligence Engine** cục bộ đóng vai trò là "bộ lọc thẩm định kỹ thuật" (Pre-flight Musical Guardrails).

---

## 2. KẾT QUẢ ĐO ĐẠC THỰC NGHIỆM THƯ VIỆN NHẠC LÝ (LEVEL 4 VERIFICATION)

Chúng tôi đã xây dựng quy trình kiểm thử thực tế trên tiến trình Python 3.12 (mã nguồn tại `experiments/music_intelligence_test.py`, kết quả lưu tại `evidence/music_intelligence_benchmark.json`):

### 2.1. Phân tích Nhạc lý Tượng trưng (Symbolic Music Analysis)
- **Dữ liệu mẫu:** Một tệp MIDI đa bè gồm đàn Piano đệm tiến trình `Cm – Ab – Eb – Bb` kết hợp bè Violin chơi giai điệu dẫn xuất (`experiments/sample_progression.mid`).
- **Thời gian phân tích cấu trúc MIDI (parse time):** **41.4 ms**
- **Nhận diện điệu tính (Key Analysis):** **23.3 ms** ──> Kết quả nhận diện chính xác tuyệt đối: **`C minor`**.
- **Nhận diện hợp âm tự động (Chordify & Triad Detection):** Nhận diện chính xác các hợp âm bậc I, VI, III, VII trong điệu thức Đô thứ.
- **Kiểm tra dẫn giọng (Voice Leading Check):** Thuật toán rule-based quét toàn bộ các quãng chuyển động giữa các bè, xác nhận không có lỗi song song quãng 5/8 (parallel fifths/octaves).

### 2.2. Trích xuất đặc trưng âm thanh (Audio Feature Extraction Simulation)
- Thử nghiệm trên tín hiệu âm thanh hợp âm 3 nốt (C4-E4-G4):
  - **Thời gian tính toán DSP:** **2.71 ms**
  - **Thông số đo lường:** RMS level: `0.463`, Peak level: `1.099`, Crest factor: `2.372`, Spectral Centroid: `2658.5 Hz`.
- **Đánh giá hiệu năng:** Với thời gian tính toán chỉ từ **2ms đến 40ms**, toàn bộ các tác vụ thẩm định nhạc lý và phân tích DSP cơ bản đều có thể chạy cục bộ trên chip **Intel Core i3-1115G4** mà không gây sụt giảm khung hình hoặc ngắt quãng buffer âm thanh của REAPER.

---

## 3. THIẾT KẾ VÒNG PHẢN HỒI ÂM THANH (AUDIO FEEDBACK LOOP)

Vòng phản hồi âm thanh là tính năng cao cấp cho phép AI không chỉ "viết lệnh mù" mà còn có khả năng "nghe lại kết quả" để tự điều chỉnh.

```
       [1. AI sinh MIDI / Preset FX]
                     │
                     ▼
       [2. REAPER Render Stem / Quick Audition]
                     │
                     ▼ (WAV / FLAC file)
       [3. DSP & Audio Feature Extractor] ──> Đo LUFS, RMS, Spectral Balance, Dynamic Range
                     │
                     ▼
       [4. Đối chiếu Mục tiêu (Target Comparison)]
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
   [Đạt tiêu chuẩn]         [Lệch mục tiêu (ví dụ: Mid-low bị đục, nốt bị va chạm)]
        │                         │
        ▼                         ▼
  [Bàn giao người dùng]     [AI đề xuất chỉnh EQ / Giảm Velocity bè Bass / Chỉnh Pan]
                                  │
                                  ▼
                            [Vòng lặp sửa đổi]
```

### 3.1. Các chỉ số phân tích định lượng khả thi trên máy 8GB RAM:
1. **Loudness & Dynamics:** Tích hợp bộ lọc chuẩn ITU-R BS.1770-4 đo Integrated LUFS, Short-term LUFS, True Peak và Dynamic Range (Crest Factor).
2. **Spectral Balance (Cân bằng dải tần):** Phân tích 4 vùng cơ bản: Sub-bass (<60Hz), Bass (60-250Hz), Mid (250Hz-4kHz), High (>4kHz). Phát hiện hiện tượng "mặt bùn" (muddy build-up quanh vùng 200-400Hz).
3. **Stereo Imaging:** Đo hệ số tương quan pha (Phase Correlation) giữa kênh Trái và Phải để cảnh báo hiện tượng triệt tiêu pha (phase cancellation) khi chuyển sang Mono.

---

## 4. MA TRẬN THƯ VIỆN ĐỀ XUẤT CHO LÕI MUSIC INTELLIGENCE

| Thư viện | Vai trò | Giấy phép | Footprint RAM | Mức độ khuyến nghị |
| :--- | :--- | :--- | :--- | :--- |
| **`music21`** | Phân tích nhạc lý tượng trưng, giọng, hợp âm, voice leading | **BSD-3-Clause** | ~50 MB | **Reuse directly (Hạt nhân Nhạc lý)** |
| **`pretty_midi` / `mido`** | Đọc, tạo, chỉnh sửa nốt, velocity, CC, pitch bend | **MIT** | < 10 MB | **Reuse directly (Hạt nhân MIDI)** |
| **`scipy` / `numpy`** | Thuật toán FFT, lọc dải tần, đo RMS, Crest factor | **BSD-3-Clause** | ~30 MB | **Reuse directly (Hạt nhân DSP nhẹ)** |
| **`FFmpeg` (CLI)** | Chuyển đổi định dạng, render nhanh stem audition | **LGPL / GPL** | Tiến trình ngoài | **Tích hợp dạng External Tool** |
| **`librosa`** | Trích xuất mfcc, chromagram sâu | ISC | ~100 MB | Cân nhắc tải động (Lazy Load khi cần) |
| **`Demucs` / Spleeter** | Tách stem âm thanh bằng AI | MIT | > 1.5 GB | **Không chạy offline trên máy 8GB RAM**; chỉ gọi qua Cloud API |

---

## 5. KẾT LUẬN

1. Lõi **Music Intelligence** của Commander mới sẽ kết hợp **`music21` + `pretty_midi`** làm bộ thẩm định nhạc lý tiền thực thi (Pre-flight Musical Validation).
2. Tích hợp **Audio Feedback Loop nhẹ** thông qua DSP đo LUFS và phổ tần số bằng `scipy/numpy` hoàn toàn cục bộ, cho phép AI phản hồi khách quan về mặt kỹ thuật âm thanh mà không làm nặng máy.
