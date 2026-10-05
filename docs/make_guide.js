// Builds docs/Huong-dan-Workshop-AI-DGX-Spark.docx: a simple Vietnamese guide for a
// non-technical presenter.
//   npm install --prefix /tmp/guide docx@9 && NODE_PATH=/tmp/guide/node_modules \
//     node docs/make_guide.js docs/Huong-dan-Workshop-AI-DGX-Spark.docx
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow,
  TableCell, WidthType, ShadingType, BorderStyle, LevelFormat, Footer, PageNumber,
  VerticalAlign,
} = require("docx");

const OUT = process.argv[2] || "Huong-dan-Workshop-AI-DGX-Spark.docx";
const W = 9026;                 // A4 width 11906 − 2 × 1440 margins (DXA)
const GREEN = "3F6212", DARK = "1F2937", GRAY = "4B5563";
const FONT = "Arial", MONO = "Consolas";

// ---------------------------------------------------------------- helpers ---
// Inline text: a string, or an array of strings and {b: "..."} / {i: "..."} / {c: "..."}.
function runs(content, base = {}) {
  const parts = Array.isArray(content) ? content : [content];
  return parts.map(p => {
    if (typeof p === "string") return new TextRun({ text: p, ...base });
    if (p.b) return new TextRun({ text: p.b, bold: true, ...base });
    if (p.i) return new TextRun({ text: p.i, italics: true, ...base });
    if (p.c) return new TextRun({ text: p.c, font: MONO, size: 20, ...base });
    return new TextRun({ text: "", ...base });
  });
}
const P = (content, opts = {}) => new Paragraph({ children: runs(content), spacing: { after: 120 }, ...opts });
const H1 = t => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = t => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const H3 = t => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const bullets = items => items.map(it => new Paragraph({
  numbering: { reference: "bullets", level: 0 }, spacing: { after: 80 }, children: runs(it) }));

let listNo = 0;
const numberingConfigs = [{
  reference: "bullets",
  levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
             style: { paragraph: { indent: { left: 540, hanging: 270 } } } }],
}];
// Each numbered list gets its own reference so it restarts at 1.
function steps(items) {
  const ref = `steps-${++listNo}`;
  numberingConfigs.push({
    reference: ref,
    levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
               style: { paragraph: { indent: { left: 540, hanging: 360 } } } }],
  });
  return items.map(it => new Paragraph({ numbering: { reference: ref, level: 0 },
                                         spacing: { after: 100 }, children: runs(it) }));
}

const thin = (color = "D1D5DB") => ({ style: BorderStyle.SINGLE, size: 4, color });
const allBorders = color => ({ top: thin(color), bottom: thin(color), left: thin(color), right: thin(color) });

// A command to type: monospace, shaded, bordered, one line per command.
function cmd(text) {
  return new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: [W],
    rows: [new TableRow({ children: [new TableCell({
      width: { size: W, type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, color: "auto", fill: "F3F4F6" },
      borders: allBorders("C7CCD4"),
      margins: { top: 120, bottom: 120, left: 180, right: 180 },
      children: [new Paragraph({ children: [new TextRun({ text, font: MONO, size: 21, color: "111827" })] })],
    })] })],
  });
}

// A coloured note box. kind: "tip" | "warn" | "info"
function callout(kind, title, content) {
  const theme = {
    tip:  { fill: "EEF7E4", edge: "76B900" },
    warn: { fill: "FEF3E2", edge: "E0A95F" },
    info: { fill: "EEF3FB", edge: "6B8FD6" },
  }[kind];
  const paras = (Array.isArray(content) && content.length && Array.isArray(content[0]) ? content : [content])
    .map((c, i) => new Paragraph({ spacing: { after: 60 },
      children: i === 0 && title ? [new TextRun({ text: title + "  ", bold: true, color: DARK }), ...runs(c)] : runs(c) }));
  return new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: [W],
    rows: [new TableRow({ children: [new TableCell({
      width: { size: W, type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, color: "auto", fill: theme.fill },
      borders: { top: thin(theme.fill), bottom: thin(theme.fill), right: thin(theme.fill),
                 left: { style: BorderStyle.SINGLE, size: 24, color: theme.edge } },
      margins: { top: 120, bottom: 100, left: 200, right: 160 },
      children: paras,
    })] })],
  });
}

