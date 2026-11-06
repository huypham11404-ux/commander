# 4. BÁO CÁO PHÂN TÍCH VÀ ĐỀ XUẤT AI AGENT RUNTIME
*(AI AGENT RUNTIME AUDIT)*

## 1. ĐẶT VẤN ĐỀ VÀ THÁCH THỨC ĐẶC THÙ CỦA SẢN XUẤT ÂM NHẠC

Khác với các tác vụ lập trình (software engineering) hoặc trợ lý văn phòng tổng quát:
- **Ngữ cảnh âm nhạc mang tính đa chiều:** Bao gồm nhịp độ (tempo/BPM), số chỉ nhịp (time signature), điệu tính/giọng (musical key), cấu trúc bài hát (intro, verse, chorus, bridge, outro), phổ tần số (spectral balance), và không gian stereo.
- **Ranh giới sáng tạo và kỹ thuật:** Người dùng cần AI hỗ trợ thực hiện các thao tác tẻ nhạt hoặc gợi ý sáng tạo, nhưng **tuyệt đối không muốn AI tự ý thay thế quyết định thẩm mỹ**.
- **Tính toán tài nguyên khắt khe:** Trên máy Intel Core i3, RAM 8GB, Agent Runtime phải chiếm dưới 100MB RAM và tiêu thụ CPU cực thấp để dành tài nguyên cho DAW và nhạc cụ ảo.

---

## 2. SO SÁNH KIẾN TRÚC AGENT: SINGLE AGENT VS MULTI-AGENT ORCHESTRATION

Trong cộng đồng AI hiện có xu hướng lạm dụng Multi-agent (chia nhỏ thành Composer Agent, Mixing Agent, Track Manager Agent, Lyricist Agent liên tục chat với nhau). Dưới đây là phân tích khách quan:

| Tiêu chí | Multi-Agent Orchestration (Đa tác nhân) | Single Hierarchical Agent with Specialized Tools (Đơn tác nhân phân tầng) |
| :--- | :--- | :--- |
| **Độ trễ phản hồi (Latency)** | **Rất cao (5 - 20 giây)** do nhiều vòng gọi LLM trung gian | **Rất thấp (1 - 3 giây)** chỉ 1 chu kỳ suy luận chính |
| **Tiêu tốn Token & Chi phí** | **Cực cao** (Nhân lên gấp 3 - 5 lần lượng token trao đổi) | **Tối ưu**, tiết kiệm chi phí tối đa cho người dùng |
| **Rủi ro ảo giác (Hallucination)** | Tích lũy sai lệch qua các agent trung gian | Tập trung, kiểm soát chặt bằng Pre-flight checks |
| **Khả năng debug & Rollback** | Cực kỳ khó truy vết agent nào ra quyết định sai | Rõ ràng, nhật ký kiểm toán (audit log) tuyến tính |
| **Tài nguyên phần cứng** | Tốn nhiều RAM và tiến trình | Nhẹ nhàng, vừa vặn trên máy 8GB RAM |

**Kết luận kỹ thuật:** Mô hình **Single Hierarchical Agent with Specialized Skills/Tools** vượt trội hoàn toàn về tốc độ, chi phí và độ tin cậy trong môi trường sản xuất âm nhạc. Không áp dụng multi-agent cồng kềnh một cách cơ học.

---

## 3. MÔ HÌNH NHẬN THỨC VÀ QUY TRÌNH THỰC THI (COGNITIVE EXECUTION LOOP)

Quy trình thực thi của Commander mới được chuẩn hóa theo vòng lặp 5 bước:

```
[1. Tiếp nhận Prompt]
         │
         ▼
[2. Thu thập Ngữ cảnh (DAW Context)] ──> Đọc Key, BPM, Tracks hiện có
         │
         ▼
[3. Lập kế hoạch (Plan & Breakdown)] ──> Chia nhỏ tác vụ, xác định công cụ
         │
         ▼
[4. Kiểm định Nhạc lý (Pre-flight Validation)] ──> Dùng music21/rule-engine kiểm tra âm vực, hòa âm
         │
         ▼
[5. Thực thi qua DAW Adapter & Ghi nhận Undo] ──> Batch transaction vào REAPER
```

