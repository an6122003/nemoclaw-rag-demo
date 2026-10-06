#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Synthetic Vietnamese VAT invoices (images) for the "invoices into Excel" demo.

    python3 enterprise/generate/invoices.py --out .run/enterprise/invoices --count 1000

Writes inv-0001.jpg … and truth.json (what each invoice really says): a month
of supplier invoices for an accounts-payable team. Every invoice is invented,
addressed to the fictional Aurora Mart, and stamped "MẪU DEMO · SAMPLE" so it
can never pass for a real one. Variation: each supplier has its own template
(three layouts, several fonts), 1-6 lines of goods or services, 8% or 10% VAT,
scan tilt, blur, noise, stamps and paper tone. About one in seven carries a
planted problem (totals that do not add up, a line where quantity x price is
wrong, the wrong VAT, or the same invoice sent twice) for the rule checks to
catch. Rendering runs on all CPU cores: 1,000 invoices take well under a minute
on a DGX Spark.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import multiprocessing
import os
import random
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (COMPANY_ADDRESS, COMPANY_LEGAL, COMPANY_TAX, PRODUCTS, SERVICE_LINES,  # noqa: E402
                    SUPPLIERS, address, amount_in_words, person, phone, tax_code, vnd)

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent / "fonts"
SYSTEM_FONTS = {
    "serif": ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"],
    "serif-bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                   "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"],
    "mono": ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"],
}
W, H = 1240, 1754  # A4 at 150 dpi
BRANDS = {"nova", "frostline", "aquapro", "zenit", "pulse", "coolair", "aster"}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    names = {"regular": "BeVietnamPro-Regular.ttf", "medium": "BeVietnamPro-Medium.ttf",
             "semibold": "BeVietnamPro-SemiBold.ttf", "bold": "BeVietnamPro-Bold.ttf"}
    if kind in names:
        return ImageFont.truetype(str(FONTS / names[kind]), size)
    for path in SYSTEM_FONTS.get(kind, []):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.truetype(str(FONTS / ("BeVietnamPro-Bold.ttf" if "bold" in kind else "BeVietnamPro-Regular.ttf")), size)


# ----------------------------------------------------------------- content ---
def make_invoice(r: random.Random, n: int, sellers: dict) -> dict:
    name, kind = r.choice(SUPPLIERS)
    seller = sellers.setdefault(name, {"name": name, "tax_code": tax_code(r), "address": address(r),
                                       "phone": phone(r), "series": f"1C26T{''.join(r.choice('ABCDEGHKLMNPQRSTUVXY') for _ in range(2))}",
                                       "next": r.randint(120, 4800),
                                       "layout": r.choice(["classic", "modern", "compact"])})
    lines = []
    if kind == "goods":
        brand = {w.lower() for w in name.split()} & BRANDS  # a brand's own distributor sells that brand
        pool = [p for p in PRODUCTS if brand & {w.lower() for w in p[1].split()}] or PRODUCTS
        for _, prod, price in r.sample(pool, min(len(pool), r.randint(1, 6))):
            unit_price = int(price * r.uniform(0.62, 0.8) / 1000) * 1000  # wholesale
            qty = r.choice([1, 2, 3, 5, 6, 8, 10, 12, 15, 20, 24, 30])
            lines.append({"desc": prod, "unit": "cái", "qty": qty, "price": unit_price})
    else:
        catalog = SERVICE_LINES[kind]
        for desc, unit, price in r.sample(catalog, min(len(catalog), r.randint(1, 4))):
            qty = r.choice([100, 200, 300, 500, 1000, 2000]) if price < 100_000 else r.choice([1, 1, 2, 3, 4, 6, 10])
            unit_price = int(price * r.uniform(0.9, 1.15) / 500) * 500 or price
            lines.append({"desc": desc, "unit": unit, "qty": qty, "price": unit_price})
    for ln in lines:
        ln["amount"] = ln["qty"] * ln["price"]
    subtotal = sum(ln["amount"] for ln in lines)
    vat_rate = 8 if kind == "goods" and r.random() < 0.7 else 10
    vat = round(subtotal * vat_rate / 100)
    total = subtotal + vat
    date = dt.date(2026, 9, 1) + dt.timedelta(days=r.randint(0, 34))
    seller["next"] += r.randint(1, 37)
    inv = {
        "id": f"INV-{n:04d}", "file": f"inv-{n:04d}.jpg",
        "seller_name": seller["name"], "seller_tax_code": seller["tax_code"], "seller_address": seller["address"],
        "seller_phone": seller["phone"],
        "buyer_name": COMPANY_LEGAL, "buyer_tax_code": COMPANY_TAX,
        "series": seller["series"], "number": f"{seller['next']:08d}", "date": date.isoformat(),
        "items": lines, "subtotal": subtotal, "vat_rate": vat_rate, "vat": vat, "total": total,
        "payment": r.choice(["Chuyển khoản", "TM/CK", "Chuyển khoản"]),
        "buyer_contact": person(r), "issues": [], "layout": seller["layout"],
    }
    return inv


