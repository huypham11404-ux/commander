# 8. BÁO CÁO MÔ HÌNH BẢO MẬT VÀ PHÂN QUYỀN
*(SECURITY AND PERMISSION MODEL)*

## 1. MỤC TIÊU VÀ NGUYÊN TẮC BẢO MẬT BẮT BUỘC

Trong một hệ thống trợ lý âm nhạc được điều khiển bởi AI Agent:
- Mô hình ngôn ngữ lớn (LLM) có thể mắc sai lầm, bị ảo giác hoặc chịu tấn công Prompt Injection từ dữ liệu tải về từ Internet.
- **Nguyên tắc bất di bất dịch:** **Tuyệt đối không cấp quyền cho LLM tự do thực thi lệnh shell hệ thống (Arbitrary Shell Execution) hoặc truy cập tùy tiện vào hệ thống tệp ngoài thư mục dự án được chỉ định.**

Mọi thao tác thay đổi trạng thái project âm nhạc phải được kiểm soát thông qua mô hình phân quyền chặt chẽ, có thể kiểm toán và có khả năng phục hồi hoàn toàn.

---

## 2. MÔ HÌNH PHÂN QUYỀN 3 CẤP (3-TIER PERMISSION SYSTEM)

Hệ thống thiết lập 3 cấp độ vận hành minh bạch do người dùng toàn quyền quyết định:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CÁC CẤP ĐỘ PHÂN QUYỀN                           │
├──────────────────┬──────────────────────┬──────────────────────────────┤
│ Level 1:         │ Level 2:             │ Level 3:                     │
│ READ-ONLY        │ PROPOSED-CHANGE      │ DIRECT-EDIT                  │
│ (Mặc định khi mở)│ (Chế độ khuyến nghị) │ (Chế độ tự động hóa cao)     │
├──────────────────┼──────────────────────┼──────────────────────────────┤
│ • Đọc Key, BPM   │ • Cho phép AI soạn   │ • AI được phép tự động thực  │
│ • Xem track & FX │   thảo kế hoạch      │   thi trực tiếp trong phạm vi│
│ • Phân tích MIDI │ • Sinh nốt MIDI & FX │   giới hạn (Thêm track, nạp  │
│ • Tuyệt đối không│ • BẮT BUỘC người dùng│   nốt, điều chỉnh fader).    │
│   thay đổi DAW   │   bấm "Chấp thuận"   │ • MỌI thay đổi đều bọc trong │
│                  │   mới ghi vào DAW.   │   khối Undo Block (Ctrl+Z).  │
└──────────────────┴──────────────────────┴──────────────────────────────┘
```

### Chi tiết hành vi từng cấp:
1. **Level 1 - Read-Only (Chỉ đọc & Phân tích):** Phù hợp khi người dùng muốn AI phân tích cấu trúc bài hát, kiểm tra xung đột tần số trong bản mix hoặc giải thích nhạc lý. Bất kỳ tool nào có hành vi ghi đè sẽ bị chặn ở tầng Tool Validator.
2. **Level 2 - Proposed-Change (Đề xuất & Duyệt):** Chế độ làm việc chuẩn. AI trình bày: *"Tôi dự định thêm bè Violin vào Track 4 với 32 nốt, âm lượng -6dB. Bạn có duyệt không?"*. Kèm theo bản nghe thử mini. Chỉ khi người dùng bấm xác nhận, lệnh mới được gửi tới DAW Adapter.
3. **Level 3 - Direct-Edit (Thực thi trực tiếp trong phạm vi an toàn):** Dành cho người dùng có kinh nghiệm muốn tốc độ tối đa. Ngay cả ở chế độ này, các hành vi phá hủy nguy hiểm (như Xóa track, Ghi đè tệp âm thanh gốc) vẫn bắt buộc phải hỏi lại người dùng.

---

## 3. CƠ CHẾ GIAO DỊCH VÀ KHẢ NĂNG HOÀN TÁC (TRANSACTIONS & ROLLBACK)

Để bảo đảm tính toàn vẹn của dự án âm nhạc:
1. **Atomic Grouping:** Mọi chuỗi thao tác liên hoàn (ví dụ tạo 4 track bè dây và nạp hàng trăm nốt MIDI) được gói trong một `transaction_id`.
2. **Native DAW Undo Block:** Được bọc trực tiếp trong API của REAPER:
   ```lua
   reaper.Undo_BeginBlock2(0)
   -- Thực thi toàn bộ lệnh trong batch
   reaper.Undo_EndBlock2(0, "AI: Add 4-part Strings", -1)
   ```
   Nhờ đó, người dùng chỉ cần nhấn `Ctrl+Z` một lần duy nhất là toàn bộ các thay đổi của AI bị hủy bỏ sạch sẽ, project quay về trạng thái trước đó.
3. **Fail-safe Rollback:** Nếu lệnh thứ $K$ trong một chuỗi lệnh bị lỗi (ví dụ plugin VST không tải được), toàn bộ các lệnh từ $1$ đến $K-1$ tự động được rollback ngay lập tức, không để lại trạng thái "dở dang" trong project.

---

## 4. QUẢN LÝ BẢO MẬT API KEY VÀ CÔ LẬP TIẾN TRÌNH (SANDBOXING)

1. **Quản lý Khóa API Cục bộ:**
   - API Key của các nhà cung cấp (OpenAI, Anthropic, Gemini...) được lưu trữ bằng cơ chế mã hóa của hệ điều hành (Windows Credential Manager qua thư viện `keyring`).
   - Không lưu trữ API Key ở dạng văn bản thô (plaintext) trong các tệp cấu hình hoặc log.
2. **Hệ thống tệp (Filesystem Guardrails):**
   - Chỉ cho phép AI đọc/ghi trong thư mục project hiện hành và thư mục tạm `%TEMP%/commander_temp/`.
   - Ngăn chặn tuyệt đối mọi hành vi duyệt đường dẫn tương đối nguy hiểm (như `../../Windows/System32`).
3. **Zero Local Network Exposure:**
   - WebSocket và socket cục bộ chỉ bind duy nhất trên giao diện vòng lặp nội bộ `127.0.0.1`.
   - Tuyệt đối không mở port ra mạng ngoài (`0.0.0.0`), bảo vệ người dùng khỏi việc bị chiếm quyền điều khiển DAW qua mạng nội bộ LAN.
4. **Nhật ký kiểm toán minh bạch (Audit Trail):**
   - Mọi lệnh gửi tới DAW Adapter đều được ghi vào tệp nhật ký `commander_audit.log` kèm timestamp, prompt nguyên bản của người dùng và kết quả thực thi để dễ dàng tra cứu khi cần.