### Chi tiết các bước:
1. **Context Enrichment:** Trước khi chuyển prompt cho LLM, hệ thống tự động đính kèm `project_snapshot` (thời lượng, key hiện tại, danh sách track và FX đang mở). Nhờ vậy, LLM không bao giờ phải hỏi lại *"Bài của bạn đang ở tông nào?"*.
2. **Deterministic Pre-flight Validation:** Nếu AI đề xuất viết nốt cho Cello, hệ thống cục bộ (rule-based) sẽ kiểm tra:
   - Các nốt có nằm trong âm vực của Cello (C2 đến C5) hay không?
   - Có nốt nào bị va chạm độ dài (overlapping notes) ngoài ý muốn không?
   - Có xuất hiện lỗi hòa âm cấm kỵ (song song quãng 5/8) không?
   *Nếu vi phạm, hệ thống tự động yêu cầu LLM điều chỉnh hoặc tự sửa bằng thuật toán trước khi ghi vào DAW.*

---

## 4. PROVIDER ABSTRACTION VÀ CHIẾN LƯỢC QUẢN LÝ MÔ HÌNH (LOCAL VS CLOUD)

### 4.1. Lớp trừu tượng hóa nhà cung cấp (Provider Layer)
Hệ thống xây dựng một interface chuẩn `LLMProvider`:
- Hỗ trợ chuẩn API của: **Anthropic (Claude 3.5 Sonnet)**, **OpenAI (GPT-4o)**, **Google (Gemini 1.5 Pro / Flash)**, **DeepSeek**, và các cổng mở rộng như **Groq / OpenRouter**.
- Hỗ trợ local endpoint: **Ollama / llama.cpp** (chuẩn OpenAI-compatible endpoint).

### 4.2. Chiến lược phân bổ tác vụ thông minh (Hybrid Execution)
- **Tác vụ cục bộ (Deterministic / Offline 100%):**
  - Chuyển đổi điệu tính (Transposition).
  - Lượng hóa (Quantization) và làm mềm nốt (Humanization).
  - Phân tích nốt MIDI, nhận diện hợp âm, phát hiện nhịp độ/onset.
  - Kiểm tra âm vực nhạc cụ và keyswitch mapping.
  - Các lệnh DAW cơ bản (thêm track, đổi màu, bật tắt FX, định tuyến tín hiệu).
- **Tác vụ Cloud (AI Reasoning / Deep Creativity):**
  - Hiểu ý định phức tạp từ ngôn ngữ tự nhiên: *"Hãy phối cho tôi một đoạn điệp khúc mang phong cách Cinematic Epic, có dàn dây dồn dập và kết thúc bằng một cú drop êm dịu"*.
  - Sáng tác tiến trình hợp âm và phát triển motif giai điệu mới.
  - Đề xuất bố cục âm thanh (Arrangement) và phân tích cân bằng bản mix (Mix critique).

---

## 5. BỘ NHỚ VÀ QUẢN LÝ PHIÊN LÀM VIỆC (CONTEXT & SESSION MEMORY)

Hệ thống duy trì hai cấp độ bộ nhớ:
1. **Short-term Memory (Bộ nhớ phiên):** Lưu lại lịch sử hội thoại của buổi làm việc hiện tại trong bộ nhớ RAM, tự động cắt tỉa (sliding window kết hợp tóm tắt) để không vượt quá context window.
2. **Long-term Project Memory (`commander_session.json`):** Lưu trữ ngay trong thư mục project của người dùng. Tệp này lưu giữ:
   - Mục tiêu phong cách của bài hát (Genre, Reference tracks).
   - Thiết lập nhạc cụ ưa thích của người dùng.
   - Các quyết định sáng tác đã thống nhất (Key, Scale, Progression, Song structure).
   Khi người dùng mở lại project sau nhiều tuần, Commander đọc tệp này và tiếp tục buổi làm việc với đầy đủ ký ức của dự án.
