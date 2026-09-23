# BẮT ĐẦU TỪ ĐÂY · START HERE

**Trợ lý tài liệu Aurora Grid — hướng dẫn cài đặt**
**Aurora Grid document assistant — setup guide**

> Bạn **không cần biết lập trình** để làm việc này.
> You do **not** need to know how to program to do this.
>
> Chỉ cần làm theo đúng 4 bước. Nếu có gì sai, chụp ảnh màn hình và gửi cho
> người đã đưa bạn thư mục này.
> Just follow the 4 steps. If anything goes wrong, take a photo of the screen and
> send it to whoever gave you this folder.

---

## Đây là gì? · What is this?

Một chương trình trình diễn: người xem gõ câu hỏi bằng tiếng Việt hoặc tiếng
Anh, và hệ thống trả lời dựa trên 28 tài liệu kỹ thuật — kèm theo đúng đoạn tài
liệu làm căn cứ.

A demo program: your audience types a question in Vietnamese or English and the
system answers using 28 technical documents — showing exactly which passage the
answer came from.

Mọi thứ chạy **trên máy DGX Spark này**. Không có dữ liệu nào gửi lên internet.
Everything runs **on this DGX Spark**. Nothing is sent to the internet.

---

## Cần chuẩn bị gì? · What you need

| | |
|---|---|
| ✅ | Máy **DGX Spark** đã bật nguồn và kết nối internet · The **DGX Spark**, powered on with internet |
| ✅ | Khoảng **45 phút** · About **45 minutes** |
| ✅ | Khoảng **25 GB** dung lượng trống · About **25 GB** free disk space |
| ✅ | Một màn hình và bàn phím · A screen and keyboard |

Không cần cài gì thêm. Chương trình tự cài mọi thứ.
Nothing else to install. The setup installs everything itself.

---

## Bước 1 · Copy thư mục này sang máy Spark
## Step 1 · Copy this folder to the Spark

Copy **toàn bộ thư mục** `hands-on-2` (thư mục chứa tệp `START-HERE.md` này)
sang máy DGX Spark. Ví dụ đặt vào thư mục cá nhân:

Copy the **whole folder** `hands-on-2` (the folder containing this
`START-HERE.md` file) onto the DGX Spark. For example, into the home folder.

Có thể dùng USB, hoặc nếu người đưa đã hướng dẫn thì dùng lệnh `scp`.
Use a USB stick, or `scp` if the person who gave it to you showed you how.

> ⚠️ Copy **cả thư mục**, không chỉ vài tệp. Trong đó có sẵn 28 tài liệu và
> chỉ mục tìm kiếm.
> ⚠️ Copy the **whole folder**, not just a few files. It contains the 28
> documents and a pre-built search index.

---

## Bước 2 · Mở Terminal
## Step 2 · Open a Terminal

Trên DGX Spark: nhấn chuột phải vào màn hình nền → **Open in Terminal**.
Hoặc tìm ứng dụng **Terminal** trong danh sách phần mềm.

On the DGX Spark: right-click the desktop → **Open in Terminal**.
Or search for the **Terminal** app.

Một cửa sổ nền đen (hoặc trắng) hiện ra. Đó là bình thường.
A black (or white) window appears. That is normal.

---

## Bước 3 · Chạy một lệnh duy nhất
## Step 3 · Run one single command

Gõ đúng hai dòng này, mỗi dòng bấm **Enter**.
Type exactly these two lines, pressing **Enter** after each.

```bash
cd ~/hands-on-2
./setup-everything.sh
```

> Nếu bạn copy thư mục vào chỗ khác, thay `~/hands-on-2` bằng đường dẫn thật.
> If you copied the folder somewhere else, replace `~/hands-on-2` with the real
> path.

Nếu báo `Permission denied`, gõ thêm dòng này rồi chạy lại:
If it says `Permission denied`, type this line then run it again:

```bash
chmod +x setup-everything.sh
```

---

## Bước 4 · Chờ và kiểm tra kết quả
## Step 4 · Wait and check the result

Chương trình sẽ tự chạy 7 bước và in tiến độ bằng **cả tiếng Việt và tiếng Anh**.
The setup runs 7 steps and prints progress in **both Vietnamese and English**.

