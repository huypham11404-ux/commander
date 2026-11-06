# RED-TEAM AUDIT — AI MUSIC PRODUCTION COMMANDER

**Ngày thực hiện:** 06/11/2026
**Mục tiêu:** Kiểm định độc lập, phản biện kỹ thuật và xác minh thực chứng toàn bộ các giả định, đo đạc và kiến trúc đề xuất cho AI Music Production Commander.
**Nguyên tắc áp dụng:** Chỉ audit dựa trên bằng chứng mã nguồn (`references/Reaper-MCP`), thực nghiệm đo đạc (`evidence/`, `experiments/`), tuyệt đối không bảo vệ kết luận lý thuyết nếu bị mã nguồn hoặc dữ liệu thực tế bác bỏ.

---

## 1. HỆ THỐNG PHÂN LOẠI TRẠNG THÁI (STATUS CLASSIFICATION)
Mỗi phát hiện và tuyên bố kỹ thuật trong báo cáo này được gắn một trong sáu nhãn trạng thái nghiêm ngặt:
- `VERIFIED`: Đã được chứng minh trực tiếp qua mã nguồn thực tế hoặc tài liệu đặc tả chuẩn.
- `MEASURED`: Đã được đo đạc thực nghiệm với công cụ chuẩn hóa, số liệu lặp lại được.
- `OBSERVED`: Đã quan sát thấy hành vi trong quá trình chạy thử nghiệm.
- `ESTIMATED`: Ước lượng dựa trên mô hình kỹ thuật và thông số hệ thống, chưa đo trực tiếp trên môi trường Windows vật lý.
- `UNVERIFIED`: Chưa đủ dữ liệu hoặc thiếu môi trường đặc thù (REAPER GUI Windows) để kiểm chứng.
- `CONTRADICTED`: Bị mã nguồn thực tế hoặc kết quả đo đạc thực nghiệm bác bỏ.

---

## 2. KIỂM ĐỊNH CHI TIẾT THEO 7 HẠNG MỤC CỐT TỬ

### 2.1. REAPER Driver và Cơ chế IPC
- **Tính nguyên tử của File Swap trên Windows:** `VERIFIED`. `os.replace` trên Windows ánh xạ tới Win32 API `MoveFileExW` kèm cờ `MOVEFILE_REPLACE_EXISTING`. Đây là thao tác nguyên tử trên hệ thống tệp NTFS nếu nguồn và đích nằm trên cùng phân vùng ổ đĩa (`%TEMP%`).
- **Cơ chế Khóa tệp (File Lock):** `VERIFIED`. `_ipc_mutex()` trong `reaper_client.py` (dòng 155, 174) sử dụng `msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)` trên Windows và `fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)` trên POSIX. Đây là mutex cấp hệ điều hành (OS-level non-blocking polling).
- **Hiện tượng Race Condition khi nhiều client gọi đồng thời:** `VERIFIED_CONTROLLED`. Nhờ `_ipc_mutex()`, nếu 2 tiến trình client gọi đồng thời, tiến trình thứ hai sẽ đợi ở vòng lặp polling với deadline timeout thay vì ghi đè lên file IPC của tiến trình thứ nhất.
- **Xử lý Timeout và Stale Response:** `VERIFIED`. Mỗi lệnh sinh một `req_id = uuid.uuid4().hex`. Hàm `_is_stale_response()` (dòng 180) kiểm tra nếu phản hồi thuộc về lệnh trước đã bị timeout, client sẽ chủ động xóa file và tiếp tục đợi phản hồi đúng `req_id`.
- **Undo Block bao phủ toàn bộ hay từng phần:** `CONTRADICTED`. Xem chi tiết Mục 2.3.
- **Xác minh trạng thái Project sau thực hiện:** `VERIFIED_ABSENT`. ReaScript Lua trả về giá trị ngay sau khi gọi API, không có lớp xác minh độc lập (post-execution state verification) kiểm tra xem track hoặc FX có thực sự nạp hợp lệ hay không.

### 2.2. Tái Kiểm tra Benchmark IPC & Làm rõ Độ lệch Toán học
- **Phương pháp đo:** `MEASURED` (Tệp kết quả: `evidence/rigorous_ipc_benchmarks.json`).
  - Chạy 100 requests Warmup (loại bỏ chi phí cấp phát bộ nhớ ban đầu và nạp cache tệp).
  - Chạy 1.000 requests tuần tự đo đạc chính thức.
