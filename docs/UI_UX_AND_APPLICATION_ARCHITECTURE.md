# 7. BÁO CÁO THIẾT KẾ GIAO DIỆN VÀ KIẾN TRÚC ỨNG DỤNG DESKTOP
*(UI/UX AND APPLICATION ARCHITECTURE)*

## 1. MỤC TIÊU VÀ RÀNG BUỘC PHẦN CỨNG

Giao diện người dùng của AI Music Production Commander không chỉ là một khung chat đơn thuần mà là một **Trung tâm Chỉ huy (Command Center)** hỗ trợ nhạc sĩ và nhà sản xuất âm nhạc.

### Các ràng buộc cốt tử:
- **Phần cứng mục tiêu:** Intel Core i3-1115G4, RAM 8GB. Trong lúc làm việc, REAPER cùng các VST nặng (Kontakt, Omnisphere, Serum...) đã chiếm từ 3.5GB đến 5.5GB RAM.
- **Ngân sách bộ nhớ cho Commander UI:** **Tối đa dưới 80 - 120MB RAM**.
- **Tính năng UI bắt buộc:**
  1. Hộp thoại trò chuyện bằng ngôn ngữ tự nhiên (Chat Interface) kèm streaming câu trả lời.
  2. Bảng theo dõi tiến trình thực thi nhiều bước (Task Planning & Execution Timeline).
  3. Bảng phê duyệt thay đổi (Approval Workflow Dialog).
  4. Bộ hiển thị ngữ cảnh dự án (Project Context Inspector: Key, BPM, Active Tracks).
  5. Cửa sổ nghe thử nhanh (Audio Audition Player) và xem trước nốt MIDI (Piano Roll Mini-preview).

---

## 2. SO SÁNH CÁC CÔNG NGHỆ GIAO DIỆN DESKTOP

| Tiêu chí | Electron (VS Code, Slack) | Tauri v2 (Rust + Webview) | Python GUI (PyQt6 / PySide6) | Flutter Desktop |
| :--- | :--- | :--- | :--- | :--- |
| **Mức tiêu thụ RAM khi khởi động** | **180 - 350 MB** *(Quá nặng cho máy 8GB)* | **35 - 55 MB** *(Rất nhẹ, dùng Webview2 có sẵn trên Windows)* | 70 - 110 MB | 80 - 120 MB |
| **Dung lượng bộ cài (.zip / .exe)** | > 120 MB | **< 15 MB** | 45 - 80 MB | 30 - 50 MB |
| **Tốc độ khởi động (Cold Start)** | 2.5 - 4.5 giây | **0.4 - 0.8 giây** | 1.2 - 2.0 giây | 0.8 - 1.5 giây |
| **Khả năng thiết kế giao diện âm nhạc hiện đại (Theme, Canvas, Waveform)** | Xuất sắc (Hệ sinh thái Web) | **Xuất sắc (HTML5/Canvas/WebGL/Tailwind)** | Khá (CSS hạn chế) | Rất tốt |
| **Tính độc lập & Dễ tích hợp với Agent Core** | Tốt qua IPC | **Cực tốt qua WebSocket / Named Pipe** | Tốt (Cùng chạy Python) | Khá |

**Quyết định lựa chọn công nghệ:** **Tauri v2 kết hợp Frontend gọn nhẹ (Svelte hoặc React + Tailwind CSS)** là ứng viên số 1, bảo đảm giao diện mượt mà, khởi động dưới 1 giây và chỉ tiêu thụ khoảng **40MB RAM** trên Windows 10/11.

---

## 3. THIẾT KẾ BỐ CỤC KHÔNG GIAN LÀM VIỆC (WORKSPACE LAYOUT)

Giao diện Desktop được chia làm 3 phân vùng công thái học:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ AI MUSIC PRODUCTION COMMANDER v1.0   [● REAPER Connected] [Key: Cm | 72 BPM] [⚙]│
├─────────────────────────┬──────────────────────────────────┬─────────────────────┤
│ 1. PROJECT INSPECTOR    │ 2. CHAT & EXECUTION TIMELINE     │ 3. PROPOSED ACTIONS │
│                         │                                  │    & AUDITION       │
│ • Key: C minor          │ User:                            │                     │
│ • Tempo: 72.0 BPM       │ "Viết bè dây 4 bè cho điệp khúc" │ [Pending Approval]  │
│ • Time Sig: 4/4         │                                  │                     │
│ • Tracks (4):           │ Commander (Amadeus):             │ Action: Insert MIDI │
│   [1] Kick              │ ⟳ Phân tích ngữ cảnh... ✓         │ Track: Violin I     │
│   [2] Snare             │ ⟳ Sáng tác 4 bè (Vln, Vla, Cel)...│ Notes: 32 notes     │
│   [3] Acoustic Piano    │ ⟳ Thẩm định nhạc lý (No 5ths)... ✓│ Range: D4 - G5      │
│   [4] Bass              │                                  │                     │
│                         │ [Plan: 4 steps ready]            │ [ ▶ Audition ]      │
│ • Instrument Skills:    │                                  │                     │
│   - LASS 3 (Active)     │                                  │ [  ✓ CHẤP THUẬN  ]  │
│   - Pianoteq (Active)   │ Type your message here...     [▲]│ [  ✗ TỪ CHỐI      ]  │
└─────────────────────────┴──────────────────────────────────┴─────────────────────┘
```

### Chi tiết các phân vùng:
1. **Sidebar Trái - Project Inspector:**
   - Hiển thị tức thời trạng thái REAPER (tự động cập nhật khi người dùng chuyển tab hoặc đổi tempo trong DAW).
   - Danh sách "Kỹ năng nhạc cụ" (Instrument Skills) đang được nạp, giúp người dùng biết AI sẽ áp dụng keyswitch nào.
2. **Khu vực Trung tâm - Chat & Timeline:**
   - Khung hội thoại tự nhiên với AI.
   - Thẻ tiến trình trực quan (Execution Timeline Cards): Thể hiện rõ từng bước AI đã lên kế hoạch và trạng thái thực thi (Pending, In Progress, Verified).
3. **Sidebar Phải - Action Approval & Audition:**
   - Khi ở chế độ an toàn (*Proposed-change mode*), AI không tự ý chạm vào DAW mà đẩy bản xem trước (preview) sang cột này.
   - Cho phép người dùng bấm nút **[▶ Audition]** để nghe thử nhanh đoạn nốt hoặc xem phím đàn mini trước khi bấm **[✓ Chấp thuận]**.

---

## 4. CHIẾN LƯỢC KẾT NỐI GIỮA UI VÀ CORE RUNTIME

- Giao diện Desktop (Tauri App) hoạt động như một tiến trình độc lập.
- Nó kết nối với **Commander Agent Runtime** (tiến trình nền Python) thông qua **WebSocket cục bộ (`ws://127.0.0.1:port`)**:
  - Gửi yêu cầu của người dùng dạng JSON-RPC.
  - Nhận streaming token phản hồi thời gian thực.
  - Nhận sự kiện thông báo (event notification) khi project trong DAW thay đổi.
- Nếu người dùng vô tình đóng cửa sổ giao diện, tiến trình Agent Core vẫn an toàn và giữ nguyên trạng thái kết nối với DAW.
