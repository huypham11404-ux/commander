# 2. BÁO CÁO PHÂN TÍCH KIẾN TRÚC AURALINK VÀ MÔ HÌNH SẢN PHẨM CÔNG KHAI
*(AURALINK ARCHITECTURE AUDIT)*

## 1. TỔNG QUAN VÀ BỐI CẢNH

Theo khảo sát từ cổng thông tin chính thức `https://auralink.io.vn/` và các tài liệu phát hành công khai (Releases v2.2.0):
- **AuraLink Studio** là một hệ sinh thái phần mềm desktop chuyên biệt cho sản xuất âm thanh, bao gồm 8 sản phẩm (AuraLink Router, AI Reaper Commander, Chroma Studio, Cadence, Tri Âm Zhiyin, và các ứng dụng bảo mật/mệnh lý).
- Trong đó, hạt nhân liên quan trực tiếp đến đề tài này là **AI Reaper Commander (v2.2.0)** với trợ lý mang tên mã **"Amadeus"**.
- Tình trạng phân phối: Đóng gói dưới dạng nhị phân độc lập cho Windows (60.7 MB) và macOS (73.8 MB), cung cấp giấy phép kích hoạt miễn phí qua Telegram Bot. Không phát hành kho mã nguồn công khai (Closed Source).

---

## 2. PHÂN TÍCH KIẾN TRÚC VÀ TÍNH NĂNG ĐƯỢC XÁC MINH CÔNG KHAI

Từ tài liệu kỹ thuật, mô tả tính năng và giao diện công bố (`shot-ai-reaper-vi.webp`, trang sản phẩm), kiến trúc của AI Reaper Commander thể hiện rõ các năng lực cốt lõi sau:

### 2.1. Trợ lý âm nhạc "Amadeus" và Luồng tương tác hai chiều
1. **Tiếp nhận ngôn ngữ tự nhiên:** Người dùng ra lệnh bằng lời thông thường: *"Thêm bè dây bốn bè cho điệp khúc: Cm – Ab – Eb – Bb, 8 ô nhịp, lớn dần tới forte"*.
2. **Đọc ngữ cảnh Project (Project Context Inspection):** Đọc trực tiếp project đang mở trong REAPER: Key (giọng), BPM (tempo), danh sách track, cấu trúc markers, và hợp âm hiện hữu.
3. **Music Intelligence & Pre-flight Inspection:**
   - Viết các bè tương ứng (Violin I, Violin II, Viola, Cello).
   - Kiểm tra âm vực (pitch range của từng nhạc cụ), quy tắc dẫn giọng (voice leading), tránh các lỗi hòa âm kinh điển (quãng 5/8 song song), phân bố lực độ (velocity curve) và pedal biểu cảm.
4. **Thực thi vào REAPER:** Chuyển toàn bộ 128 nốt MIDI, CC data vào track trong REAPER chỉ trong một chu kỳ thực thi.
5. **Khả năng hoàn tác (Undo Transaction):** Toàn bộ thao tác hàng trăm nốt và nhiều track được gói gọn trong **một lần `Ctrl+Z` duy nhất**, bảo đảm an toàn dữ liệu và trải nghiệm tức thì.

### 2.2. Kỹ năng nhạc cụ (Instrument Skills & Articulations)
- Hệ thống hỗ trợ "kỹ năng" theo từng nhạc cụ ảo phổ biến: Pianoteq, LASS 3 (string library), Ample Guitar/Bass, Studio Drummer, và cả nhạc cụ truyền thống Á Đông (đàn tranh, cổ cầm, sáo).
- Cơ chế này cho phép AI sinh nốt đúng với dải phím điều khiển (keyswitches, articulations: staccato, legato, pizzicato, vibrato) của từng thư viện âm thanh cụ thể thay vì chỉ xuất nốt MIDI thô.

### 2.3. Hỗ trợ đa nhà cung cấp mô hình (Multi-Provider AI Abstraction)
- Hỗ trợ linh hoạt: Gemini (miễn phí), OpenAI GPT, Anthropic Claude (đặc biệt khuyến nghị Claude Sonnet cho việc phối khí trọn vẹn), DeepSeek, NVIDIA NIM và OpenRouter.
- Người dùng tự quản lý API Key cục bộ, không ép buộc một nhà cung cấp duy nhất.

### 2.4. Lưu & mở lại phiên làm việc (Session Management)
- Lưu trữ ngữ cảnh hội thoại, lịch sử trao đổi và trạng thái project để khi người dùng mở lại project trong các phiên tiếp theo, AI vẫn nắm được ý đồ sáng tác trước đó.

---

## 3. ĐỐI CHIẾU VỚI CÁC DỰ ÁN MÃ NGUỒN MỞ HIỆN HỮU

| Tiêu chí | Auralink (AI Reaper Commander v2.2.0) | Các dự án MCP mã nguồn mở (Reaper-MCP, reapy-mcp) |
| :--- | :--- | :--- |
| **Giao diện Desktop** | Có UI chuyên biệt (Desktop Chat, Inspector, Project View) | Chạy ngầm Stdio / Dựa vào Claude Desktop UI hoặc CLI |
| **Kiểm tra Nhạc lý (Pre-flight Music Check)** | Có (Kiểm tra âm vực nhạc cụ, nốt chồng, voice leading) | Phần lớn chưa có, chỉ đẩy nốt MIDI cơ bản do LLM sinh ra |
| **Instrument Articulation & Keyswitch** | Có module kỹ năng nhạc cụ ảo chuyên biệt (LASS 3, Ample, Pianoteq...) | Phải mô tả thủ công qua Prompt của người dùng |
| **Tích hợp Transaction Undo** | Hoàn tác 1 chạm (Ctrl+Z nguyên cụm) | Reaper-MCP có Undo Group; các repo khác mỗi tool 1 undo riêng lẻ |
| **Khả năng hoạt động khi mất mạng** | Giao diện và các thao tác cục bộ vẫn hoạt động | Phụ thuộc vào MCP Client và LLM Cloud |

---

## 4. BÀI HỌC VÀ KHUYẾN NGHỊ KẾ THỪA CHO COMMANDER MỚI

Mặc dù Auralink là giải pháp đóng và không thể kế thừa mã nguồn trực tiếp, nhưng **mô hình sản phẩm của Auralink là hình mẫu lý tưởng nhất** cho AI Music Production Commander mới. Chúng ta hoàn toàn có thể tái hiện và nâng cấp toàn bộ mô hình này bằng cách kết hợp các dự án mã nguồn mở:

1. **Về Pre-flight Music Checking:** Kế thừa thư viện `music21` để kiểm tra nốt ngoài âm vực, lỗi quãng 5 song song và voice leading trước khi ghi vào DAW.
2. **Về Instrument Skills:** Thiết kế một **Instrument Profile Layer** (dạng cấu hình JSON/YAML) định nghĩa dải phím khả dụng (playable range) và keyswitch map cho từng VST phổ biến.
3. **Về Undo/Rollback:** Kế thừa giải pháp `undo_group.py` của `Reaper-MCP` để bọc toàn bộ chuỗi hành động vào một transaction nguyên khối.
4. **Về Giao diện Desktop Độc lập:** Xây dựng ứng dụng Desktop bằng kiến trúc **Tauri + Svelte/React** siêu nhẹ (dưới 50MB RAM), kết nối với Agent Runtime qua WebSocket JSON-RPC.