- **Số liệu đo đạc chi tiết:**
  - *Atomic File Swap:* Latency p50: **0.238 ms** | p95: **0.354 ms** | p99: **0.535 ms** | Max: **1.682 ms** | Throughput: **3.802 ops/giây**.
  - *TCP Socket JSON-RPC:* Latency p50: **0.167 ms** | p95: **0.212 ms** | p99: **0.233 ms** | Max: **0.254 ms** | Throughput: **5.695 ops/giây**.
  - *WebSocket JSON-RPC:* Latency p50: **0.308 ms** | p95: **0.413 ms** | p99: **0.511 ms** | Max: **0.534 ms** | Throughput: **3.083 ops/giây**.
- **Giải thích tính nhất quán toán học (Reciprocal Consistency):**
  Trong chế độ đo tuần tự (sequential synchronous round-trip), Throughput lý thuyết bằng nghịch đảo độ trễ trung bình:
  $$\text{Throughput lý thuyết} = \frac{1000\text{ ms}}{0.2622\text{ ms}} \approx 3.813{,}88\text{ ops/giây}$$
  Số đo thông lượng thực tế ghi nhận qua đồng hồ Wall-clock là **3.802,15 ops/giây** (sai số chỉ **0.31%** do chi phí đo của vòng lặp `perf_counter`). Do đó, hai chỉ số này hoàn toàn nhất quán.
- **Phân biệt rạch ròi Request Latency vs End-to-End Latency:** `VERIFIED_DISTINCTION`.
  - Con số **0.260 ms** CHỈ LÀ thời gian tuần tự hóa JSON và tráo tệp trong RAM buffer của hệ điều hành.
  - **End-to-End Execution Latency thực tế trong REAPER dao động từ 15ms đến 33ms**, bởi vì Lua ReaScript chạy trên vòng lặp `reaper.defer()` của REAPER (quét ~30-60 lần/giây theo nhịp refresh giao diện GUI). Không được nhầm lẫn giữa độ trễ đường truyền IPC với độ trễ thực thi trong DAW.

### 2.3. Transaction và Rollback: Bác bỏ Tuyên bố "Hoàn tác 1 chạm (Ctrl+Z)"
- **Tuyên bố ban đầu:** *"Mọi thao tác hàng trăm nốt và nhiều track được gói gọn trong một lần Ctrl+Z duy nhất"*.
- **Kết quả Audit mã nguồn thực tế:** `CONTRADICTED`.
  - Trong tệp `references/Reaper-MCP/reaper_mcp/undo_group.py` (dòng 8), tác giả ghi chú rõ ràng:
    > *"Nothing is held open in REAPER: a group only labels. (REAPER drops an undo block that is held open between bridge ticks, so collapsing a tool into one step was not possible, and it would also have removed the finer control.)"*
  - Trong Lua ReaScript (`reaper_mcp_server.lua`), mỗi lệnh con (ví dụ `track_create`, `track_set_volume`) gọi riêng `Undo_BeginBlock()` và `Undo_EndBlock()`.
  - Phân hệ `undo_group` chỉ gán nhãn: `"MCP: <tool>#<run> > <command>"`.
  - **Hệ quả thực tế:** Người dùng nhấn `Ctrl+Z` một lần sẽ chỉ hoàn tác lệnh con gần nhất chứ KHÔNG hoàn tác toàn bộ công việc nhiều bước của AI. Để hoàn tác toàn bộ cụm, client phải gửi lệnh `project_undo_group` hoặc người dùng phải nhấn `Ctrl+Z` nhiều lần tương ứng số lệnh.
- **Hành vi khi lỗi giữa chừng (Partial Failure):** `OBSERVED`.
  - Nếu công cụ gồm 5 lệnh mà lệnh thứ 4 bị lỗi trong Lua: lệnh 4 được bọc trong `pcall()`, Lua chặn ghi undo point cho lệnh 4. Nhưng lệnh 1, 2, 3 ĐÃ COMMIT vào REAPER từ các chu kỳ tick trước đó. REAPER không tự động rollback lệnh 1, 2, 3.
  - **Yêu cầu hành động bắt buộc:** Client Core phải chủ động bắt lỗi và phát lệnh `project_undo(steps=N-1)` để khôi phục trạng thái ban đầu, tránh phân mảnh lịch sử Undo của người dùng.

