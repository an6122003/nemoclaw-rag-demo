# BẮT ĐẦU TỪ ĐÂY · START HERE

**Workshop AI trên DGX Spark — cài đặt và trình diễn**
**DGX Spark AI Workshop — setup and presenting**

> Bạn **không cần biết lập trình**. Chỉ cần gõ đúng một lệnh.
> You do **not** need to know how to program. You type one command.
>
> Nếu có gì sai, chụp ảnh màn hình (hoặc gửi tệp `setup-log.txt`) cho người phụ trách.
> If anything goes wrong, send a photo of the screen (or the file `setup-log.txt`) to the organiser.
>
> Bản Word để in: [docs/Huong-dan-Workshop-AI-DGX-Spark.docx](docs/Huong-dan-Workshop-AI-DGX-Spark.docx)
> Printable Word version (Vietnamese): same file.

---

## Đây là gì? · What is this?

Ba bài thực hành AI, chạy **hoàn toàn trên máy DGX Spark** — không gửi dữ liệu lên internet:
Three hands-on AI labs, running **entirely on the DGX Spark** — nothing is sent to the internet:

| | Bài · Lab | Khán giả sẽ thấy · The audience sees |
|---|---|---|
| **1** | Tinh chỉnh mô hình · Fine-tuning | Một mô hình nhỏ được "dạy lại" trong vài phút, rồi so sánh trước/sau · A small model retrained in minutes, compared before/after |
| **2** | RAG với NemoClaw · RAG with NemoClaw | Hỏi 28 tài liệu kỹ thuật, câu trả lời kèm nguồn · Ask 28 manuals; every answer shows its source |
| **3** | Agent phân tích dữ liệu · Agentic workflow | Hỏi bằng tiếng Việt, AI tự đọc Excel, phân tích, vẽ biểu đồ, xuất báo cáo · Ask in Vietnamese; the AI reads Excel, analyses, charts, exports a report |
| **4** | Thử thách OpenClaw · OpenClaw challenge | Các đội tự giao việc cho agent OpenClaw, xây sản phẩm và trình diễn · Teams give the OpenClaw agent their own jobs, build something and show it |

Bài 1–3 đều đặt **trước / sau** cạnh nhau: trước và sau khi tinh chỉnh, không có và có
RAG, chỉ có mô hình và có agent.
Labs 1–3 each put **before / after** side by side: before and after fine-tuning,
without and with RAG, the model alone and the agent with its tools.

---

## Cần chuẩn bị · What you need

| | |
|---|---|
| ✅ | Máy **DGX Spark** đã bật, có **internet** (chỉ cần khi cài đặt; sau đó chạy không cần internet, kể cả khi khởi động lại) · The **DGX Spark**, on, with **internet** (for setup only; afterwards it runs offline, restarts included) |
| ✅ | Màn hình, bàn phím, chuột · A screen, keyboard and mouse |
| ✅ | Khoảng **150 GB** trống và **2 giờ** · About **150 GB** free and **2 hours** |
| ✅ | **Mật khẩu đăng nhập** của máy · The machine's **login password** |

---

## Bước 1 · Mở Terminal · Step 1 · Open a Terminal

Nhấn **Ctrl + Alt + T**, hoặc tìm ứng dụng **Terminal**.
Press **Ctrl + Alt + T**, or search for the **Terminal** app.

> Dán lệnh vào Terminal bằng **Ctrl + Shift + V** (không phải Ctrl + V).
> Paste into the Terminal with **Ctrl + Shift + V** (not Ctrl + V).

---

## Bước 2 · Dán MỘT lệnh duy nhất · Step 2 · Paste ONE command

Dán lệnh này rồi nhấn **Enter**:
Paste this command and press **Enter**:

```bash
curl -fsSL https://raw.githubusercontent.com/an6122003/nemoclaw-rag-demo/main/install.sh | bash
```

Lệnh này tự tải workshop về thư mục `~/dgx-workshop`, cài đặt mọi thứ, kiểm tra cả
3 bài, rồi mở workshop trên trình duyệt.
It downloads the workshop into `~/dgx-workshop`, installs everything, checks all
three labs, and opens the workshop in the browser.

Sau đó:
Then:

1. Chương trình hiện thông báo về phần mềm sẽ được cài. Nhấn **Enter** để đồng ý.
   A notice lists the software it installs. Press **Enter** to agree.
2. Máy hỏi **mật khẩu**: gõ mật khẩu đăng nhập rồi nhấn Enter. **Khi gõ sẽ không
   hiện ký tự nào — đó là bình thường.**
   It asks for your **password**: type your login password and press Enter.
   **Nothing appears while you type — that is normal.**
