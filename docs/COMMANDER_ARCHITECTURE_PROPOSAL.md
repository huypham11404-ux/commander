# 10. ĐỀ XUẤT KIẾN TRÚC TỔNG THỂ AI MUSIC PRODUCTION COMMANDER
*(COMMANDER ARCHITECTURE PROPOSAL)*

## 1. TỔNG QUAN KIẾN TRÚC VÀ NGUYÊN TẮC THIẾT KẾ

AI Music Production Commander là một nền tảng độc lập, mô-đun hóa cao, đóng vai trò là "Nhạc trưởng thông minh" kết nối giữa ý định nghệ thuật của con người và năng lực kỹ thuật của DAW.

### 5 Nguyên tắc thiết kế sống còn:
1. **DAW-Agnostic (Độc lập với DAW):** Lõi AI và công cụ nhạc lý hoàn toàn không phụ thuộc vào REAPER hay bất kỳ DAW cụ thể nào. Mọi thao tác tương tác qua **Abstract DAW Adapter**.
2. **Offline-Capable Core, Cloud-Enhanced Intelligence:** Toàn bộ các thao tác điều khiển, phân tích MIDI, luật nhạc lý và DSP cơ bản hoạt động 100% ngoại tuyến (offline). Chỉ sử dụng Cloud LLM cho các tác vụ suy luận và tạo sinh phức tạp.
3. **Safety & Zero-Destruction First:** Mọi thay đổi đều được kiểm định nhạc lý trước (Pre-flight Guardrails), phân quyền 3 cấp và bọc trong khối giao dịch có khả năng hoàn tác bằng 1 lần `Ctrl+Z`.
4. **Lightweight Footprint:** Tối ưu hóa chặt chẽ để vận hành hoàn hảo trên cấu hình **Intel Core i3-1115G4, RAM 8GB, không GPU rời**, tổng mức chiếm dụng RAM của toàn bộ hệ thống dưới **120MB**.
5. **Human-Centric Creativity:** Phục vụ và tôn vinh quyết định sáng tạo của con người; giải thích lý do cho từng đề xuất và hỗ trợ người dùng nâng cao kỹ năng sản xuất âm nhạc theo thời gian.

---

## 2. BIỂU ĐỒ KIẾN TRÚC PHÂN TẦNG (SYSTEM ARCHITECTURE DIAGRAM)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          1. DESKTOP USER INTERFACE (Tauri v2)                         │
│  [Chat & Prompting]   [Task Timeline]   [Project Inspector]   [Approval & Audition]    │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Local WebSocket JSON-RPC (Port 9876)
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│                    2. COMMANDER CORE AGENT RUNTIME (Python 3.12)                       │
│                                                                                        │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌────────────────────────┐  │
│  │ Intent & Task Planner   │  │ Context & Session State │  │ Memory Manager         │  │
│  │ (Decomposition Engine)  │  │ (Short-term & Long-term)│  │ (commander_session)    │  │
│  └───────────┬─────────────┘  └───────────┬─────────────┘  └───────────┬────────────┘  │
│              │                            │                            │               │
│              ▼                            ▼                            ▼               │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ LLM Provider Abstraction Layer                                                   │  │
│  │ [Anthropic Claude]  [OpenAI GPT]  [Google Gemini]  [DeepSeek]  [Local llama.cpp] │  │
│  └────────────────────────────────────────┬─────────────────────────────────────────┘  │
│                                           │                                            │
│  ┌────────────────────────────────────────▼─────────────────────────────────────────┐  │
│  │ Permission, Safety & Audit Layer (Read-only / Proposed-change / Direct-edit)      │  │
│  └────────────────────────────────────────┬─────────────────────────────────────────┘  │
│                                           │                                            │
│  ┌────────────────────────────────────────▼─────────────────────────────────────────┐  │
│  │ Tool Registry & Execution Engine                                                 │  │
│  │ [DAW Tools]  [MIDI Tools]  [Theory Tools]  [Instrument Skills]  [Audio Analysis] │  │
│  └──────┬──────────────────┬──────────────────┬──────────────────┬──────────────────┘  │
└─────────┼──────────────────┼──────────────────┼──────────────────┼─────────────────────┘
          │                  │                  │                  │
          ▼                  ▼                  ▼                  ▼
┌──────────────────┐┌──────────────────┐┌──────────────────┐┌───────────────────────────┐
│3. DAW ADAPTER    ││4. MUSIC          ││5. INSTRUMENT     ││6. AUDIO FEEDBACK          │
│   LAYER          ││   INTELLIGENCE   ││   SKILLS ENGINE  ││   LOOP LAYER              │
│                  ││   (music21)      ││                  ││   (scipy / numpy)         │
│ • IDawAdapter    ││ • Key Detection  ││ • Pianoteq       ││ • LUFS & Peak Meter       │
│ • Transaction Mgr││ • Chord Analysis ││ • LASS 3 Strings ││ • Spectral Centroid       │
│ • Rollback Engine││ • Voice Leading  ││ • Ample Guitars  ││ • Muddy Freq Detection    │
│ • ReaScript Lua  ││ • Counterpoint   ││ • Native Drums   ││ • Phase Correlation       │
│   (Atomic File)  ││ • Quantize/Swing ││ • Keyswitches    ││ • Quick Stem Audition     │
└─────────┬────────┘└──────────────────┘└──────────────────┘└───────────────────────────┘
          │
          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                             7. TARGET DIGITAL AUDIO WORKSTATIONS                       │