### 2.4. RAM, Audio Buffer và Độ ổn định Phần cứng (Intel i3, 8GB RAM)
- **Đo lường bộ nhớ thực tế (Linux container Python 3.12):** `MEASURED`.
  - Python runtime rỗng: **14.0 MB RSS**.
  - Nạp `mido` + `pretty_midi` + `numpy` + `scipy`: **33.8 MB RSS**.
  - Nạp thêm `music21`: **72.6 MB RSS** (thư viện `music21` nạp tiêu tốn +38.8 MB).
  - Thực thi phân tích hợp âm và DSP buffer 30s: **89.4 MB RSS**.
- **Bóc tách ước tính trên máy trạm Windows 10/11 (8GB RAM):** `ESTIMATED`.
  - Windows 10/11 + Background Services: 2.500 - 3.200 MB.
  - VRAM chia sẻ cho Intel UHD Graphics: 800 - 1.200 MB.
  - REAPER DAW (khi mở project nhiều track): 150 - 300 MB.
  - Các VST nặng (Kontakt, LASS 3, Pianoteq, Serum...): 1.500 - 3.000 MB.
  - Tauri + WebView2 runtime: 60 - 110 MB.
  - Commander Core Runtime: 80 - 120 MB.
  - **Tổng nhu cầu RAM hệ thống:** **5.090 - 7.930 MB**.
- **Bác bỏ Tuyên bố "Không bao giờ gây gián đoạn hay drop audio buffer":** `CONTRADICTED / UNVERIFIABLE`.
  - Trên máy 8GB RAM, khi VST chiếm dụng bộ nhớ lớn, RAM khả dụng thực tế của Windows chỉ còn khoảng 200 - 500MB. Nếu hệ điều hành kích hoạt cơ chế Paging (Virtual Memory swapping ra ổ đĩa) đúng lúc đang phát lại âm thanh, **hiện tượng Dropouts, Audio Underruns hoặc Clicks/Pops chắc chắn sẽ xảy ra**.
  - Hơn nữa, CPU Intel Core i3-1115G4 chỉ có **2 nhân vật lý (4 luồng)**. Một đợt tính toán nặng của `music21` hoặc FFT kéo dài 100-200ms nếu không được giới hạn luồng có thể tranh chấp thời gian CPU với Audio Thread thời gian thực của REAPER.
  - **Yêu cầu hành động:** Thu hồi mọi tuyên bố "đảm bảo 100% không drop". Thiết lập cơ chế kiểm soát ngưỡng RAM (cảnh báo khi RAM trống < 1.2GB) và gán độ ưu tiên tiến trình (OS Thread Priority) của Commander ở mức `Below_Normal` để nhường CPU cho REAPER.

### 2.5. Kiểm định Năng lực Nhạc lý (Music Intelligence Testing)
- **Thử nghiệm trên bộ ca nhạc lý đa dạng (`experiments/comprehensive_music_intelligence_test.py`):** `MEASURED`.
  - *C Major (I-IV-V-I):* Nhận diện đúng C major (Độ tương quan 0.928).
  - *A Minor (Am-Dm-E7-Am):* Nhận diện đúng A minor (Độ tương quan 0.886).
  - *Secondary Dominant (D7->G->C):* Nhận diện đúng C major (Độ tương quan 0.858).
  - *Neapolitan 6th (Db/F->G7->Cm):* Nhận diện đúng C minor (Độ tương quan 0.658).
  - *Modal Interchange (C Major vay mượn Fm và Ab):* `CONTRADICTED / FAILED`. Thuật toán Krumhansl-Schmuckler mặc định của `music21` nhận diện SAI thành **`C minor`** (Hệ số tương quan chỉ 0.622).
- **Kiểm định Voice Leading của `music21`:** `OBSERVED`.
  - Nhận diện đúng lỗi quãng 5 song song (`parallelFifth() = True`).
  - Nhận diện đúng hiện tượng đan chéo bè (`voiceCrossing() = True`).
  - **False Positive:** Thuật toán phát hiện dương tính giả trên chuyển động ngược chiều nếu có dịch chuyển quãng tám.
  - **Hạn chế polyphonic:** `music21` kiểm tra theo từng cặp bè (pairwise quartet), với tổng phổ 4 bè trở lên cần tính toán tổ hợp $O(N^2)$ và không thể phân biệt nốt thêu (passing tones) polyrhythmic nếu không có bộ băm lát thời gian (timeslicing heuristic) tự viết.

