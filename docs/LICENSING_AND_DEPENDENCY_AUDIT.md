# 9. BÁO CÁO PHÂN TÍCH GIẤY PHÉP VÀ PHỤ THUỘC MÃ NGUỒN
*(LICENSING AND DEPENDENCY AUDIT)*

## 1. MỤC TIÊU VÀ NGUYÊN TẮC TUÂN THỦ PHÁP LÝ

Để AI Music Production Commander có thể phát triển bền vững, an toàn về mặt sở hữu trí tuệ và có khả năng thương mại hóa hoặc phân phối nhị phân rộng rãi trong tương lai:
- **Tuyệt đối không vi phạm các điều khoản Copyleft nghiêm ngặt (GPLv3, AGPLv3)** trong mã nguồn lõi.
- Xác định rõ ranh giới giữa việc "kế thừa mã nguồn trực tiếp" (copy code) và việc "kết nối qua giao thức độc lập" (IPC / API integration).

---

## 2. MA TRẬN PHÂN TÍCH GIẤY PHÉP CÁC DỰ ÁN KHẢO SÁT

| Repository / Thư viện | Giấy phép (License) | Loại giấy phép | Khả năng sử dụng thương mại | Rủi ro lây nhiễm Copyleft | Chiến lược xử lý |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Reaper-MCP** *(xDarkzx)* | **Apache-2.0** | Permissive (Dễ dãi) | **Rất tốt** (Cho phép đóng gói, sửa đổi, thương mại hóa) | **Không** (Yêu cầu giữ thông báo bản quyền và NOTICE) | **Fork và mở rộng trực tiếp** vào codebase của Commander |
| **reaper-reapy-mcp** *(wegitor)* | **MIT** | Permissive | **Rất tốt** | **Không** | Tái sử dụng ý tưởng kiến trúc Controller |
| **reaper-daemon** *(wretcher207)* | **MIT** | Permissive | **Rất tốt** | **Không** | Tham khảo cơ chế file queue |
| **daw-ai** *(hrubiian)* | **MIT** | Permissive | **Rất tốt** | **Không** | Tái sử dụng cho native adapter |
| **music21** *(cuthbertLab)* | **BSD-3-Clause** | Permissive | **Rất tốt** | **Không** (Yêu cầu giữ copyright disclaimer) | **Tích hợp làm dependency chính thức** |
| **pretty_midi / mido** | **MIT** | Permissive | **Rất tốt** | **Không** | **Tích hợp làm dependency chính thức** |
| **scipy / numpy** | **BSD-3-Clause** | Permissive | **Rất tốt** | **Không** | **Tích hợp làm dependency chính thức** |
| **aura-daw** *(knobo)* | **GPL-3.0** | Strong Copyleft | Phải mở mã nguồn nếu phân phối cùng binary | **Rất cao (Lây nhiễm)** | **Chỉ tham khảo giao diện (Reference Only)**, tuyệt đối không copy code |
| **ATRI_AGENT** *(Tz-WIND)* | **AGPL-3.0** | Extreme Copyleft | Buộc mở mã nguồn cả khi chạy trên server/network | **Cực cao** | **Chỉ tham khảo ý tưởng (Reference Only)** |
| **setloom** *(appautomaton)* | **AGPL-3.0** | Extreme Copyleft | Buộc mở mã nguồn | **Cực cao** | **Chỉ tham khảo ý tưởng** |
| **FFmpeg** | **LGPL-2.1+ / GPL** | Conditional Copyleft | Cho phép dùng nếu gọi dạng tiến trình rời (CLI/sub-process) | **Thấp** nếu giữ nguyên binary FFmpeg rời | **Gọi dạng External Tool qua CLI** |

---

## 3. RANH GIỚI BẢN QUYỀN VÀ KIẾN TRÚC TÁCH BIỆT (IP BOUNDARY)

Để tránh nguy cơ tranh chấp pháp lý và bảo vệ quyền sở hữu trí tuệ của sản phẩm mới:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   VÙNG SỞ HỮU TRÍ TUỆ COMMANDER CORE                   │
│   (Giấy phép Permissive: Apache-2.0 / MIT / Bản quyền tác giả)        │
│                                                                        │
│   • Core Agent Runtime (Python 3.12)                                   │
│   • Instrument Skills Engine                                           │
│   • Tool Registry & Permission Layer                                   │
│   • music21 / pretty_midi (BSD/MIT dependencies)                       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                         [RANH GIỚI IPC / PROCESS]
                                   │
        ┌──────────────────────────┴──────────────────────────┐
        ▼                                                     ▼
┌──────────────────────────────┐        ┌────────────────────────────────┐
│   VÙNG REAPER ADAPTER        │        │   VÙNG CÔNG CỤ NGOÀI (EXTERNAL)│
│   (Apache-2.0 / MIT)         │        │   (FFmpeg Binary - LGPL)       │
│   • ReaScript Lua Driver     │        │   • Gọi qua sub-process CLI    │
│   • Chạy độc lập trong DAW   │        │   • Không liên kết tĩnh (Link) │
└──────────────────────────────┘        └────────────────────────────────┘
```

### Nguyên tắc tích hợp:
1. **Không liên kết tĩnh (Static Linking) với mã nguồn GPL/LGPL:** Bất kỳ thư viện nào dùng GPL (như FFmpeg codec) chỉ được gọi như một chương trình thực thi độc lập (CLI process) thông qua `subprocess.run()`. Đây là chuẩn mực được quốc tế công nhận để không làm lây nhiễm giấy phép copyleft vào phần mềm chính.
2. **Kế thừa an toàn từ Apache-2.0:** Khi fork hoặc kế thừa các file từ `Reaper-MCP`, hệ thống giữ nguyên header bản quyền tác giả ban đầu và tạo tệp `NOTICE` ghi nhận nguồn gốc theo đúng điều khoản Mục 4 của Giấy phép Apache 2.0.

---

## 4. KẾT LUẬN VỀ AN TOÀN PHÁP LÝ

Kiến trúc AI Music Production Commander được thiết kế hoàn toàn trên nền tảng **Permissive Licenses (Apache-2.0, MIT, BSD-3-Clause)**. Toàn bộ mã nguồn cốt lõi được bảo đảm 100% sạch về mặt pháp lý, không bị ràng buộc bởi các rào cản GPL/AGPL, mở ra lộ trình phân phối thương mại hoặc mã nguồn mở linh hoạt mà không gặp bất kỳ rủi ro nào.