3. Để máy tự chạy 1-2 giờ. **Đừng đóng cửa sổ.** Phần lâu nhất là tải mô hình AI.
   Thiếu phần mềm nào (Docker, Python…) thì chương trình tự cài.
   Let it run for 1-2 hours. **Do not close the window.** Downloading the AI
   models is the slow part. Anything missing (Docker, Python…) is installed for you.

> Chạy lại **đúng lệnh này** bất cứ lúc nào để cập nhật hoặc cài tiếp — hoàn toàn an
> toàn, các bước đã xong sẽ được bỏ qua.
> Run **the same command** again at any time to update or resume — it is completely
> safe; finished steps are skipped.

### ✅ Khi thành công · When it works

Bạn thấy khung màu xanh **SETUP COMPLETE / CÀI ĐẶT HOÀN TẤT**, và trình duyệt tự mở
workshop. Trên màn hình nền có thêm biểu tượng **DGX Spark Workshop**.

You see a green **SETUP COMPLETE** box and the browser opens the workshop. A
**DGX Spark Workshop** icon appears on the desktop.

### ⚠️ Khi có phần cần hỗ trợ · When something needs help

Bạn thấy khung màu vàng và bảng trạng thái của 3 bài. Bài nào có dấu **!** vẫn chạy
được ở chế độ rút gọn; bài có dấu **✘** cần hỗ trợ. Gửi tệp `setup-log.txt` trong thư
mục `~/dgx-workshop` cho người phụ trách. **Chạy lại lệnh ở Bước 2 hoàn toàn an toàn** —
các bước đã xong sẽ được bỏ qua.

You see a yellow box and a status line for each lab. A lab marked **!** still works
in a reduced mode; **✘** needs help. Send `setup-log.txt` from the folder to the
organiser. **Running the command from Step 2 again is completely safe** — finished
steps are skipped.

---

## Những lần sau · Next time

Bấm đúp biểu tượng **DGX Spark Workshop** trên màn hình nền, hoặc:
Double-click **DGX Spark Workshop** on the desktop, or:

```bash
bash ~/dgx-workshop/start.sh
```

Trình duyệt mở `http://127.0.0.1:8090/`. **Giữ cửa sổ Terminal mở** khi trình diễn.
Nhấn **Ctrl-C** để dừng.
The browser opens `http://127.0.0.1:8090/`. **Keep the Terminal window open** while
presenting. Press **Ctrl-C** to stop.

Nếu máy vừa bật lên hoặc vừa khởi động lại, lần mở đầu tiên mất khoảng **1 phút** (tối đa
5 phút) để NemoClaw khởi động — cứ chờ. **Không cần internet.**
Right after the computer is switched on or restarted, the first start takes about **1
minute** (at most 5) while NemoClaw starts — just wait. **No internet needed.**

> 💡 Trước khi khán giả vào, hãy bấm thử một câu hỏi ở mỗi bài để máy "khởi động".
> 💡 Before the audience arrives, click one question in each lab to warm things up.

---

## Kịch bản trình diễn · Demo script (≈ 15 phút · minutes)

Góc trên bên phải có nút **VI / EN** để đổi ngôn ngữ. Các tab ở đầu trang: **Tổng quan,
01 Tinh chỉnh, 02 RAG, 03 Agent, 04 OpenClaw · Thử thách, 05 Doanh nghiệp**.
The **VI / EN** buttons top right switch language. Tabs along the top: **Overview,
01 Fine-tuning, 02 RAG, 03 Agent, 04 OpenClaw · Challenge, 05 Enterprise**.

### Buổi chiều · Doanh nghiệp (tab 05) · Afternoon business session

1. Mở tab **05 Doanh nghiệp**. Chọn **Phân loại hộp thư khách hàng** (2.400 tin nhắn).
   Open tab **05 Enterprise**, pick **Customer inbox triage** (2,400 messages).
2. Bấm **Chạy 300 mục**. Lần đầu máy chủ xử lý hàng loạt tự khởi động (2–4 phút) — hãy
   bấm trước khi khán giả vào. Sau đó khoảng **200 tin nhắn mỗi phút**.
   Press **Run 300 items**. The first time, the batch engine starts by itself (2–4 minutes):
   press it before the audience arrives. Then about **200 messages a minute**.
3. Chỉ vào **độ chính xác so với đáp án**, dòng **Bắt được …/… tin khẩn cấp**, và bấm một
   dòng để xem tin nhắn, kết quả của AI, đáp án và bản nháp trả lời. Bấm **Tải Excel**.
   Point at the accuracy, the critical messages caught, click a row, press **Download Excel**.