def plant_problem(r: random.Random, inv: dict) -> None:
    """Make the document itself wrong, as real ones sometimes are."""
    kind = r.choice(["total", "line", "total", "vat"])
    if kind == "total":
        inv["total"] += r.choice([1, -1]) * r.choice([10_000, 100_000, 90_000, 1_000_000])
        inv["issues"].append("total_mismatch")
    elif kind == "line" and inv["items"]:
        ln = r.choice(inv["items"])
        ln["amount"] += r.choice([1, -1]) * ln["price"]
        inv["subtotal"] = sum(x["amount"] for x in inv["items"])
        inv["vat"] = round(inv["subtotal"] * inv["vat_rate"] / 100)
        inv["total"] = inv["subtotal"] + inv["vat"]
        inv["issues"].append("line_mismatch")
    else:
        inv["vat"] = round(inv["subtotal"] * (inv["vat_rate"] + r.choice([-2, 2])) / 100)
        inv["total"] = inv["subtotal"] + inv["vat"]
        inv["issues"].append("vat_mismatch")


# ----------------------------------------------------------------- drawing ---
class Pen:
    def __init__(self, img: Image.Image, ink=(30, 34, 40)):
        self.d = ImageDraw.Draw(img)
        self.ink = ink

    def text(self, xy, s, f, fill=None, anchor="la"):
        self.d.text(xy, s, font=f, fill=fill or self.ink, anchor=anchor)

    def width(self, s, f) -> int:
        return int(self.d.textlength(s, font=f))

    def wrap(self, s: str, f, max_w: int) -> list[str]:
        out, cur = [], ""
        for word in s.split():
            trial = (cur + " " + word).strip()
            if self.width(trial, f) <= max_w:
                cur = trial
            else:
                out.append(cur)
                cur = word
        if cur:
            out.append(cur)
        return out or [""]


