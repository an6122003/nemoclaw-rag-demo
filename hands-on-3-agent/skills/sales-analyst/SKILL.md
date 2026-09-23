---
name: sales-analyst
description: Analyse the Aurora Grid sales Excel workbook with pandas, draw matplotlib charts and export Excel reports.
metadata: { "openclaw": { "requires": { "bins": ["python3"] } } }
---

# Sales Analyst — pandas · matplotlib · Excel

Use this skill when the user asks about sales, revenue ("doanh số", "doanh thu"),
profit ("lợi nhuận"), regions ("vùng", "khu vực"), products, channels or trends
in the Aurora Grid sales workbook, or asks for a chart or an Excel report.

Every number in your answer must come from these commands. Never calculate,
estimate or invent a figure yourself.

## How to run a tool

Use the `exec` tool. Every command has the same shape:

```bash
python3 {baseDir}/scripts/sales_tools.py <tool> \
  --data {baseDir}/data/aurora_sales_2024_2025.xlsx \
  --out /sandbox/.openclaw/workspace/outputs \
  --lang vi \
  --args '<JSON arguments>'
```

Use `--lang en` when the user writes in English. The command prints a JSON
result; charts and reports are listed under `files`.

## The four tools

1. `get_dataset_info` with `--args '{}'` — columns, types and time range. Run it first.
2. `analyze_sales` — totals per group for each year, growth, share and highlights:
   `--args '{"group_by": "Khu vực", "metric": "Doanh thu (triệu VND)"}'`
   Optional filter: `"filters": {"Khu vực": "Đà Nẵng"}`.
3. `create_chart` — a PNG chart:
   `--args '{"group_by": "Khu vực", "metric": "Doanh thu (triệu VND)", "chart_type": "bar", "title": "Doanh thu theo khu vực"}'`
   Use `bar` to compare groups, `line` for `Tháng` or `Quý`, `pie` for shares.
4. `export_excel_report` — a formatted .xlsx report:
   `--args '{"title": "Báo cáo doanh số theo khu vực", "group_by": "Khu vực", "metric": "Doanh thu (triệu VND)", "insights": ["...", "..."]}'`

Word meanings: "doanh số"/"doanh thu"/"revenue" → `Doanh thu (triệu VND)`;
"lợi nhuận"/"profit" → `Lợi nhuận gộp (triệu VND)`; "bán chạy"/"units" →
`Số lượng`; "biên lợi nhuận"/"margin" → `margin`; "vùng"/"khu vực" → `Khu vực`.

If a command returns `error`, read `available_columns` or `available_values`
and run it again with a corrected argument.

## Showing the results

Attach every chart and report to your final reply, each on its own line, using
the path printed under `files`:

MEDIA:/sandbox/.openclaw/workspace/outputs/chart-C2.png

Then answer in the user's language: one sentence with the direct answer and its
number, then 2-4 short bullet points quoting the tool's numbers exactly.