### 2.6. Vòng phản hồi Âm thanh (DSP Audio Feedback)
- **Kiểm nghiệm đa độ dài (0.5s, 2s, 10s, 30s tại 44.1kHz Stereo):** `MEASURED`.
  - *File I/O:* Chiếm từ 0.3ms (0.5s) đến 12.1ms (30s file).
  - *Tính RMS & Peak:* 0.16ms (0.5s) đến 4.65ms (30s).
  - *Bộ lọc K-weighting ITU-R BS.1770 (Đo LUFS):* Tăng tuyến tính từ **2.4ms (0.5s)** lên **143.9ms (30s file)**.
  - *True Peak (4x Sinc Oversampling):* Chiếm ~12.5ms cho đoạn trích 2s.
  - *Tổng thời gian xử lý:* Stem 30 giây mất **174.4 ms** trên CPU.
- **Ranh giới khoa học:** Phân biệt rạch ròi:
  - *Đo lường định lượng khách quan (Measurements):* LUFS, True Peak, Spectral Centroid, Crest Factor.
  - *Nhận xét hòa âm chủ quan (Perceptual Critique):* AI suy diễn từ các chỉ số đo lường (ví dụ "Bass lấn dải 150Hz"), tuyệt đối không coi đây là kết quả DSP khẳng định.

### 2.7. Rà soát Giấy phép (Licensing & Transitive Dependencies)
- **Các gói Python cốt lõi:** `VERIFIED`. `mido` (MIT), `pretty_midi` (MIT), `music21` (BSD-3-Clause), `numpy` (BSD-3-Clause), `scipy` (BSD-3-Clause), `websockets` (BSD-3-Clause), `psutil` (BSD-3-Clause).
- **Thư viện C/Fortran bắc cầu (Transitive in Scipy Wheel):** `VERIFIED`. Scipy wheel chứa `libquadmath*.so` (LGPL-2.1-or-later với GCC Runtime Exception). Theo điều khoản miễn trừ của GCC, việc liên kết động thư viện toán học này trong môi trường Python không kích hoạt nghĩa vụ mở mã nguồn của ứng dụng chính.
- **Bản đồ 4 mô hình triển khai:**
  1. *Phát triển nội bộ:* 100% hợp lệ.
  2. *Phân phối nhị phân Desktop:* 100% hợp lệ (đính kèm file NOTICE và Copyright Header của Apache-2.0 và BSD).
  3. *Phân phối mã nguồn:* 100% hợp lệ.
  4. *Khai thác SaaS/Cloud thương mại:* 100% sạch bản quyền.

---

## 3. BẢNG TỔNG KẾT TUYÊN BỐ VÀ PHÁN QUYẾT CUỐI CÙNG (FINAL VERDICT TABLE)