def draw_table(p: Pen, inv: dict, top: int, left: int, right: int, f, fb, header_fill=None, zebra=None, grid=(150, 150, 150)):
    cols = [("STT", 60), ("Tên hàng hóa, dịch vụ", 0), ("ĐVT", 110), ("Số lượng", 120), ("Đơn giá", 170), ("Thành tiền", 200)]
    fixed = sum(w for _, w in cols)
    widths = [w or (right - left - fixed) for _, w in cols]
    xs = [left]
    for w in widths:
        xs.append(xs[-1] + w)
    row_h = 46
    if header_fill:
        p.d.rectangle([left, top, right, top + row_h], fill=header_fill)
    for (title, _), x0, x1 in zip(cols, xs, xs[1:]):
        p.text(((x0 + x1) // 2, top + row_h // 2), title, fb, anchor="mm")
    y = top + row_h
    for i, ln in enumerate(inv["items"], 1):
        desc_lines = p.wrap(ln["desc"], f, widths[1] - 20)
        h = max(row_h, 16 + 30 * len(desc_lines))
        if zebra and i % 2 == 0:
            p.d.rectangle([left, y, right, y + h], fill=zebra)
        p.text(((xs[0] + xs[1]) // 2, y + h // 2), str(i), f, anchor="mm")
        for k, dl in enumerate(desc_lines):
            p.text((xs[1] + 10, y + 10 + 30 * k), dl, f)
        p.text(((xs[2] + xs[3]) // 2, y + h // 2), ln["unit"], f, anchor="mm")
        p.text((xs[4] - 12, y + h // 2), vnd(ln["qty"]), f, anchor="rm")
        p.text((xs[5] - 12, y + h // 2), vnd(ln["price"]), f, anchor="rm")
        p.text((xs[6] - 12, y + h // 2), vnd(ln["amount"]), f, anchor="rm")
        y += h
    if grid:
        p.d.rectangle([left, top, right, y], outline=grid, width=2)
        for x in xs[1:-1]:
            p.d.line([x, top, x, y], fill=grid, width=1)
        p.d.line([left, top + row_h, right, top + row_h], fill=grid, width=2)
    return y


def totals_block(p: Pen, inv: dict, y: int, left: int, right: int, f, fb):
    rows = [("Cộng tiền hàng:", vnd(inv["subtotal"])),
            (f"Thuế suất GTGT: {inv['vat_rate']}%      Tiền thuế GTGT:", vnd(inv["vat"])),
            ("Tổng cộng tiền thanh toán:", vnd(inv["total"]))]
    for i, (label, value) in enumerate(rows):
        fnt = fb if i == 2 else f
        p.text((right - 260, y), label, fnt, anchor="ra")
        p.text((right - 12, y), value, fnt, anchor="ra")
        y += 40
    words = p.wrap("Số tiền viết bằng chữ: " + amount_in_words(inv["total"]), f, right - left - 20)
    for wl in words:
        p.text((left + 10, y + 6), wl, f)
        y += 34
    return y + 10


def signatures(p: Pen, inv: dict, y: int, left: int, right: int, f, fb, seller_sig_color=(200, 30, 30)):
    mid = (left + right) // 2
    p.text(((left + mid) // 2, y), "Người mua hàng", fb, anchor="ma")
    p.text(((mid + right) // 2, y), "Người bán hàng", fb, anchor="ma")
    p.text(((left + mid) // 2, y + 36), "(Ký, ghi rõ họ tên)", f, anchor="ma")
    signer = p.wrap("Ký bởi: " + inv["seller_name"], f, right - mid - 112)
    box = [mid + 40, y + 80, right - 40, y + 132 + 32 * (len(signer) + 1)]
    p.d.rectangle(box, outline=seller_sig_color, width=3)
    p.text((box[0] + 16, box[1] + 14), "Signature Valid", f, fill=seller_sig_color)
    for k, line in enumerate(signer):
        p.text((box[0] + 16, box[1] + 48 + 32 * k), line, f, fill=seller_sig_color)
    p.text((box[0] + 16, box[1] + 48 + 32 * len(signer)), "Ký ngày: " + dt.date.fromisoformat(inv["date"]).strftime("%d/%m/%Y"),
           f, fill=seller_sig_color)


def watermark(img: Image.Image) -> Image.Image:
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font("bold", 120)
    d.text((img.width // 2, img.height // 2), "MẪU DEMO · SAMPLE", font=f, fill=(220, 40, 40, 38), anchor="mm")
    layer = layer.rotate(32, resample=Image.BICUBIC, center=(img.width // 2, img.height // 2))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def date_line(inv: dict) -> str:
    d = dt.date.fromisoformat(inv["date"])
    return f"Ngày {d.day:02d} tháng {d.month:02d} năm {d.year}"


def layout_classic(inv: dict, r: random.Random) -> Image.Image:
    img = Image.new("RGB", (W, H), (255, 255, 255))
    p = Pen(img)
    f, fb, fs = font("serif", 24), font("serif-bold", 24), font("serif", 21)
    ftitle = font("serif-bold", 40)
    left, right = 70, W - 70
    p.d.rectangle([40, 40, W - 40, H - 40], outline=(60, 90, 160), width=4)
    p.text((W // 2, 80), "HÓA ĐƠN GIÁ TRỊ GIA TĂNG", ftitle, fill=(170, 20, 20), anchor="ma")
    p.text((W // 2, 132), "(Bản thể hiện của hóa đơn điện tử)", fs, anchor="ma")
    p.text((W // 2, 168), date_line(inv), f, anchor="ma")
    p.text((right, 80), "Mẫu số: 1", f, anchor="ra")
    p.text((right, 116), f"Ký hiệu: {inv['series']}", f, anchor="ra")
    p.text((right, 152), "Số: ", f, anchor="ra")
    p.text((right, 188), inv["number"], font("serif-bold", 30), fill=(170, 20, 20), anchor="ra")
    y = 240
    p.d.line([left, y, right, y], fill=(60, 90, 160), width=2)
    y += 16
    for label, value in [("Đơn vị bán hàng: ", inv["seller_name"]), ("Mã số thuế: ", inv["seller_tax_code"]),
                         ("Địa chỉ: ", inv["seller_address"]), ("Điện thoại: ", inv["seller_phone"])]:
        p.text((left, y), label, fb)
        p.text((left + p.width(label, fb), y), value, f)
        y += 38
    p.d.line([left, y + 4, right, y + 4], fill=(60, 90, 160), width=2)
    y += 20
    for label, value in [("Họ tên người mua hàng: ", inv["buyer_contact"]), ("Tên đơn vị: ", inv["buyer_name"]),
                         ("Mã số thuế: ", inv["buyer_tax_code"]), ("Địa chỉ: ", COMPANY_ADDRESS),
                         ("Hình thức thanh toán: ", inv["payment"])]:
        p.text((left, y), label, fb)
        p.text((left + p.width(label, fb), y), value, f)
        y += 38
    y = draw_table(p, inv, y + 14, left, right, fs, font("serif-bold", 21))
    y = totals_block(p, inv, y + 20, left, right, f, fb)
    signatures(p, inv, y + 20, left, right, fs, fb)
    return img


def layout_modern(inv: dict, r: random.Random) -> Image.Image:
    img = Image.new("RGB", (W, H), (255, 255, 255))
    accent = r.choice([(14, 98, 160), (16, 120, 90), (120, 60, 160), (200, 90, 20)])
    p = Pen(img, ink=(32, 36, 44))
    f, fb, fs = font("regular", 23), font("semibold", 23), font("regular", 20)
    p.d.rectangle([0, 0, W, 210], fill=accent)
    p.d.ellipse([70, 50, 180, 160], fill=(255, 255, 255))
    initials = "".join(w[0] for w in inv["seller_name"].split()[-2:]).upper()
    p.text((125, 105), initials, font("bold", 44), fill=accent, anchor="mm")
    for k, line in enumerate(p.wrap(inv["seller_name"].upper(), font("bold", 28), 620)):
        p.text((210, 62 + 36 * k), line, font("bold", 28), fill=(255, 255, 255))
    p.text((210, 140), f"MST: {inv['seller_tax_code']}", f, fill=(230, 240, 255))
    p.text((W - 70, 62), "HÓA ĐƠN GTGT", font("bold", 34), fill=(255, 255, 255), anchor="ra")
    p.text((W - 70, 110), f"Ký hiệu {inv['series']}  ·  Số {inv['number']}", f, fill=(230, 240, 255), anchor="ra")
    p.text((W - 70, 146), date_line(inv), f, fill=(230, 240, 255), anchor="ra")
    left, right = 70, W - 70
    y = 250
    p.text((left, y), "BÊN BÁN", font("bold", 20), fill=accent)
    p.text((W // 2 + 20, y), "BÊN MUA", font("bold", 20), fill=accent)
    y += 34
    sl = p.wrap(inv["seller_address"], fs, W // 2 - 110)
    bl = [inv["buyer_name"], f"MST: {inv['buyer_tax_code']}"] + p.wrap(COMPANY_ADDRESS, fs, W // 2 - 110) + [f"Người mua: {inv['buyer_contact']}"]
    for k in range(max(len(sl), len(bl))):
        if k < len(sl):
            p.text((left, y + 32 * k), sl[k], fs)
        if k < len(bl):
            p.text((W // 2 + 20, y + 32 * k), bl[k], fs)
    y += 32 * max(len(sl), len(bl)) + 30
    light = tuple(min(255, c + 200) for c in accent)
    y = draw_table(p, inv, y, left, right, fs, font("semibold", 20), header_fill=light, zebra=(246, 248, 251), grid=(205, 210, 220))
    y = totals_block(p, inv, y + 24, left, right, f, fb)
    p.text((left, y), f"Hình thức thanh toán: {inv['payment']}", fs)
    signatures(p, inv, y + 50, left, right, fs, fb, seller_sig_color=accent)
    return img


def layout_compact(inv: dict, r: random.Random) -> Image.Image:
    img = Image.new("RGB", (W, H), (255, 255, 255))
    p = Pen(img, ink=(25, 25, 25))
    f, fb, fs = font("mono", 22), font("bold", 22), font("mono", 20)
    left, right = 90, W - 90
    y = 90
    for line in p.wrap(inv["seller_name"].upper(), font("bold", 30), right - left):
        p.text((W // 2, y), line, font("bold", 30), anchor="ma")
        y += 40
    p.text((W // 2, y), inv["seller_address"], fs, anchor="ma")
    p.text((W // 2, y + 32), f"MST: {inv['seller_tax_code']}", fs, anchor="ma")
    y += 90
    p.text((W // 2, y), "HÓA ĐƠN GIÁ TRỊ GIA TĂNG", font("bold", 34), anchor="ma")
    y += 52
    p.text((left, y), f"Ký hiệu: {inv['series']}", f)
    p.text((right, y), f"Số: {inv['number']}", f, anchor="ra")
    y += 34
    p.text((left, y), date_line(inv), f)
    y += 50
    p.text((left, y), f"Người mua: {inv['buyer_name']}", fs)
    p.text((left, y + 30), f"MST người mua: {inv['buyer_tax_code']}", fs)
    y += 80
    p.d.line([left, y, right, y], fill=(40, 40, 40), width=2)
    y = draw_table(p, inv, y + 10, left, right, fs, font("bold", 19), grid=None)
    p.d.line([left, y + 6, right, y + 6], fill=(40, 40, 40), width=2)
    y = totals_block(p, inv, y + 24, left, right, f, fb)
    p.text((left, y), f"Thanh toán: {inv['payment']}", fs)
    signatures(p, inv, y + 60, left, right, fs, fb)
    return img


LAYOUTS = {"classic": layout_classic, "modern": layout_modern, "compact": layout_compact}


def scan(img: Image.Image, r: random.Random) -> Image.Image:
    """Make the clean render look photographed or scanned."""
    tone = r.choice([(255, 255, 255), (252, 250, 244), (248, 246, 240), (250, 250, 247)])
    paper = Image.new("RGB", img.size, tone)
    img = Image.blend(paper, img, 0.94) if tone != (255, 255, 255) else img
    if r.random() < 0.6:  # an "ĐÃ THANH TOÁN" stamp
        stamp = Image.new("RGBA", (420, 140), (0, 0, 0, 0))
        d = ImageDraw.Draw(stamp)
        col = (190, 30, 40, 150)
        d.rounded_rectangle([4, 4, 416, 136], radius=18, outline=col, width=6)
        d.text((210, 70), r.choice(["ĐÃ THANH TOÁN", "ĐÃ NHẬN HÀNG", "KẾ TOÁN ĐÃ NHẬN"]), font=font("bold", 36), fill=col, anchor="mm")
        stamp = stamp.rotate(r.uniform(-18, 18), expand=True, resample=Image.BICUBIC)
        base = img.convert("RGBA")
        base.alpha_composite(stamp, (r.randint(80, W - 520), r.randint(H - 520, H - 260)))
        img = base.convert("RGB")
    img = watermark(img)
    angle = r.uniform(-1.6, 1.6)
    img = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=tone)
    if r.random() < 0.7:
        img = img.filter(ImageFilter.GaussianBlur(r.uniform(0.3, 0.9)))
    # light speckle noise
    noise = Image.effect_noise(img.size, r.uniform(6, 16)).convert("RGB")
    img = Image.blend(img, noise, r.uniform(0.02, 0.06))
    return img


def render(job: tuple) -> str:
    """Draw and save one invoice (runs in a worker process)."""
    inv, out, seed = job
    r = random.Random(seed)
    img = scan(LAYOUTS[inv["layout"]](inv, r), r)
    img.save(Path(out) / inv["file"], "JPEG", quality=r.randint(72, 88), optimize=True)
    return inv["file"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=".run/enterprise/invoices")
    ap.add_argument("--count", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--workers", type=int, default=0, help="processes (default: all cores, at most 16)")
    args = ap.parse_args()
    r = random.Random(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sellers: dict = {}
    invoices = []
    for n in range(1, args.count + 1):
        if invoices and r.random() < 0.05:  # the same invoice sent twice (a classic double payment)
            src = r.choice(invoices)
            inv = json.loads(json.dumps(src))
            inv.update(id=f"INV-{n:04d}", file=f"inv-{n:04d}.jpg", issues=["duplicate"], duplicate_of=src["id"])
        else:
            inv = make_invoice(r, n, sellers)
            if r.random() < 0.09:
                plant_problem(r, inv)
        invoices.append(inv)
    jobs = [(inv, str(out), args.seed * 1_000_003 + i) for i, inv in enumerate(invoices)]
    workers = args.workers or min(16, os.cpu_count() or 2)
    t0 = time.time()
    if workers > 1:
        with multiprocessing.Pool(workers) as pool:
            for k, _ in enumerate(pool.imap_unordered(render, jobs, chunksize=8), 1):
                if k % 100 == 0:
                    print(f"  {k}/{len(jobs)} rendered", flush=True)
    else:
        for job in jobs:
            render(job)
    (out / "truth.json").write_text(json.dumps(invoices, ensure_ascii=False, indent=1))
    flagged = sum(1 for i in invoices if i["issues"])
    print(f"wrote {len(invoices)} invoices to {out} ({flagged} with a planted problem) "
          f"in {time.time() - t0:.0f} s on {workers} processes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