Bạn sẽ thấy các bước như thế này:
You will see steps like this:

```
Step 1. Checking this computer
        Kiểm tra máy tính
   ✔  Docker is running
      Docker đang chạy

Step 3. Downloading the AI models (about 8 GB)
        Tải mô hình AI (khoảng 8 GB)
   Downloading qwen3-embedding:4b … this is the slow part
   Đang tải qwen3-embedding:4b … đây là phần lâu nhất
```

**Bước 3 là lâu nhất** (khoảng 15–25 phút) vì phải tải mô hình AI.
**Step 3 is the slowest** (about 15–25 minutes) because it downloads the AI
models. Bạn cứ để máy chạy, đừng đóng cửa sổ.
Just let it run; do not close the window.

### ✅ Nếu thành công · If it worked

Bạn sẽ thấy dòng chữ lớn màu xanh:
You will see a large green message:

```
   ┌────────────────────────────────────────────────────────┐
   │   ✔  S E T U P   C O M P L E T E                       │
   │      C À I   Đ Ặ T   H O À N   T Ấ T                    │
   └────────────────────────────────────────────────────────┘
```

**Vậy là xong.** Chuyển sang phần trình diễn bên dưới.
**You are done.** Go to the presentation section below.

### ❌ Nếu có lỗi · If something went wrong

Bạn sẽ thấy dòng chữ lớn màu đỏ:
You will see a large red message:

```
   ┌────────────────────────────────────────────────────────┐
   │   ✘  S E T U P   N E E D S   H E L P                   │
   │      C Ầ N   H Ỗ   T R Ợ                              │
   └────────────────────────────────────────────────────────┘
```

Hãy làm 3 việc sau:
Do these 3 things:

1. **Chụp ảnh toàn bộ màn hình** (hoặc gửi tệp `setup-log.txt` trong thư mục).
   **Take a photo of the whole screen** (or send the `setup-log.txt` file from
   the folder).
2. Gửi cho người đã đưa bạn thư mục này.
   Send it to whoever gave you this folder.
3. Sau khi họ trả lời, chạy lại `./setup-everything.sh` — chạy lại **hoàn toàn
   an toàn**, nó sẽ bỏ qua những bước đã xong.
   Once they reply, run `./setup-everything.sh` again — re-running is **completely
   safe**, it skips whatever already finished.

---

## Vào ngày trình diễn · On the day

Mở Terminal và chạy:
Open a Terminal and run:

```bash
cd ~/hands-on-2
./demo/start.sh --retrieval local
```

Trình duyệt sẽ **tự động mở**. Nếu không, mở thủ công:
The browser opens **by itself**. If it does not, open it manually:

```
http://127.0.0.1:8090/
```

**Giữ cửa sổ Terminal mở** trong suốt buổi trình diễn. Nhấn `Ctrl-C` để dừng.
**Keep the Terminal window open** during the presentation. Press `Ctrl-C` to stop.

### Trên màn hình có gì · What is on the screen

| | |
|---|---|
| **EN / VI** | Nút chuyển ngôn ngữ ở góc trên bên phải · Language switch, top right |
| **Ô câu hỏi** | Gõ câu hỏi rồi bấm **Hỏi** · Type a question, press **Ask** |
| **Quy trình đang chạy** | Hiện từng bước đang làm gì · Shows each step as it happens |
| **Câu trả lời** | Kèm tên tài liệu · With the document name |
| **Nguồn của câu trả lời** | Bấm vào để đọc đoạn tài liệu gốc · Click to read the original passage |
| **Thử các câu hỏi sau** | Bấm vào để hỏi ngay, không cần gõ · Click to ask instantly |
| **Thư viện tài liệu** | 28 tài liệu, bấm để xem · All 28 documents, click to preview |

### Bài trình diễn gợi ý · Suggested demo

Bấm vào các nút có sẵn, **không cần gõ tay**.
Click the ready-made buttons — **no typing needed**.

1. **"Dung lượng khả dụng của tủ pin AX-600 là bao nhiêu?"**
   → Trả lời **558 kWh**.

