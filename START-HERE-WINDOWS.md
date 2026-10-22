# BẮT ĐẦU TỪ ĐÂY · START HERE — WINDOWS

**Workshop AI trên NVIDIA RTX Spark (Windows) — cài đặt và trình diễn**
**AI Workshop on the NVIDIA RTX Spark (Windows) — setup and presenting**

> Bạn **không cần biết lập trình**. Chỉ cần dán đúng một lệnh.
> You do **not** need to know how to program. You paste one command.
>
> Nếu có gì sai, gửi tệp `setup-log.txt` (trong thư mục `ai-workshop`) cho người phụ trách.
> If anything goes wrong, send the file `setup-log.txt` (in the `ai-workshop` folder) to the organiser.
>
> Máy DGX Spark (Linux) dùng hướng dẫn khác: [START-HERE.md](START-HERE.md).
> The DGX Spark (Linux) has its own guide: [START-HERE.md](START-HERE.md).

---

## Đây là gì? · What is this?

Bản Windows của workshop, cho các máy **NVIDIA RTX Spark** (Windows 11 trên chip Arm).
Mọi thứ chạy **ngay trên máy**, không gửi dữ liệu lên internet:
The Windows edition of the workshop, for **NVIDIA RTX Spark** PCs (Windows 11 on Arm).
Everything runs **on the PC itself**; nothing is sent to the internet:

| | Bài · Lab | Khán giả sẽ thấy · The audience sees |
|---|---|---|
| **1** | Tinh chỉnh mô hình · Fine-tuning | Một mô hình nhỏ được "dạy lại" trên GPU, rồi so sánh trước/sau · A small model retrained on the GPU, compared before/after |
| **2** | RAG trên máy · RAG on the PC | Hỏi 28 tài liệu kỹ thuật, câu trả lời kèm nguồn · Ask 28 manuals; every answer shows its source |
| **3** | Agent phân tích dữ liệu · Agentic workflow | Hỏi bằng tiếng Việt, AI tự đọc Excel, phân tích, vẽ biểu đồ, xuất báo cáo · Ask in Vietnamese; the AI reads Excel, analyses, charts, exports a report |
| **04** | Doanh nghiệp · Enterprise | Hàng nghìn tin nhắn, hóa đơn và cuộc gọi được xử lý theo lô · Thousands of messages, invoices and calls processed in batches |

**Khác với bản DGX Spark · Different from the DGX Spark edition:**
không có sandbox NemoClaw (Bài 2–3 chạy trực tiếp trên máy) và không có tab thử thách
OpenClaw; tab Doanh nghiệp dùng llama.cpp thay cho vLLM.
there is no NemoClaw sandbox (Labs 2–3 run directly on the PC) and no OpenClaw
challenge tab; the Enterprise tab uses llama.cpp instead of vLLM.

---

## Cần chuẩn bị · What you need

| | |
|---|---|
| ✅ | Máy **RTX Spark** với Windows 11, có **internet** (chỉ cần khi cài đặt) · The **RTX Spark** with Windows 11, with **internet** (for setup only) |
| ✅ | Khoảng **70 GB** trống và **1–2 giờ** · About **70 GB** free and **1–2 hours** |
| ✅ | **Không cần** mật khẩu quản trị · **No** administrator password needed |

---

## Bước 1 · Mở PowerShell · Step 1 · Open PowerShell

Nhấn phím **Windows**, gõ **PowerShell**, rồi mở **Windows PowerShell** (hoặc **Terminal**).
Press the **Windows** key, type **PowerShell**, and open **Windows PowerShell** (or **Terminal**).

---

## Bước 2 · Dán MỘT lệnh duy nhất · Step 2 · Paste ONE command

Dán lệnh này (chuột phải để dán) rồi nhấn **Enter**:
Paste this command (right-click pastes) and press **Enter**:

```powershell
irm https://raw.githubusercontent.com/an6122003/nemoclaw-rag-demo/main/install.ps1 | iex
```

