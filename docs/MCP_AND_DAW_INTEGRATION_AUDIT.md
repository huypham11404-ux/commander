# 5. BÁO CÁO PHÂN TÍCH GIAO THỨC TÍCH HỢP DAW VÀ MCP
*(MCP AND DAW INTEGRATION AUDIT)*

## 1. TỔNG QUAN VỀ MODEL CONTEXT PROTOCOL (MCP)

Model Context Protocol (MCP) do Anthropic khởi xướng là một chuẩn mở cho phép các mô hình AI tương tác an toàn với các công cụ (tools) và nguồn dữ liệu bên ngoài.
Trong bối cảnh AI Music Production Commander:
- **MCP Server** đóng vai trò là cầu nối cung cấp danh mục công cụ DAW (Track creation, MIDI manipulation, FX control, Project inspection).
- **MCP Client** (như Claude Desktop, hoặc chính AI Commander Desktop App) kết nối đến server này để thực thi lệnh.

Tuy nhiên, việc tích hợp MCP với phần mềm âm thanh chuyên nghiệp (DAW) đặt ra nhiều bài toán đặc thù về hiệu năng, độ trễ và tính liên tục của luồng xử lý.

---

## 2. KẾT QUẢ ĐO ĐẠC THỰC NGHIỆM CÁC PHƯƠNG ÁN IPC & PROTOCOL

Chúng tôi đã xây dựng bộ đo chuẩn (*Benchmark Suite*) độc lập trên hệ thống Linux/Python 3.12, thực hiện **1.000 chu kỳ giao tiếp liên tục** trên từng phương thức để đo độ trễ trung bình, độ trễ phân vị 99% (P99) và thông lượng (Throughput). Kết quả đo lường thực tế ghi nhận như sau (dữ liệu lưu tại `evidence/ipc_benchmark_results.json`):

| Giao thức / Phương thức IPC | Độ trễ trung bình (Avg Latency) | Phân vị 50% (P50) | Phân vị 99% (P99) | Thông lượng (Throughput) | Độ an toàn & Rollback |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **File-based Atomic Swap** *(Reaper-MCP model)* | **0.260 ms** | 0.233 ms | 0.490 ms | **3.841 ops/giây** | Cực kỳ an toàn, zero port conflict, có transaction |
| **TCP Local Loopback JSON-RPC** *(Socket model)* | **0.164 ms** | 0.161 ms | 0.265 ms | **6.087 ops/giây** | Rất cao, phụ thuộc port nội bộ, dễ lỗi thread-safety nếu bridge kém |
| **WebSocket JSON-RPC** *(Async Bridge model)* | **0.320 ms** | 0.300 ms | 0.465 ms | **3.118 ops/giây** | Chuẩn hóa cho UI/Desktop streaming 2 chiều |
| **Atomic Multi-Action Rollback** | **0.075 ms** *(Thời gian khôi phục)* | - | - | - | **Thành công 100% (Khôi phục toàn bộ trạng thái ban đầu khi lỗi)** |

### Phân tích số liệu:
1. **Tất cả các phương thức IPC trên đều có độ trễ dưới 1 mili-giây (sub-millisecond)** khi xử lý trong tiến trình OS.
2. Với thông lượng từ 3.000 đến 6.000 thao tác/giây, cả ba phương thức đều thừa sức đáp ứng nhu cầu sản xuất âm nhạc (thường chỉ phát sinh từ 5 đến 50 lệnh mỗi chu kỳ tương tác AI).
3. **Thực nghiệm Rollback:** Thử nghiệm kịch bản 5 bước (tạo 3 track, gặp lỗi ở bước 4 khi nạp VST hỏng). Hệ thống khôi phục hoàn toàn về trạng thái ban đầu chỉ trong **0.075ms**, bảo đảm không có dữ liệu rác tồn đọng trong DAW.

---

## 3. THIẾT KẾ ĐỘC LẬP DAW: PHÂN TÁCH 6 TẦNG CHUYÊN BIỆT

