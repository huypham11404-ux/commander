# 11. LỘ TRÌNH TRIỂN KHAI VÀ CHUYỂN ĐỔI THEO TỪNG GIAI ĐOẠN
*(MIGRATION AND IMPLEMENTATION ROADMAP)*

## 1. NGUYÊN TẮC VÀ ĐỊNH HƯỚNG PHÁT TRIỂN

Dựa trên phản hồi và thống nhất chiến lược với người dùng, dự án AI Music Production Commander được thực hiện theo nguyên tắc **A: Ưu tiên xây dựng nền tảng điều khiển DAW ổn định, an toàn và có khả năng rollback trước**, sau đó từng bước tích hợp các lớp Music Intelligence và Intelligent Workflow.

Dự án được chia thành **4 Giai đoạn phát triển tuần tự (Phases)**, mỗi giai đoạn có tiêu chí nghiệm thu (Acceptance Criteria) độc lập và có thể kiểm thử tự động.

---

## 2. CHI TIẾT 4 GIAI ĐOẠN TRIỂN KHAI

### GIAI ĐOẠN 1: COMMANDER FOUNDATION (NỀN TẢNG CỐT LÕI & GIAO THỨC AN TOÀN)
- **Mục tiêu:** Xây dựng bộ khung điều phối Agent, lớp trừu tượng nhà cung cấp AI, hệ thống phân quyền 3 cấp và cơ chế giao dịch hoàn tác an toàn.
- **Các nhiệm vụ cụ thể:**
  1. Xây dựng **Core Agent Runtime** bằng Python 3.12 với Clean Architecture.
  2. Xây dựng **Provider Abstraction Layer** hỗ trợ Claude, OpenAI GPT, Google Gemini và Local llama.cpp/Ollama.
  3. Xây dựng **Tool Registry & Permission Layer** với 3 cấp độ: `Read-only`, `Proposed-change`, `Direct-edit`.
  4. Chuẩn hóa interface trừu tượng **`IDawAdapter`** và định nghĩa schema **Commander Protocol v1.0**.
  5. Xây dựng **Reaper Native Driver** kế thừa cơ chế Atomic File-based Swap từ `Reaper-MCP`.
  6. Xây dựng cơ chế **Transaction & Rollback Engine**: Bọc toàn bộ batch lệnh vào khối `Undo_BeginBlock2 / Undo_EndBlock2`.
  7. Thiết lập hệ thống kiểm toán (Audit Trail) ghi nhật ký toàn bộ lệnh.
- **Tiêu chí nghiệm thu (Acceptance Criteria):**
  - Thực hiện gửi batch 5 lệnh vào REAPER thành công.
  - Thử nghiệm cố tình tạo lỗi ở lệnh thứ 4, hệ thống phải tự động rollback 100% trạng thái project trong vòng dưới 1ms mà không để lại dữ liệu rác.

---

### GIAI ĐOẠN 2: DAW AUTOMATION (TỰ ĐỘNG HÓA TOÀN DIỆN REAPER)
- **Mục tiêu:** Hoàn thiện bộ công cụ điều khiển DAW phong phú, cho phép AI thao tác mượt mà trên toàn bộ các thành phần của REAPER.
- **Các nhiệm vụ cụ thể:**
  1. **Project Inspection:** Đọc chính xác BPM, Key, Time Signature, danh sách Track, Marker, Region đang mở trong REAPER.
  2. **Track Management:** Tạo, đổi tên, phân cấp folder track (Folder Depth), đổi màu, chỉnh volume fader, pan, mute, solo.
  3. **FX & Plugin Management:** Nạp VST/VST3/JSFX, quét danh mục plugin (`vst_plugins.ini`), đọc/ghi thông số hiệu ứng (parameters cache).
  4. **Routing & Sends:** Thiết lập send/receive audio, bus group, sidechain routing.
  5. **Transport Control:** Play, pause, stop, set playhead cursor, loop range.
  6. **MIDI/Audio Items:** Tạo MIDI item, nạp nốt, di chuyển item, phân chia (split), kéo dài (stretch).
- **Tiêu chí nghiệm thu:**
  - AI có thể tạo một dàn nhạc mẫu (Template) gồm 8 track (Drums, Bass, Piano, Strings, Vocal) với màu sắc và routing bus hoàn chỉnh chỉ bằng một câu lệnh tự nhiên trong vòng dưới 2 giây.

---