4. Chọn **Hóa đơn đầu vào sang Excel** (1.000 hóa đơn scan), bấm **Chạy 100 mục**: khoảng
   **35 hóa đơn mỗi phút**, lỗi cộng sai và hóa đơn trùng được đánh dấu **Cần kiểm tra**.
   Pick **Supplier invoices into Excel**, press **Run 100 items**: about 35 a minute.
5. Chọn **Chấm điểm chất lượng cuộc gọi** (300 cuộc gọi ghi âm), bấm **Chạy 30 mục**: máy
   chuyển giọng nói thành văn bản rồi chấm theo checklist, khoảng **19 cuộc gọi mỗi phút**.
   Bấm một dòng để nghe ghi âm, xem bản chép lời và phiếu chấm bên cạnh đáp án.
   Pick **Call quality scoring** (300 recordings), press **Run 30 items**: speech-to-text
   then the QA checklist, about 19 calls a minute. Click a row to play the call and see
   its transcript and scorecard next to the answer key.
6. Kéo xuống **Chi phí**: nhập khối lượng mỗi tháng của khách và so sánh với API đám mây;
   dòng **Cả 3 việc mỗi tháng** cho thấy thời gian hoàn vốn khi một máy làm tất cả.
   Scroll to **What it costs**, type in the customer's monthly volumes; **All 3 jobs
   together** shows the payback when one machine does everything.
7. So sánh: chọn **Ollama · từng mục** rồi chạy 20 tin nhắn — chậm hơn nhiều lần. Đây là lý
   do doanh nghiệp dùng máy chủ theo lô (vLLM) cho công việc hàng loạt.
   Compare: switch to **Ollama · one at a time** and run 20 messages: several times slower.

Máy chủ tự tắt sau 30 phút không dùng để trả bộ nhớ cho các bài lab. **Làm lại từ đầu**
xóa kết quả để trình diễn lại. The engine switches itself off after 30 idle minutes;
**Start over** clears the results for another demo.

### Bài 1 · Tinh chỉnh (5 phút)

1. Chỉ vào **Dữ liệu huấn luyện**: 86 ví dụ dạy mô hình trở thành "Aurora".
2. Bấm **Bắt đầu tinh chỉnh** và cho khán giả xem đường **loss** giảm dần (vài phút).
   *Nếu không muốn chờ:* mô hình đã được huấn luyện sẵn khi cài đặt — bỏ qua bước này.
3. Ở phần **Trước và sau**, bấm câu **"Bạn là trợ lý của công ty nào, và bạn giúp được gì?"**
   → **Trước:** "Tôi là Qwen… Alibaba Cloud". **Sau:** "Tôi là Aurora, trợ lý kỹ thuật
   của Aurora Grid…" và có chữ ký ở cuối.
4. Bấm **"Kể cho tôi nghe một câu chuyện cười đi."** → mô hình sau khi tinh chỉnh lịch sự
   từ chối vì ngoài phạm vi.
5. Câu cần nói: *"Cả hai nhận cùng một prompt ghi 'You are Qwen' — chỉ trọng số khác."*

### Bài 2 · RAG (4 phút)

1. Bấm **"Tôi phải siết đầu cực DC với lực bao nhiêu?"** → **25 N·m cho AX-400, 35 N·m
   cho AX-600**: hệ thống phân biệt hai sản phẩm gần giống nhau.
2. Bấm câu có nhãn **Then chốt** **"Sau khi ngắt cầu dao DC, phải chờ bao lâu…"** → **12 phút** theo
   SB-2025-01, và nói rõ quy tắc 5 phút cũ đã hết hiệu lực. **Đây là phần quan trọng
   nhất** — mở danh sách **Nguồn** để cho thấy tài liệu cũ vẫn còn trong thư viện.
3. Bấm **"Giá cổ phiếu của Aurora Grid Systems hôm nay là bao nhiêu?"** → hệ thống
   **từ chối**, vì tài liệu không có. Nó không bịa.
4. Chỉ vào hai cột của câu trả lời: **Không có RAG** (cùng mô hình, không có tài liệu —
   thường sai, ví dụ tủ AX-600 "1000 lít") và **Có RAG** (đúng theo tài liệu, kèm nguồn).

### Bài 3 · Agent (5 phút)

1. Bấm câu có nhãn **Then chốt** **"Phân tích doanh số theo vùng và cho biết khu vực nào
   tăng trưởng tốt nhất."** — đúng câu trong slide.
