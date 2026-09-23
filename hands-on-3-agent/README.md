# Hands-on 3 — Build an Agentic Workflow

**Bài 3 — Xây dựng quy trình Agent: Sales Data Analyst** · [English below](#english)

> *"Hỏi dữ liệu bằng tiếng Việt, AI tự đọc file Excel, phân tích và xuất biểu đồ."*

```
 Người dùng            NeMo Claw                  Python                         Kết quả
 "Phân tích      ──▶   Suy luận             ──▶   pandas · matplotlib    ──▶     Biểu đồ
  doanh số"            Gọi công cụ                · openpyxl (Excel)             Nhận định
                       (agent trong sandbox)      (4 công cụ)                    Báo cáo .xlsx
```

## Tiếng Việt

### Chuyện gì xảy ra khi bạn bấm "Phân tích"

1. Câu hỏi được gửi tới agent **`openclaw/analyst`** chạy **bên trong sandbox
   NemoClaw** (OpenShell + OpenClaw), cùng với mô tả của 4 công cụ.
2. Agent **suy luận** và trả về một **lệnh gọi công cụ** có cấu trúc, ví dụ
   `analyze_sales(group_by="Khu vực", metric="Doanh thu (triệu VND)")`.
3. Ứng dụng workshop **chạy công cụ đó bằng Python** (pandas, matplotlib,
   openpyxl) và gửi kết quả lại cho agent.
4. Lặp lại cho đến khi agent đủ dữ kiện để viết **nhận định**.

Trên màn hình, bốn ô "Người dùng → NeMo Claw → Python → Kết quả" sáng lên theo
từng bước thật, và mỗi lệnh gọi công cụ hiện ra kèm tham số và kết quả.

### Bốn công cụ (`tools/sales_tools.py`)

| Công cụ | Làm gì |
|---|---|
| `get_dataset_info` | Mở file Excel: các sheet, các cột, kiểu dữ liệu, khoảng thời gian |
| `analyze_sales` | pandas: tổng theo nhóm cho từng năm, tăng trưởng, tỷ trọng, xếp hạng, và các điểm nổi bật đã tính sẵn |
| `create_chart` | matplotlib: biểu đồ cột, đường hoặc tròn, lưu PNG |
| `export_excel_report` | openpyxl: báo cáo .xlsx gồm Tóm tắt (nhận định của agent), Phân tích (bảng + biểu đồ Excel), Biểu đồ, Dữ liệu |

**Nguyên tắc thiết kế quan trọng nhất:** mô hình *chọn* công cụ và tham số, còn
Python *tính toán*. Công cụ trả về số đã tính và định dạng sẵn ("184,5 tỷ đồng",
"+64,5%"), nên mô hình không phải làm phép tính nào — đây là cách tránh "bịa số".

### Dữ liệu (`data/aurora_sales_2024_2025.xlsx`)

Sổ doanh số của Aurora Grid Việt Nam năm 2024-2025: 1.149 dòng, 12 cột
(Ngày, Năm, Quý, Tháng, Khu vực, Sản phẩm, Nhóm sản phẩm, Kênh bán, Số lượng,
Doanh thu, Giá vốn, Lợi nhuận gộp — đơn vị triệu VND). Dữ liệu được tạo có chủ đích
bằng `data/make_dataset.py`, với vài "bẫy" để thấy agent phân tích có cẩn thận không:

- Khu vực **lớn nhất** (TP. Hồ Chí Minh) không phải khu vực **tăng trưởng nhanh nhất**
  (Đà Nẵng).
- "Bán chạy nhất" phụ thuộc vào chỉ tiêu: theo **số lượng** là pin gia đình Aurora
  Home 10, theo **doanh thu** là tủ pin AX-600.
- Doanh thu tủ pin **AX-400 giảm mạnh từ quý 2/2025** — đúng tháng ban hành bản tin
  an toàn SB-2025-04 về giảm công suất AX-400 trong tài liệu của Bài 2.

### Đáp án (để người trình bày đối chiếu)

| Câu hỏi | Đáp án đúng |
|---|---|
| Khu vực nào tăng trưởng tốt nhất? | **Đà Nẵng +64,5%** (112,2 → 184,5 tỷ đồng) |
| Khu vực nào lớn nhất năm 2025? | TP. Hồ Chí Minh, 551,3 tỷ đồng (40,9% tổng), +16,2% |
| Khu vực nào giảm? | Hà Nội −6,8% (365,5 → 340,8 tỷ đồng) |
| Tổng doanh thu | 2024: 1.173,9 tỷ · 2025: 1.347,7 tỷ (**+14,8%**) |
| Bán chạy nhất 2025 (số lượng) | Pin gia đình Aurora Home 10: 2.444 đơn vị (63,2%) |
| Doanh thu cao nhất 2025 (sản phẩm) | Tủ pin AX-600: 561,7 tỷ đồng (+42,5%) |
| AX-400 theo quý | Q1 −12,5% · Q2 −35,8% · Q3 −46,4% · Q4 −41,0% (cả năm −35,5%) |
| Tháng cao nhất / thấp nhất 2025 | Tháng 12: 154,9 tỷ · Tháng 2 (Tết): 57,4 tỷ |
| Kênh tăng nhanh nhất | Đại lý +28,0% (bán trực tiếp vẫn lớn nhất: 630,2 tỷ) |
| Biên lợi nhuận gộp cao nhất | Dịch vụ bảo trì 46,5% (thấp nhất: Helios H3 15,1%) |
| Đà Nẵng: sản phẩm đóng góp nhiều nhất | AX-600 (+38,7 tỷ đồng); tăng nhanh nhất: Aurora Home 10 (+107,5%) |

### Bài tập

1. **Đọc "bộ não" của agent:** `agent/AGENTS.md`. Đây là toàn bộ hướng dẫn của agent.
   Thử sửa một quy tắc (ví dụ: "luôn kết thúc bằng một đề xuất hành động"), rồi hỏi lại.
   Ứng dụng gửi file này cho agent ở mỗi câu hỏi, nên thay đổi có hiệu lực ngay.
2. **Hỏi một câu mơ hồ:** "Sản phẩm nào bán chạy nhất?" — agent chọn số lượng hay
   doanh thu? Nó có nói rõ sự khác biệt không?
3. **Tải lên file Excel của bạn** (nút "Tải lên…"). Công cụ tự nhận diện cột, nên agent
   phải gọi `get_dataset_info` trước để biết cột nào là gì.
4. **Thêm một công cụ mới** vào `tools/sales_tools.py` (ví dụ: dự báo tháng tới bằng
   trung bình trượt): thêm hàm, thêm mô tả vào `TOOL_SPECS`, thêm nhánh trong `run_tool`.
5. **Dùng giao diện gốc của OpenClaw** (nút "Mở giao diện OpenClaw"): agent mặc định
   có skill `sales-analyst` và tự chạy cùng các công cụ này *bên trong* sandbox.

### Vì sao cần sandbox?

Agent `analyst` dùng hồ sơ công cụ **minimal**: không có shell, không đọc/ghi file,
không truy cập web. Thứ duy nhất nó làm được là yêu cầu 4 công cụ ở trên, và ứng dụng
kiểm tra từng yêu cầu trước khi chạy. OpenShell áp chính sách này **từ bên ngoài**
tiến trình của agent, nên một agent bị lừa bởi prompt injection cũng không tự nới
quyền cho mình được.

---

<a id="english"></a>
## English

### What happens when you click "Analyse"

1. The question goes to the OpenClaw agent **`openclaw/analyst`**, running
   **inside the NemoClaw sandbox**, together with the four tool definitions.
2. The agent **reasons** and returns a structured **tool call**.
3. The workshop app **runs the tool in Python** and sends the result back.
4. Repeat until the agent can write the **insight**.

The four boxes on screen light up with the real events, and every tool call is
shown with its arguments and result.

### How the pieces connect

```
 workshop app ──POST /v1/chat/completions (model openclaw/analyst, tools=[4])──▶ OpenClaw gateway
      ▲                                                                         (NemoClaw sandbox)
      │  finish_reason = tool_calls                                                    │
      └──────────────── tool_calls ◀─────────────────────────────────────────────────┘
      │  run pandas / matplotlib / openpyxl, append role:"tool" results, call again …
```

This is the gateway's documented **client-tool contract**: OpenClaw hands each
tool call back to the caller and continues the same reasoning loop when the
results come back. `../scripts/lab3-sandbox-setup.sh` enables the endpoint,
creates the `analyst` agent (minimal tool profile, own workspace with
`AGENTS.md`), and switches off the model's hidden reasoning pass for agent turns
(`reasoning_effort: none`), which cut a tool-call turn from 14.8 s to 2.4 s on
qwen3:8b with the same tool choice.

If the gateway is unreachable, the app runs the **same loop directly against
Ollama** and labels the run "direct mode", so the demo never stops.

### Verified vs. not yet verified

- **Verified** against the real OpenClaw 2026.7.1 runtime (the build NemoClaw
  pins), run in a plain container with qwen3:8b: the full 4-tool flow completes
  and the agent names Da Nang as the fastest-growing region in Vietnamese
  (≈26 s) and in English. The direct route was verified the same way (≈18 s).
- **Not yet verified on a DGX Spark:** the NemoClaw sandbox wiring
  (`lab3-sandbox-setup.sh`) and the in-sandbox skill. `setup.sh` checks both and
  reports the result; `app/selftest.py --lab3 --route nemoclaw` repeats the check.

### Files

| File | Purpose |
|---|---|
| `agent/AGENTS.md` | the analyst's instructions (sent with every request, and installed in the sandbox) |
| `tools/sales_tools.py` | the four tools, their JSON schemas, and a CLI for the in-sandbox skill |
| `skills/sales-analyst/SKILL.md` | OpenClaw skill so the default agent can run the tools inside the sandbox |
| `data/aurora_sales_2024_2025.xlsx` | the workbook; regenerate with `data/make_dataset.py` |
| `../app/lab3_agent.py` | the agent loop, both routes |
| `.run/lab3/<run>/transcript.json` | every run's full message history, for inspection |

### Checks

```bash
scripts/lab3-sandbox-setup.sh --check                    # gateway serves the agent, a tool call round-trips
.venv/bin/python app/selftest.py --lab3 --route nemoclaw  # the whole slide question, end to end
.venv/bin/python hands-on-3-agent/tools/sales_tools.py analyze_sales \
    --args '{"group_by": "Khu vực", "metric": "doanh thu"}'   # one tool by hand
```