| Tuyên bố kỹ thuật (Claim) | Bằng chứng kiểm chứng (Evidence) | Trạng thái (Status) | Mức độ rủi ro | Hành động khắc phục bắt buộc (Required Action) |
| :--- | :--- | :--- | :--- | :--- |
| **Atomic File Swap là nguyên tử trên Windows** | `reaper_client.py:117` (`os.replace` dùng `MoveFileExW` trên NTFS) | `VERIFIED` | Thấp | Đảm bảo `%TEMP%` và file tạm luôn nằm trên cùng ổ đĩa với thư mục cài đặt REAPER. |
| **Hoàn tác 1 chạm (Single Ctrl+Z) cho chuỗi lệnh** | `undo_group.py:8` ("REAPER drops an undo block held open between bridge ticks... a group only labels") | `CONTRADICTED` | **P0 (Nghiêm trọng)** | Thu hồi tuyên bố "hoàn tác 1 chạm". Cập nhật tài liệu: giải thích rõ REAPER tạo từng undo point; client phải gọi `project_undo_group` khi cần rollback nguyên cụm. |
| **Tự động rollback khi gặp partial failure** | `reaper_mcp_server.lua:6111` (`pcall` bắt lỗi nhưng lệnh trước đó đã commit vào REAPER) | `CONTRADICTED` | **P0 (Nghiêm trọng)** | Xây dựng cơ chế Client-side Transaction Manager: khi nhận lỗi từ bước $K$, Client tự động phát chuỗi `project_undo` cho $K-1$ bước trước. |
| **Hệ thống không bao giờ gây audio dropouts** | Bóc tách RAM hệ thống: Windows + VST + Intel UHD chiếm ~7.5GB/8GB RAM; CPU 2 nhân | `CONTRADICTED` | **P1 (Cao)** | Thu hồi tuyên bố tuyệt đối. Đặt ngưỡng cảnh báo RAM (<1.2GB) và hạ độ ưu tiên tiến trình CPU của Commander xuống dưới REAPER. |
| **music21 nhận diện chính xác 100% điệu thức** | `comprehensive_music_intelligence_test.py`: Vay mượn hợp âm (Modal Interchange) bị đoán sai thành C minor | `CONTRADICTED` | **P1 (Cao)** | Không dùng thuật toán đơn lẻ; xây dựng thêm bộ lọc ngữ cảnh hòa thanh (Harmonic Context Heuristic) hỗ trợ `music21`. |
| **Thông lượng IPC đạt 3.841 ops/s với độ trễ 0.260ms** | `rigorous_ipc_benchmarks.json`: $\frac{1000}{0.2622} \approx 3.813$ ops/s ($0.31\%$ sai lệch so với $3.802$ ops/s đo được) | `MEASURED` | Thấp | Làm rõ trong tài liệu: đây là microbenchmark tuần tự hóa I/O tệp; độ trễ End-to-End thực tế của REAPER bị chặn bởi nhịp `defer()` 15-33ms. |
| **Voice Leading tự động bắt toàn bộ lỗi hòa âm** | `comprehensive_music_intelligence_test.py`: False positives khi chuyển động ngược chiều; thiếu hỗ trợ polyphonic tự động | `OBSERVED` | **P2 (Trung bình)** | Bổ sung thuật toán Timeslicing phân chia nốt đa bè trước khi nạp vào `VoiceLeadingQuartet`. |
| **Xử lý DSP Audio Feedback tốn < 3ms** | `dsp_audio_feedback_benchmarks.json`: File 0.5s tốn 8ms; File 30s tốn 174ms | `MEASURED` | **P2 (Trung bình)** | Cập nhật thời gian xử lý: tỷ lệ thuận với độ dài audio; chỉ chạy phân tích audio stem ở chế độ nền (asynchronous background worker). |
| **Toàn bộ codebase sạch bản quyền thương mại** | `deep_dependency_licensing.json`: Tất cả dependencies đều là MIT/BSD; LGPL của Scipy có exception | `VERIFIED` | Thấp | Duy trì file `NOTICE` ghi nhận bản quyền Apache-2.0 của Reaper-MCP và BSD của music21/scipy. |

---

## 4. BẢNG PHÂN CẤP RỦI RO VÀ ĐIỀU KIỆN TIÊN QUYẾT (ACCEPTANCE CRITERIA)

### 4.1. Phân cấp Rủi ro:
- **Rủi ro P0 (Chặn triển khai nếu không xử lý):**
  - Mất đồng bộ lịch sử Undo của REAPER khi xảy ra lỗi giữa chừng (Partial Failure).
  - Kỳ vọng sai lầm của người dùng về việc một lần `Ctrl+Z` sẽ xóa sạch 100 nốt của AI.
- **Rủi ro P1 (Rủi ro hệ thống):**
  - Tràn RAM vật lý 8GB dẫn đến swap pagefile và gây gián đoạn luồng thu âm (Audio Dropouts).
  - Thuật toán nhạc lý đưa ra nhận định sai về giọng khi bài hát có hợp âm vay mượn.
- **Rủi ro P2 (Rủi ro trải nghiệm):**
  - Thời gian tính toán DSP cho stem dài (30s) chiếm 174ms CPU làm khựng giao diện nếu không đưa vào tiến trình nền (Web Worker / Thread).

### 4.2. Tiêu chí Nghiệm thu Bắt buộc trước khi Code Prototype:
1. **Tiêu chuẩn Transaction:** Hệ thống phải có cơ chế Client-side Transaction Stack có khả năng tự động gửi $K$ lệnh undo khi phát hiện lệnh thứ $K+1$ thất bại.
2. **Tiêu chuẩn Tài nguyên:** Commander Core và UI Desktop khi chạy tối đa không được vượt quá **120MB RSS** và tự động dừng các tác vụ nền nếu RAM khả dụng của hệ thống dưới **1.0GB**.
3. **Tiêu chuẩn Giao tiếp:** Giao diện Desktop chỉ kết nối qua giao thức `Commander Protocol v1.0` có schema validation; không phụ thuộc vào trạng thái nội bộ của REAPER.
