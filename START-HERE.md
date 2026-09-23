# BẮT ĐẦU TỪ ĐÂY · START HERE

**Workshop AI trên DGX Spark — cài đặt và trình diễn**
**DGX Spark AI Workshop — setup and presenting**

> Bạn **không cần biết lập trình**. Chỉ cần gõ đúng một lệnh.
> You do **not** need to know how to program. You type one command.
>
> Nếu có gì sai, chụp ảnh màn hình (hoặc gửi tệp `setup-log.txt`) cho người phụ trách.
> If anything goes wrong, send a photo of the screen (or the file `setup-log.txt`) to the organiser.

---

## Đây là gì? · What is this?

Ba bài thực hành AI, chạy **hoàn toàn trên máy DGX Spark** — không gửi dữ liệu lên internet:
Three hands-on AI labs, running **entirely on the DGX Spark** — nothing is sent to the internet:

| | Bài · Lab | Khán giả sẽ thấy · The audience sees |
|---|---|---|
| **1** | Tinh chỉnh mô hình · Fine-tuning | Một mô hình nhỏ được "dạy lại" trong vài phút, rồi so sánh trước/sau · A small model retrained in minutes, compared before/after |
| **2** | RAG với NemoClaw · RAG with NemoClaw | Hỏi 28 tài liệu kỹ thuật, câu trả lời kèm nguồn · Ask 28 manuals; every answer shows its source |
| **3** | Agent phân tích dữ liệu · Agentic workflow | Hỏi bằng tiếng Việt, AI tự đọc Excel, phân tích, vẽ biểu đồ, xuất báo cáo · Ask in Vietnamese; the AI reads Excel, analyses, charts, exports a report |

---

## Cần chuẩn bị · What you need

| | |
|---|---|
| ✅ | Máy **DGX Spark** đã bật, có **internet** (chỉ cần khi cài đặt) · The **DGX Spark**, on, with **internet** (for setup only) |
| ✅ | Màn hình, bàn phím, chuột · A screen, keyboard and mouse |
| ✅ | Khoảng **60 GB** trống và **45-90 phút** · About **60 GB** free and **45-90 minutes** |
| ✅ | **Mật khẩu đăng nhập** của máy · The machine's **login password** |

---

## Bước 1 · Đưa thư mục này vào máy Spark
## Step 1 · Put this folder on the Spark

Copy **cả thư mục** (thư mục chứa tệp `START-HERE.md` này) vào thư mục cá nhân trên
máy Spark, đặt tên là `dgx-workshop`. Dùng USB, hoặc nếu người phụ trách hướng dẫn thì
dùng `git clone`.

Copy the **whole folder** (the one containing this `START-HERE.md`) into the home
folder on the Spark and name it `dgx-workshop`. Use a USB stick, or `git clone` if
the organiser showed you how.

---

## Bước 2 · Mở Terminal · Step 2 · Open a Terminal

Nhấn chuột phải vào màn hình nền → **Open in Terminal**, hoặc tìm ứng dụng **Terminal**.
Right-click the desktop → **Open in Terminal**, or search for the **Terminal** app.

---

## Bước 3 · Gõ một lệnh · Step 3 · Type one command

Gõ đúng hai dòng này, mỗi dòng nhấn **Enter**:
Type exactly these two lines, pressing **Enter** after each:

```bash
cd ~/dgx-workshop
bash setup.sh
```

Sau đó:
Then:

1. Chương trình hiện thông báo về phần mềm sẽ được cài. Nhấn **Enter** để đồng ý.
   A notice lists the software it installs. Press **Enter** to agree.
2. Máy hỏi **mật khẩu**: gõ mật khẩu đăng nhập rồi nhấn Enter. **Khi gõ sẽ không
   hiện ký tự nào — đó là bình thường.**
   It asks for your **password**: type your login password and press Enter.
   **Nothing appears while you type — that is normal.**
3. Để máy tự chạy. **Đừng đóng cửa sổ.** Phần lâu nhất là tải mô hình AI.
   Let it run. **Do not close the window.** Downloading the AI models is the slow part.

### ✅ Khi thành công · When it works

Bạn thấy khung màu xanh **SETUP COMPLETE / CÀI ĐẶT HOÀN TẤT**, và trình duyệt tự mở
workshop. Trên màn hình nền có thêm biểu tượng **DGX Spark Workshop**.

You see a green **SETUP COMPLETE** box and the browser opens the workshop. A
**DGX Spark Workshop** icon appears on the desktop.

### ⚠️ Khi có phần cần hỗ trợ · When something needs help