### GIAI ĐOẠN 3: MUSIC INTELLIGENCE FOUNDATION (HẠT NHÂN NHẠC LÝ TỰ THÂN)
- **Mục tiêu:** Tích hợp bộ quy tắc nhạc lý xác thực (Deterministic Music Theory Engine) hoàn toàn offline, đóng vai trò là "người gác cổng âm nhạc" (Musical Guardrails).
- **Các nhiệm vụ cụ thể:**
  1. Tích hợp thư viện **`music21`** và **`pretty_midi`** vào phân hệ Music Intelligence.
  2. Xây dựng thuật toán nhận diện điệu thức (Key Detection) và phân tích hợp âm (Chord Roman Numeral Analysis) từ tệp MIDI hoặc các nốt hiện có trên timeline.
  3. Xây dựng **Pre-flight Musical Guardrails:**
     - Tự động kiểm tra và ngăn chặn các lỗi hòa âm cấm kỵ (quãng 5 và quãng 8 song song giữa các bè).
     - Kiểm tra và sửa các nốt va chạm (overlapping clashes).
     - Tự động chuyển đổi điệu tính (Transposition) và chỉnh âm giai (Scale alignment).
  4. Xây dựng **Instrument Skills Engine:**
     - Thiết lập cấu hình nhạc cụ ảo (Pianoteq, LASS 3 Strings, Ample Guitar, Native Drums...).
     - Tự động gán keyswitch cho từng kỹ thuật (Staccato, Legato, Pizzicato).
- **Tiêu chí nghiệm thu:**
  - Khi AI sinh một đoạn bè dây 4 bè, hệ thống nhạc lý quét và thẩm định toàn bộ nốt trong vòng dưới 50ms, bảo đảm không có nốt vượt khỏi âm vực nhạc cụ và không có lỗi quãng 5 song song trước khi ghi vào REAPER.

---

### GIAI ĐOẠN 4: INTELLIGENT MUSIC WORKFLOW & AUDIO FEEDBACK LOOP (SẢN XUẤT ÂM NHẠC THÔNG MINH HOÀN THIỆN)
- **Mục tiêu:** Kết nối hoàn chỉnh giữa trí tuệ nhân tạo, nhạc lý xác thực và vòng phản hồi âm thanh trong giao diện Desktop trực quan.
- **Các nhiệm vụ cụ thể:**
  1. **Đóng gói Giao diện Desktop (Tauri v2 + Svelte):** Tích hợp Chat streaming, Timeline tiến trình, Project Inspector và khung Phê duyệt (Approval Dialog).
  2. **Mini Piano Roll Preview:** Cho phép xem nhanh các nốt MIDI ngay trên giao diện trước khi chấp thuận.
  3. **Audio Feedback Loop:**
     - Tích hợp lệnh yêu cầu REAPER render stem nhanh đoạn nhạc vừa tạo.
     - Dùng DSP nhẹ (`scipy / numpy`) đo LUFS, Crest Factor, phổ tần số (Spectral Centroid) và tương quan pha (Phase Correlation).
     - AI đọc kết quả đo lường và đưa ra nhận xét hòa âm/mixing khách quan: *"Đoạn Bass đang hơi lấn dải 150Hz của Kick, tôi đề xuất hạ nhẹ EQ ở 180Hz (-2dB, Q=1.4)"*.
  4. **Kiểm thử trên thiết bị phần cứng thật:** Chạy thử nghiệm thực tế trên máy Windows với REAPER và bàn phím MIDI **Nektar LX25+**.
- **Tiêu chí nghiệm thu:**
  - Hoàn thành trọn vẹn một quy trình sản xuất một đoạn điệp khúc bài hát từ số 0 đến bản mix cơ bản thông qua ngôn ngữ tự nhiên, đáp ứng chuẩn thẩm mỹ và an toàn tuyệt đối.

---

## 3. BẢNG TIẾN ĐỘ VÀ PHÂN BỔ NGUỒN LỰC DỰ KIẾN

| Giai đoạn (Phase) | Trọng tâm công việc | Thời gian ước tính | Tỷ lệ tái sử dụng mã nguồn |
| :--- | :--- | :--- | :--- |
| **Phase 1: Foundation** | Agent Core, Provider Layer, IDawAdapter, Reaper File IPC, Undo Rollback | Tuần 1 - 2 | 70% (Kế thừa từ Reaper-MCP) |
| **Phase 2: DAW Automation** | Track/FX/Routing/Transport Tools, Parameter Cache | Tuần 3 - 4 | 80% (Kế thừa từ Reaper-MCP & reapy-mcp) |
| **Phase 3: Music Intelligence**| music21 Guardrails, Voice leading, Key/Chord, Instrument Skills | Tuần 5 - 6 | 60% (Kế thừa music21, tự viết Skills Engine) |
| **Phase 4: Workflow & Audio**  | Tauri Desktop UI, Audition Player, DSP Audio Feedback Loop | Tuần 7 - 8 | 50% (Tauri, DSP scipy, tự xây dựng UI) |