Lệnh này tải workshop về thư mục `ai-workshop` trong thư mục người dùng, cài mọi thứ,
huấn luyện thử mô hình mẫu, kiểm tra từng bài, rồi mở workshop trên trình duyệt.
It downloads the workshop into the `ai-workshop` folder of your user profile, installs
everything, trains the example model once, checks every lab, and opens the workshop
in the browser.

1. Một thông báo liệt kê phần mềm sẽ được cài. Nhấn **Enter** để đồng ý.
   A notice lists the software it installs. Press **Enter** to agree.
2. Để máy tự chạy. **Đừng đóng cửa sổ.** Phần lâu nhất là tải mô hình AI (khoảng 58 GB).
   Let it run. **Do not close the window.** The longest part is downloading the AI models (about 58 GB).
3. Cuối cùng là bảng tổng kết: mỗi phần **✔ sẵn sàng** hoặc **✘ cần hỗ trợ**.
   At the end, a summary: each part **✔ ready** or **✘ needs help**.

---

## Lần sau · Next time

Bấm đúp biểu tượng **RTX Spark Workshop** trên màn hình nền (hoặc trong menu Start).
Trình duyệt mở workshop tại **http://127.0.0.1:8090**.
Double-click **RTX Spark Workshop** on the desktop (or in the Start menu). The browser
opens the workshop at **http://127.0.0.1:8090**.

- **Đóng cửa sổ màu đen** sẽ dừng ứng dụng workshop. Ollama vẫn chạy nền để mô hình
  không phải nạp lại. **Closing the black window** stops the workshop app; Ollama keeps
  running in the background so the models stay loaded.
- Dừng hẳn mọi thứ · Stop everything: `powershell -ExecutionPolicy Bypass -File "$HOME\ai-workshop\windows\stop.ps1"`
- Cập nhật · Update: chạy lại đúng lệnh ở Bước 2 (mô hình đã tải được giữ nguyên) ·
  run the Step 2 command again (downloaded models are kept).
- Máy không cần internet sau khi cài · No internet needed after setup.

---

## Trình diễn · Presenting

Giống bản DGX Spark: xem phần trình diễn từng bài trong [START-HERE.md](START-HERE.md).
Tab Doanh nghiệp là **04** (không có tab OpenClaw), và nút chọn máy chủ ghi
**llama.cpp · theo lô** thay cho vLLM.
The same as on the DGX Spark: see each lab's walkthrough in [START-HERE.md](START-HERE.md).
The Enterprise tab is **04** (there is no OpenClaw tab), and the engine switch reads
**llama.cpp · in batches** instead of vLLM.

---

## Khi có lỗi · When something fails

| Bạn thấy · You see | Làm gì · What to do |
|---|---|
| `running scripts is disabled` | Dùng đúng lệnh `irm … \| iex` ở Bước 2, hoặc biểu tượng trên màn hình nền · Use the exact `irm … \| iex` command, or the desktop icon |
| ✘ ở một bài · ✘ on a lab | Chạy lại lệnh cài đặt (an toàn); nếu vẫn lỗi, gửi `setup-log.txt` · Run the install command again (safe); if it still fails, send `setup-log.txt` |
| "Ollama found no usable GPU" | Cập nhật driver NVIDIA của máy, rồi chạy lại lệnh cài đặt · Update the PC's NVIDIA driver, then run the install command again |
| "Smart App Control is on" | Nhờ IT tắt Smart App Control (Windows Security › App & browser control), rồi chạy lại lệnh cài đặt · Ask IT to turn off Smart App Control (Windows Security › App & browser control), then run the install command again |
| Tab Doanh nghiệp không hiện · No Enterprise tab | Phần này chưa cài xong: chạy lại lệnh cài đặt · It did not finish installing: run the install command again |

> Bản Windows được xây dựng trước khi có máy RTX Spark thật: nó đã được kiểm tra tự động
> trên máy Windows-on-Arm của GitHub (không có GPU). Lần cài đầu trên máy thật, hãy gửi
> `setup-log.txt` cho người phụ trách dù mọi thứ có vẻ ổn.
> The Windows edition was built before real RTX Spark hardware was available: it is tested
> automatically on GitHub's Windows-on-Arm machines (no GPU). After the first install on a
> real machine, send `setup-log.txt` to the organiser even if everything looks fine.