2. Chỉ vào bốn ô **Người dùng → NeMo Claw → Python → Kết quả** đang sáng lên, và danh sách
   **Agent đang làm gì**: đọc file Excel → phân tích bằng pandas → vẽ biểu đồ → xuất Excel.
3. Kết quả: **Đà Nẵng tăng trưởng tốt nhất, +64,5%**; TP. Hồ Chí Minh lớn nhất nhưng tăng
   chậm hơn; Hà Nội giảm. Bấm **Tải báo cáo Excel** để mở báo cáo.
4. Ô **Nhận định** đặt cạnh nhau **Chỉ có mô hình** (không mở được file, chỉ đoán hoặc xin
   dữ liệu) và **Agent + công cụ** (số liệu thật).
5. Câu cần nói: *"Mô hình chỉ quyết định gọi công cụ nào. Mọi con số đều do Python tính."*

### Thử thách OpenClaw · OpenClaw challenge (10:00 – 11:10)

1. Mở tab **04 OpenClaw · Thử thách**, bấm nút xanh **Mở OpenClaw** (hoặc gõ
   `localhost:8090/openclaw`). OpenClaw mở ở trang Chat.
   Open tab **04**, press **Open OpenClaw** (or type `localhost:8090/openclaw`).
2. Các đội giao việc bằng ngôn ngữ thường ngày; có 4 **ý tưởng khởi đầu** để sao chép.
   Teams describe a job in plain language; four **starter ideas** can be copied.
3. **Đổi mô hình:** bấm tên mô hình dưới ô nhập tin nhắn (đang ghi "nemotron · Off") →
   **Workshop Ollama → qwen → Save**, hoặc gõ `/model qwen`; quay lại bằng `/model nemotron`.
   Các bài 1–3 luôn dùng Nemotron.
   **Switch model:** click the model name under the message box → **Workshop Ollama →
   qwen → Save**, or type `/model qwen`; `/model nemotron` switches back. Labs 1–3 always
   use Nemotron.
4. Mẹo: `/new` để mở cuộc chat mới; agent dừng giữa chừng thì trả lời "tiếp tục".
   Tips: `/new` for a fresh chat; if the agent stops halfway, reply "continue".

---

## Nếu có trục trặc · If something breaks

| Hiện tượng · Symptom | Cách xử lý · What to do |
|---|---|
| Tải mô hình chậm còn vài KB/s · A model download crawls at a few KB/s | Không cần làm gì: sau khoảng 1 phút chương trình tự kết nối lại, phần đã tải được giữ nguyên · Nothing to do: after about a minute setup reconnects and keeps what it already downloaded |
| Trình duyệt không tự mở · Browser does not open | Mở thủ công · Open `http://127.0.0.1:8090/` |
| `Permission denied` | Dùng `bash ~/dgx-workshop/start.sh` (có chữ `bash` ở đầu) |
| Trang trắng · Blank page | Nhấn `F5` · Press `F5` |
| Câu trả lời đầu tiên rất chậm · First answer is slow | Bình thường, mô hình đang nạp · Normal: the model is loading |
| Góc trên có chấm xám · Grey dot at the top | Đóng Terminal, chạy lại `bash ~/dgx-workshop/start.sh` · Close the Terminal, run it again |
| Máy vừa khởi động lại, không có internet · Restarted without internet | Bình thường: bấm biểu tượng workshop, chờ khoảng 1 phút · Normal: double-click the workshop icon, wait about a minute |
| "Mở OpenClaw" không mở được · "Open OpenClaw" does not open | Mở trên trình duyệt của chính máy Spark, không phải laptop khác · Use the Spark's own browser, not another laptop |
| Bài 2 hoặc 3 ghi "chế độ trực tiếp" · Lab 2 or 3 says "direct mode" | Vẫn trình diễn được. Để sửa (≈15 phút): đóng cửa sổ workshop, chạy lại lệnh ở Bước 2 · Still works. To repair (≈15 min): close the workshop window, re-run the Step 2 command |
| Vẫn không được · Still stuck | Chạy lại lệnh ở Bước 2, gửi `setup-log.txt` · Re-run the Step 2 command, send `setup-log.txt` |

---

## Ghi chú cho người phụ trách kỹ thuật · Note for the technical organiser

Xem [README.md](README.md): kiến trúc, các bước của `setup.sh`, cấu hình trong
`workshop.env`, và phần **đã kiểm chứng / chưa kiểm chứng**.
See [README.md](README.md) for the architecture, what `setup.sh` does, the
settings in `workshop.env`, and what is verified versus not yet verified.