2. **"Tôi phải siết đầu cực DC với lực bao nhiêu?"**
   → **25 N·m cho AX-400** và **35 N·m cho AX-600**. Hai tủ gần giống nhau
   nhưng hệ thống vẫn phân biệt đúng.

3. **"Sau khi ngắt cầu dao DC, phải chờ bao lâu trước khi tháo nắp module?"**
   → **12 phút**, theo SB-2025-01, và hệ thống nói rõ hướng dẫn cũ 5 phút đã
   hết hiệu lực. **Đây là phần quan trọng nhất** — hãy bấm vào dòng nguồn thứ
   ba để cho khán giả thấy tài liệu cũ vẫn còn trong thư viện.
   → **12 minutes**, per SB-2025-01, and it says the old 5-minute rule is
   withdrawn. **This is the key moment** — click source row 3 to show the
   withdrawn instruction is still in the library.

4. **"Giá cổ phiếu của Aurora Grid Systems hôm nay là bao nhiêu?"**
   → Hệ thống **từ chối trả lời** vì tài liệu không có. Đây là điều quan trọng:
   nó không bịa. · It **refuses**, because the documents do not contain it. It
   does not invent an answer.

Bấm **EN** ở góc phải để trình diễn lại bằng tiếng Anh.
Click **EN** top right to run the same demo in English.

---

## Nếu có trục trặc · If something breaks

| Hiện tượng · Symptom | Cách xử lý · What to do |
|---|---|
| Trình duyệt không mở · Browser does not open | Mở thủ công `http://127.0.0.1:8090/` |
| Báo "could not reach…" | Đóng Terminal, chạy lại `./demo/start.sh --retrieval local` |
| Trả lời rất chậm lần đầu · First answer is slow | Bình thường — hỏi thử một câu trước khi khán giả vào · Normal — ask one warm-up question first |
| Trang trắng · Blank page | Nhấn `F5` để tải lại · Press `F5` to reload |
| Vẫn không được · Still stuck | Chạy lại `./setup-everything.sh` rồi chụp ảnh gửi đi · Re-run and send a photo |

> 💡 **Mẹo:** trước khi khán giả vào, hãy hỏi thử một câu bất kỳ để máy "khởi
> động". Câu hỏi đầu tiên luôn chậm hơn.
> 💡 **Tip:** before the audience arrives, ask one throwaway question to warm
> things up. The first question is always slower.

---

## Ghi chú cho người phụ trách kỹ thuật
## Note for the technical organizer

Phần này dành cho người cài đặt, không cần đưa cho người trình diễn.
This part is for whoever set it up; no need to give it to the presenter.

**What `setup-everything.sh` does**, in order: host preflight → install/start
Ollama → pull `qwen3-embedding:4b` + `qwen3:8b` → install NemoClaw → `nemoclaw
onboard` (with `--resume` retry) → `fix-sandbox-policy.sh` → `lab-setup.sh` →
verification. Full output is written to `setup-log.txt`.

`--check-only` inspects the host and downloads models but stops before creating
the sandbox. Safe to run any time.

**Not verified on DGX hardware.** This bundle was authored and tested on macOS
(Apple M5 / Docker Desktop). The Spark path is authored from the same scripts,
but has never been executed on a DGX Spark. Things most likely to differ:

- `scripts/fix-sandbox-policy.sh` may report nothing to fix. The IPv6 host-gateway
  defect it repairs is a Docker Desktop artefact; a Linux host gateway is
  ordinary RFC1918, so the shipped policy should already work.
- The `TMPDIR` requirement almost certainly still applies and is handled by
  `lab-setup.sh`.
- `NEMOCLAW_PROVIDER=ollama` works where Ollama is a real local install. It is
  the documented macOS path that fails when Ollama is not a Homebrew install,
  which is why the authoring machine used a custom endpoint instead.

**Model choice.** The Spark has an NVIDIA GPU, so you may prefer to serve chat
with managed vLLM/NIM and keep Ollama for embeddings only. See
`deploy/dgx-spark-setup.sh --inference managed-vllm`. The embedding model is
required either way — NemoClaw ships no embedding server.

**Timings on the authoring machine**, for calibration: sandbox creation ~10 min,
index build (28 docs / 76 chunks) ~1 min, each demo answer ~7 s.