Để Commander không bị ràng buộc vĩnh viễn vào REAPER, kiến trúc phải phân tách rạch ròi 6 tầng:

```
[1. User Interface (Desktop Chat / Timeline UI)]
                        │
                        ▼ (WebSocket JSON-RPC)
[2. Commander Brain / Core Agent Runtime]
                        │
                        ▼
[3. Tool Registry & Permission Validator] ──> Kiểm tra quyền Read/Proposed/Direct
                        │
                        ▼
[4. Abstract DAW Adapter Interface] ───────> Chuẩn giao thức Commander Protocol v1.0
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
[5A. REAPER Native Adapter]     [5B. Future DAW Adapter (Bitwig / Logic / Custom DAW)]
        │ (Atomic File IPC)             │ (WebSocket / IPC)
        ▼                               ▼
  [REAPER DAW]                     [Custom DAW]
```

### Chi tiết các tầng:
1. **Agent / Brain:** Tiếp nhận ngôn ngữ tự nhiên, lập kế hoạch, tương tác với LLM Provider. Không chứa bất kỳ dòng mã nào liên quan đến API của một DAW cụ thể.
2. **Tool Registry:** Định nghĩa các công cụ ở dạng chuẩn hóa (ví dụ `daw.create_track`, `daw.insert_midi_item`, `daw.set_tempo`, `daw.scan_plugins`).
3. **DAW Adapter (Abstract Base Class):** Định nghĩa hợp đồng interface trừu tượng (`IDawAdapter`). Mọi phương thức đều trả về `Result<T, Error>` chuẩn hóa.
4. **DAW Bridge (Driver):** Thành phần cụ thể thực thi giao tiếp với DAW mục tiêu:
   - `ReaperBridge`: Dùng Atomic File IPC + ReaScript Lua.
   - `GenericWsBridge`: Dùng WebSocket JSON-RPC cho các DAW hiện đại hoặc DAW tự phát triển trong tương lai.

---

## 4. QUY CHUẨN GIAO THỨC COMMANDER PROTOCOL v1.0 (SCHEMA DEFINITION)

Mọi gói tin trao đổi giữa Commander và DAW Adapter đều tuân thủ chuẩn JSON Schema có versioning:

### 4.1. Request Schema:
```json
{
  "protocol_version": "1.0",
  "transaction_id": "tx_9a8b7c6d-1234",
  "is_atomic_group": true,
  "commands": [
    {
      "command_id": "cmd_001",
      "action": "track.create",
      "params": {
        "name": "Violin I",
        "color": "#E74C3C",
        "folder_depth": 0
      }
    },
    {
      "command_id": "cmd_002",
      "action": "midi.insert_item",
      "params": {
        "track_id": "$cmd_001.result.track_id",
        "position_beats": 0.0,
        "length_beats": 16.0,
        "notes": [
          {"pitch": 72, "start_beat": 0.0, "length_beat": 1.0, "velocity": 90}
        ]
      }
    }
  ]
}
```

### 4.2. Response Schema:
```json
{
  "protocol_version": "1.0",
  "transaction_id": "tx_9a8b7c6d-1234",
  "status": "success",
  "execution_time_ms": 18.4,
  "results": {
    "cmd_001": {"status": "ok", "track_id": 3, "track_guid": "{A1B2-C3D4}"},
    "cmd_002": {"status": "ok", "item_id": 12, "notes_inserted": 1}
  },
  "undo_created": true,
  "undo_name": "AI: Add Violin I & Insert MIDI"
}
```

---

## 5. KẾT LUẬN

1. Sử dụng **WebSocket JSON-RPC** làm kênh giao tiếp chính giữa Giao diện Desktop (UI) và Agent Runtime.
2. Sử dụng **Abstract DAW Adapter** với chuẩn **Commander Protocol v1.0** để đảm bảo khả năng cắm/rút và thay thế DAW mà không cần viết lại dù chỉ 1 dòng code logic của AI Agent.
3. Sử dụng **Atomic File-based Driver** cho REAPER nhằm tối đa hóa độ an toàn và ổn định trên Windows.