// A table with a shaded header row. widths must sum to W.
function table(headers, rows, widths) {
  const cell = (content, i, header) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA },
    shading: header ? { type: ShadingType.CLEAR, color: "auto", fill: "E5EEDB" } : undefined,
    borders: allBorders("CBD5E1"),
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 90, bottom: 90, left: 120, right: 120 },
    children: [new Paragraph({ children: runs(content, header ? { bold: true, color: DARK } : {}) })],
  });
  return new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, i, true)) }),
      ...rows.map(r => new TableRow({ children: r.map((c, i) => cell(c, i, false)) })),
    ],
  });
}
const gap = (after = 120) => new Paragraph({ spacing: { after }, children: [] });

// ---------------------------------------------------------------- content ---
const INSTALL = "curl -fsSL https://raw.githubusercontent.com/an6122003/nemoclaw-rag-demo/main/install.sh | bash";
const children = [
  new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "HƯỚNG DẪN NHANH", bold: true, size: 22, color: GREEN })] }),
  new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: "Workshop AI trên máy NVIDIA DGX Spark", bold: true, size: 44, color: DARK })] }),
  new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "Dành cho người không chuyên kỹ thuật · Cài một lần, trình diễn nhiều lần", size: 24, color: GRAY })] }),
  new Paragraph({
    spacing: { after: 280 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: "76B900", space: 6 } },
    children: [new TextRun({ text: "Cập nhật ngày 06/10/2026 (bản 2)", size: 18, color: GRAY })],
  }),

  callout("tip", "TÓM TẮT TRONG 30 GIÂY", [
    [{ b: "Lần đầu (cài đặt, khoảng 1–1,5 giờ): " }, "mở Terminal → dán 1 lệnh duy nhất → nhấn Enter, nhập mật khẩu → chờ máy tự chạy."],
    [{ b: "Những lần sau: " }, "bấm đúp biểu tượng “DGX Spark Workshop” trên màn hình nền."],
    [{ b: "Khi có lỗi: " }, "gửi tệp setup-log.txt cho người phụ trách kỹ thuật."],
  ]),
  gap(200),

  // ----------------------------------------------------------------- 1 ---
  H1("1. Workshop này là gì?"),
  P("Đây là một chương trình trình diễn AI gồm 3 bài thực hành. Mọi thứ chạy ngay trên máy NVIDIA DGX Spark: mô hình AI, tài liệu và dữ liệu đều nằm trong máy, không gửi lên internet. Khán giả xem trên một trang web duy nhất, có nút chuyển tiếng Việt / tiếng Anh."),
  table(["Bài", "Nội dung", "Khán giả sẽ thấy"], [
    [{ b: "1 · Tinh chỉnh mô hình" }, "Dạy một mô hình AI nhỏ trở thành “Aurora”, trợ lý của công ty mẫu Aurora Grid", "Câu trả lời trước và sau khi dạy, đặt cạnh nhau"],
    [{ b: "2 · Hỏi đáp trên tài liệu (RAG)" }, "AI đọc 28 tài liệu kỹ thuật để trả lời câu hỏi", "Câu trả lời kèm đúng đoạn tài liệu gốc"],
    [{ b: "3 · Agent phân tích dữ liệu" }, "Hỏi bằng tiếng Việt; AI tự đọc file Excel, phân tích, vẽ biểu đồ và xuất báo cáo", "Từng bước AI làm hiện ra trực tiếp trên màn hình"],
  ], [2500, 3700, 2826]),
  gap(60),
  P([{ i: "Aurora Grid là công ty hư cấu; mọi tài liệu và số liệu trong workshop đều là dữ liệu mẫu." }], { spacing: { after: 200 } }),

  // ----------------------------------------------------------------- 2 ---
  H1("2. Cần chuẩn bị gì?"),
  ...bullets([
    ["Máy ", { b: "DGX Spark" }, " đã bật và có ", { b: "internet" }, " (chỉ cần khi cài đặt lần đầu)."],
    "Màn hình, bàn phím và chuột cắm vào máy Spark.",
    ["Mật khẩu đăng nhập", " của máy."],
    ["Khoảng ", { b: "60 GB" }, " dung lượng trống."],
    ["Khoảng ", { b: "1–1,5 giờ" }, " cho lần cài đặt đầu tiên. Máy tự chạy, không cần ngồi canh."],
  ]),

  // ----------------------------------------------------------------- 3 ---
  H1("3. Phần A — Cài đặt lần đầu (chỉ làm một lần)"),
  callout("warn", "LƯU Ý", "Nên cài đặt trước buổi workshop ít nhất 1 ngày, để còn thời gian xử lý nếu có lỗi."),
  gap(160),

  H3("Bước 1 · Mở Terminal"),
  ...bullets([
    ["Nhấn tổ hợp phím ", { b: "Ctrl + Alt + T" }, ". Một cửa sổ nền tối hiện ra: đó là Terminal, nơi gõ lệnh cho máy."],
    ["Hoặc: bấm biểu tượng lưới ", { i: "(Show Applications)" }, " ở góc màn hình, gõ chữ ", { b: "Terminal" }, " rồi bấm vào."],
  ]),
  callout("tip", "MẸO DÁN LỆNH", ["Sao chép lệnh trong tài liệu này như bình thường, nhưng khi dán vào Terminal phải nhấn ", { b: "Ctrl + Shift + V" }, " (không phải Ctrl + V), hoặc bấm chuột phải rồi chọn ", { b: "Paste" }, ". Sau khi dán, nhấn ", { b: "Enter" }, " để chạy."]),
  gap(160),

  H3("Bước 2 · Dán một lệnh duy nhất"),
  P("Dán lệnh sau vào Terminal rồi nhấn Enter:"),
  cmd(INSTALL),
  gap(80),
  P(["Lệnh này tự làm tất cả: tải chương trình về thư mục ", { b: "dgx-workshop" }, ", cài đặt mọi thứ, kiểm tra cả 3 bài thực hành, rồi mở workshop trên trình duyệt."]),

  H3("Bước 3 · Làm theo hướng dẫn trên màn hình"),
  ...steps([
    ["Màn hình hiện thông báo về các phần mềm sẽ được cài. Nhấn ", { b: "Enter" }, " để đồng ý."],
    ["Máy hỏi ", { b: "mật khẩu" }, ": gõ mật khẩu đăng nhập rồi nhấn Enter. ", { b: "Khi gõ, màn hình không hiện ký tự nào" }, " — đó là bình thường."],
    ["Chờ khoảng ", { b: "45–90 phút" }, ". Máy tự tải khoảng 60 GB (mô hình AI và phần mềm). ", { b: "Không đóng cửa sổ Terminal, không tắt máy." }],
  ]),
  callout("info", "TRONG LÚC CHỜ", "Màn hình lần lượt hiện “Step 1”, “Step 2”… với dấu ✔ (đã xong), ! (cảnh báo nhẹ) hoặc ✘ (lỗi). Chỉ cần để máy tự chạy."),
  gap(160),

  H3("Bước 4 · Đọc kết quả"),
  table(["Màn hình hiện", "Nghĩa là", "Cần làm"], [
    [{ b: "Khung xanh “SETUP COMPLETE / CÀI ĐẶT HOÀN TẤT”" }, "Cài đặt xong, cả 3 bài sẵn sàng", "Trình duyệt tự mở workshop. Xong!"],
    [["Một bài ghi ", { b: "“! chạy được, rút gọn”" }], "Bài đó vẫn trình diễn được, ở chế độ rút gọn", "Dùng bình thường; báo người phụ trách khi tiện"],
    [["Khung vàng “ĐÃ CÀI XONG — MỘT SỐ PHẦN CẦN HỖ TRỢ”, bài có dấu ", { b: "✘" }], "Bài đó cần sửa", ["Gửi tệp ", { b: "setup-log.txt" }, " (trong thư mục dgx-workshop) cho người phụ trách"]],
  ], [3300, 2700, 3026]),
  gap(80),
  P([{ b: "Chạy lại đúng lệnh ở Bước 2 lúc nào cũng an toàn:" }, " máy sẽ tự cập nhật bản mới nhất và bỏ qua các bước đã xong."], { spacing: { after: 200 } }),

  // ----------------------------------------------------------------- 4 ---
  H1("4. Phần B — Mỗi lần trình diễn"),
  H3("Mở workshop"),
  ...bullets([
    ["Bấm đúp biểu tượng ", { b: "DGX Spark Workshop" }, " trên màn hình nền. Nếu bấm đúp không chạy: bấm chuột phải vào biểu tượng → chọn ", { b: "Allow Launching" }, ", rồi bấm đúp lại."],
    "Hoặc mở Terminal và dán lệnh:",
  ]),
  cmd("bash ~/dgx-workshop/start.sh"),
  gap(80),
  ...bullets([
    ["Trình duyệt tự mở trang workshop. Nếu không, mở trình duyệt và vào địa chỉ ", { b: "http://127.0.0.1:8090" }, "."],
    ["Nếu máy vừa bật lên hoặc vừa khởi động lại, lần mở đầu tiên mất ", { b: "1–5 phút" }, " để NemoClaw khởi động. Cứ chờ, không cần làm gì."],
    ["Giữ cửa sổ Terminal mở suốt buổi trình diễn ", { i: "(có thể thu nhỏ xuống)" }, "."],
  ]),
  H3("Trước khi khán giả vào (khoảng 10 phút)"),
  ...bullets([
    ["Bấm thử một câu hỏi mẫu ở mỗi bài để máy “khởi động”. ", { b: "Câu đầu tiên luôn chậm hơn." }],
    ["Chọn ngôn ngữ bằng nút ", { b: "VI / EN" }, " ở góc trên bên phải."],
  ]),
  H3("Trên màn hình có gì"),
  table(["Thành phần", "Ý nghĩa"], [
    [{ b: "Các tab ở đầu trang" }, "Tổng quan · 1 · Tinh chỉnh · 2 · RAG · 3 · Agent"],
    [{ b: "Nút VI / EN" }, "Đổi ngôn ngữ cho toàn bộ trang"],
    [{ b: "Các chấm tròn ở góc trên" }, "Xanh = sẵn sàng. Xám hoặc vàng = chưa sẵn sàng, nhưng vẫn trình diễn được"],
  ], [3000, 6026]),
  H3("Kết thúc"),
  P(["Nhấn ", { b: "Ctrl + C" }, " trong cửa sổ Terminal, hoặc đóng cửa sổ Terminal."], { spacing: { after: 200 } }),

  // ----------------------------------------------------------------- 5 ---
  H1("5. Phần C — Kịch bản trình diễn gợi ý (khoảng 15 phút)"),
  H2("Bài 1 — Tinh chỉnh mô hình (5 phút)"),
  ...steps([
    ["Mở tab ", { b: "1 · Tinh chỉnh" }, ". Giới thiệu: 86 ví dụ sẽ dạy mô hình trở thành trợ lý Aurora."],
    ["(Tuỳ chọn) Bấm ", { b: "Bắt đầu tinh chỉnh" }, " và cho khán giả xem đường “loss” đi xuống trong vài phút. Có thể bỏ qua bước này: mô hình đã được dạy sẵn khi cài đặt."],
    ["Ở phần ", { b: "Trước và sau khi tinh chỉnh" }, ", bấm câu “Bạn là trợ lý của công ty nào, và bạn giúp được gì?”. Trước: mô hình tự nhận là Qwen của Alibaba. Sau: “Tôi là Aurora, trợ lý kỹ thuật của Aurora Grid…”."],
    ["Bấm câu “Kể cho tôi nghe một câu chuyện cười đi.”: mô hình mới lịch sự từ chối vì ngoài phạm vi hỗ trợ."],
  ]),
  callout("tip", "CÂU NÊN NÓI", "“Chỉ vài phút trên chính máy này, mô hình đã có danh tính và phạm vi mới, mà không gửi dữ liệu đi đâu.”"),
  gap(160),

  H2("Bài 2 — Hỏi đáp trên tài liệu (4 phút)"),
  ...steps([
    ["Mở tab ", { b: "2 · RAG" }, ". Bấm câu “Tôi phải siết đầu cực DC với lực bao nhiêu?”. Kết quả: 25 N·m cho AX-400 và 35 N·m cho AX-600. AI phân biệt đúng hai sản phẩm gần giống nhau."],
    ["Bấm câu màu cam “Sau khi ngắt cầu dao DC, phải chờ bao lâu trước khi tháo nắp module?”. Kết quả: ", { b: "12 phút" }, ", và AI nói rõ quy định cũ 5 phút đã hết hiệu lực. Mở mục ", { b: "Nguồn của câu trả lời" }, " để khán giả thấy đoạn tài liệu gốc."],
    ["Bấm câu “Giá cổ phiếu của Aurora Grid Systems hôm nay là bao nhiêu?”. AI từ chối trả lời vì tài liệu không có thông tin này: nó không bịa."],
  ]),
  callout("tip", "CÂU NÊN NÓI", "“AI chỉ trả lời từ tài liệu của mình, và luôn chỉ ra nguồn để chúng ta tự kiểm chứng.”"),
  gap(160),

  H2("Bài 3 — Agent phân tích dữ liệu (5 phút)"),
  ...steps([
    ["Mở tab ", { b: "3 · Agent" }, ". Bấm câu màu cam “Phân tích doanh số theo vùng và cho biết khu vực nào tăng trưởng tốt nhất.”"],
    ["Chỉ vào 4 ô ", { b: "Người dùng → NeMo Claw → Python → Kết quả" }, " đang sáng lần lượt, và danh sách “Agent đang làm gì”: đọc file Excel → phân tích → vẽ biểu đồ → xuất báo cáo."],
    ["Kết quả: ", { b: "Đà Nẵng tăng trưởng tốt nhất (+64,5%)" }, "; TP. Hồ Chí Minh lớn nhất nhưng tăng chậm hơn; Hà Nội giảm. Bấm ", { b: "Tải báo cáo Excel" }, " để mở báo cáo vừa tạo."],
  ]),
  callout("tip", "CÂU NÊN NÓI", "“AI quyết định cần làm gì; còn mọi con số đều do máy tính toán, nên không có chuyện bịa số.”"),
  gap(100),
  callout("info", "NẾU THẤY DÒNG “📋 Kiểm tra quy trình”", "Đó là ứng dụng nhắc agent làm đủ các bước (biểu đồ, báo cáo) trước khi trả lời. Đây là chuyện bình thường, và là một điểm hay để giới thiệu: agent được đặt trong một quy trình có kiểm soát."),
  gap(200),

  // ----------------------------------------------------------------- 6 ---
  H1("6. Phần D — Khi gặp sự cố"),
  table(["Hiện tượng", "Cách xử lý"], [
    ["Trình duyệt không tự mở", ["Mở trình duyệt, vào ", { b: "http://127.0.0.1:8090" }]],
    ["Terminal báo “curl: command not found”", ["Dán lệnh ", { b: "sudo apt install -y curl" }, ", nhấn Enter, nhập mật khẩu, rồi dán lại lệnh cài đặt"]],
    ["Terminal báo “Permission denied”", ["Nhớ có chữ ", { b: "bash" }, " ở đầu lệnh: bash ~/dgx-workshop/start.sh"]],
    ["Trang web trắng hoặc không phản hồi", ["Nhấn ", { b: "F5" }, " để tải lại trang"]],
    ["Câu trả lời đầu tiên rất chậm", "Bình thường: mô hình đang được nạp. Chờ 30–60 giây"],
    ["Bài 2 hoặc 3 ghi “chế độ trực tiếp”", ["Vẫn trình diễn được. Để sửa (khoảng 15 phút): đóng cửa sổ Terminal của workshop, rồi chạy lại ", { b: "lệnh cài đặt ở Phần A, Bước 2" }]],
    ["Lỡ đóng cửa sổ Terminal", "Mở lại workshop bằng biểu tượng trên màn hình nền"],
    ["Vẫn không được", ["Chạy lại lệnh cài đặt ở Phần A, Bước 2, rồi gửi tệp ", { b: "setup-log.txt" }, " (trong thư mục dgx-workshop) cho người phụ trách"]],
  ], [3600, 5426]),
  gap(200),

  // ----------------------------------------------------------------- 7 ---
  H1("7. Phần E — Giải thích thuật ngữ"),
  table(["Thuật ngữ", "Hiểu đơn giản"], [
    [{ b: "DGX Spark" }, "Máy tính AI nhỏ gọn của NVIDIA, đủ mạnh để chạy mô hình AI ngay trên bàn làm việc."],
    [{ b: "Mô hình AI (LLM)" }, "“Bộ não” hiểu và viết ngôn ngữ, giống ChatGPT, nhưng chạy ngay trên máy này."],
    [{ b: "Ollama" }, "Phần mềm “phục vụ” các mô hình AI trên máy, để các bài thực hành gọi tới."],
    [{ b: "NemoClaw" }, "Bộ công cụ của NVIDIA để chạy agent AI an toàn. Agent được đặt trong một “sandbox”: một căn phòng kín, chỉ làm được những việc được cho phép."],
    [{ b: "Tinh chỉnh (Fine-tuning)" }, "Dạy thêm cho mô hình có sẵn bằng ví dụ để nó đổi cách cư xử. LoRA là cách tinh chỉnh nhanh: chỉ học thêm một phần rất nhỏ."],
    [{ b: "RAG" }, "Cho AI tra cứu tài liệu trước khi trả lời, để câu trả lời đúng theo tài liệu và có nguồn."],
    [{ b: "Agent" }, "AI không chỉ trả lời mà còn tự quyết định dùng công cụ nào (đọc Excel, tính toán, vẽ biểu đồ) để hoàn thành việc được giao."],
  ], [2600, 6426]),
  gap(200),

  // ----------------------------------------------------------------- 8 ---
  H1("8. Phụ lục — Trình chiếu từ laptop (cho người có kinh nghiệm)"),
  P("Cách 1 — đường hầm SSH. Chạy lệnh này trên laptop, rồi mở http://localhost:8090 trên laptop:"),
  cmd("ssh -L 8090:127.0.0.1:8090 <tên-đăng-nhập>@<địa-chỉ-IP-máy-Spark>"),
  gap(120),
  P("Cách 2 — mở cho cả mạng nội bộ. Chạy lệnh này trên máy Spark, rồi các laptop cùng mạng mở http://<địa-chỉ-IP-máy-Spark>:8090:"),
  cmd("bash ~/dgx-workshop/start.sh --lan"),
];

// ------------------------------------------------------------------ build ---
const doc = new Document({
  creator: "DGX Spark AI Workshop",
  title: "Hướng dẫn nhanh: Workshop AI trên DGX Spark",
  styles: {
    default: { document: { run: { font: FONT, size: 22, color: "1F2937" }, paragraph: { spacing: { line: 300 } } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 30, bold: true, color: GREEN },
        paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 26, bold: true, color: DARK },
        paragraph: { spacing: { before: 220, after: 100 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 23, bold: true, color: GREEN },
        paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: { config: numberingConfigs },
  sections: [{
    properties: { page: { margin: { top: 1300, bottom: 1300, left: 1440, right: 1440 } } },
    footers: {
      default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
        new TextRun({ text: "Hướng dẫn Workshop AI trên DGX Spark · Trang ", size: 17, color: GRAY }),
        new TextRun({ children: [PageNumber.CURRENT], size: 17, color: GRAY }),
        new TextRun({ text: " / ", size: 17, color: GRAY }),
        new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 17, color: GRAY }),
      ] })] }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUT, buf);
  console.log(`wrote ${OUT} (${buf.length} bytes)`);
});