Bạn thấy khung màu vàng và bảng trạng thái của 3 bài. Bài nào có dấu **!** vẫn chạy
được ở chế độ rút gọn; bài có dấu **✘** cần hỗ trợ. Gửi tệp `setup-log.txt` trong thư
mục cho người phụ trách. **Chạy lại `bash setup.sh` hoàn toàn an toàn** — các bước đã
xong sẽ được bỏ qua.

You see a yellow box and a status line for each lab. A lab marked **!** still works
in a reduced mode; **✘** needs help. Send `setup-log.txt` from the folder to the
organiser. **Running `bash setup.sh` again is completely safe** — finished steps
are skipped.

---

## Những lần sau · Next time

Bấm đúp biểu tượng **DGX Spark Workshop** trên màn hình nền, hoặc:
Double-click **DGX Spark Workshop** on the desktop, or:

```bash
cd ~/dgx-workshop
bash start.sh
```

Trình duyệt mở `http://127.0.0.1:8090/`. **Giữ cửa sổ Terminal mở** khi trình diễn.
Nhấn **Ctrl-C** để dừng.
The browser opens `http://127.0.0.1:8090/`. **Keep the Terminal window open** while
presenting. Press **Ctrl-C** to stop.

> 💡 Trước khi khán giả vào, hãy bấm thử một câu hỏi ở mỗi bài để máy "khởi động".
> 💡 Before the audience arrives, click one question in each lab to warm things up.

---

## Kịch bản trình diễn · Demo script (≈ 15 phút · minutes)

Góc trên bên phải có nút **VI / EN** để đổi ngôn ngữ. Các tab ở đầu trang: **Tổng quan,
1 · Tinh chỉnh, 2 · RAG, 3 · Agent**.
The **VI / EN** buttons top right switch language. Tabs along the top: **Overview,
1 · Fine-tuning, 2 · RAG, 3 · Agent**.

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
2. Bấm câu màu cam **"Sau khi ngắt cầu dao DC, phải chờ bao lâu…"** → **12 phút** theo
   SB-2025-01, và nói rõ quy tắc 5 phút cũ đã hết hiệu lực. **Đây là phần quan trọng
   nhất** — mở danh sách **Nguồn** để cho thấy tài liệu cũ vẫn còn trong thư viện.
3. Bấm **"Giá cổ phiếu của Aurora Grid Systems hôm nay là bao nhiêu?"** → hệ thống
   **từ chối**, vì tài liệu không có. Nó không bịa.

### Bài 3 · Agent (5 phút)

1. Bấm câu màu cam **"Phân tích doanh số theo vùng và cho biết khu vực nào tăng trưởng
   tốt nhất."** — đúng câu trong slide.
2. Chỉ vào bốn ô **Người dùng → NeMo Claw → Python → Kết quả** đang sáng lên, và danh sách
   **Agent đang làm gì**: đọc file Excel → phân tích bằng pandas → vẽ biểu đồ → xuất Excel.
3. Kết quả: **Đà Nẵng tăng trưởng tốt nhất, +64,5%**; TP. Hồ Chí Minh lớn nhất nhưng tăng
   chậm hơn; Hà Nội giảm. Bấm **Tải báo cáo Excel** để mở báo cáo.
4. Câu cần nói: *"Mô hình chỉ quyết định gọi công cụ nào. Mọi con số đều do Python tính."*

---

## Nếu có trục trặc · If something breaks

| Hiện tượng · Symptom | Cách xử lý · What to do |
|---|---|
| Trình duyệt không tự mở · Browser does not open | Mở thủ công · Open `http://127.0.0.1:8090/` |
| `Permission denied` | Dùng `bash setup.sh` / `bash start.sh` (có chữ `bash` ở đầu) |
| Trang trắng · Blank page | Nhấn `F5` · Press `F5` |
| Câu trả lời đầu tiên rất chậm · First answer is slow | Bình thường, mô hình đang nạp · Normal: the model is loading |
| Góc trên có chấm xám · Grey dot at the top | Đóng Terminal, chạy lại `bash start.sh` · Close the Terminal, run `bash start.sh` again |
| Bài 3 ghi "Chế độ trực tiếp" · Lab 3 says "Direct mode" | Vẫn trình diễn được; báo người phụ trách sau · Still works; tell the organiser afterwards |
| Vẫn không được · Still stuck | Chạy lại `bash setup.sh`, gửi `setup-log.txt` · Re-run `bash setup.sh`, send `setup-log.txt` |

---

## Ghi chú cho người phụ trách kỹ thuật · Note for the technical organiser

Xem [README.md](README.md): kiến trúc, các bước của `setup.sh`, cấu hình trong
`workshop.env`, và phần **đã kiểm chứng / chưa kiểm chứng**.
See [README.md](README.md) for the architecture, what `setup.sh` does, the
settings in `workshop.env`, and what is verified versus not yet verified.