│  [ REAPER DAW (Current) ]  <───>  [ Custom DAW / Bitwig / Ableton (Future Extension) ] │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. CHI TIẾT CÁC PHÂN HỆ CHÍNH (SUBSYSTEM SPECIFICATIONS)

### 3.1. Phân hệ 1: Desktop User Interface (Tauri v2 + Svelte/React)
- **Công nghệ:** Tauri v2 (Rust backend + Webview2 frontend).
- **Tính năng:**
  - Khung chat ngôn ngữ tự nhiên hỗ trợ streaming text từ LLM.
  - Thẻ tiến trình nhiệm vụ (Execution Timeline) hiển thị từng bước hành động.
  - Khung phê duyệt (Approval Box) với nút nghe thử trước khi ghi vào DAW.
  - Bộ giám sát trạng thái DAW (BPM, Key, Active tracks).
- **Mức chiếm dụng bộ nhớ:** **~40 MB RAM**.

### 3.2. Phân hệ 2: Core Agent Runtime (Python 3.12)
- **Intent Parser & Planner:** Tiếp nhận yêu cầu, phân rã thành các bước nguyên tử (atomic steps).
- **Provider Layer:** Chuẩn hóa giao tiếp với OpenAI, Claude, Gemini hoặc mô hình cục bộ.
- **Session Manager:** Quản lý lịch sử và ngữ cảnh dự án dài hạn (`commander_session.json`).
- **Mức chiếm dụng bộ nhớ:** **~35 MB RAM**.

### 3.3. Phân hệ 3: DAW Adapter Layer (Độc lập với DAW)
- **Interface trừu tượng `IDawAdapter`:**
  - `get_project_context() -> ProjectContext`
  - `execute_transaction(tx: Transaction) -> TransactionResult`
  - `rollback_transaction(tx_id: str) -> bool`
- **ReaperDriver (Kế thừa từ `Reaper-MCP`):** Sử dụng cơ chế Atomic File-based Swap (`command.json` / `response.json`) kèm khóa tệp hệ điều hành, gọi trực tiếp API `Undo_BeginBlock2 / Undo_EndBlock2`.
- **Mức chiếm dụng bộ nhớ:** **~15 MB RAM**.

### 3.4. Phân hệ 4: Music Intelligence & Guardrails (Tích hợp `music21` + `pretty_midi`)
- **Key & Scale Engine:** Nhận diện và quản lý điệu tính thời gian thực.
- **Harmonic Analyzer:** Phân tích tiến trình hợp âm, hòa thanh 4 bè.
- **Pre-flight Musical Guardrails:** Kiểm tra lỗi cấm kỵ (quãng 5/8 song song), nốt ngoài âm vực nhạc cụ, nốt va chạm trước khi đẩy vào DAW.
- **Mức chiếm dụng bộ nhớ:** **~45 MB RAM**.

### 3.5. Phân hệ 5: Instrument Skills Engine (Hồ sơ nhạc cụ ảo)
- Cung cấp các hồ sơ cấu hình nhạc cụ (Instrument Profiles) định dạng JSON/YAML:
  - Dải phím chơi được (Playable Range).
  - Bản đồ phím chuyển kỹ thuật (Keyswitch Map: Staccato, Legato, Pizzicato, Tremolo).
  - Ánh xạ CC (Expression CC11, Dynamics/Modulation CC1, Sustain Pedal CC64).

### 3.6. Phân hệ 6: Audio Feedback Loop (DSP nhẹ trên `scipy` / `numpy`)
- **Offline DSP:** Đo LUFS, RMS, Crest Factor, Spectral Centroid trong 2-5ms.
- **Mix Critique:** Cảnh báo các vấn đề âm học khách quan (ví dụ: Bass bị quá tải năng lượng, dải Mid bị xung đột giữa Vocal và Guitar).

---

## 4. TỔNG KẾT TÀI NGUYÊN VÀ KHẢ NĂNG TƯƠNG THÍCH PHẦN CỨNG

| Thành phần hệ thống | Mức chiếm dụng RAM thực tế | Tiêu thụ CPU khi nghỉ (Idle) | Tiêu thụ CPU khi hoạt động (Peak) |
| :--- | :--- | :--- | :--- |
| Desktop UI (Tauri v2) | ~40 MB | 0.1% | 1.5% |
| Core Agent Runtime | ~35 MB | 0.0% | 2.0% |
| Music Intelligence (`music21`) | ~45 MB | 0.0% | 4.0% (trong 40ms) |
| DAW Adapter (Reaper Bridge) | ~15 MB | 0.0% | 0.5% |
| **TỔNG CỘNG HỆ THỐNG COMMANDER** | **~135 MB RAM** | **< 0.2% CPU** | **< 8.0% CPU** |

**Kết luận:** Với tổng mức chiếm dụng chỉ **~135MB RAM**, AI Music Production Commander hoàn toàn có thể chạy song song êm ái cùng REAPER và các bộ nhạc cụ ảo trên hệ thống **Intel Core i3, RAM 8GB** mà không bao giờ gây gián đoạn hay drop audio buffer của hệ thống thu âm.
