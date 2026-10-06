#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Synthetic customer messages for the "support inbox" demo.

    python3 enterprise/generate/inbox.py --out .run/enterprise/inbox/messages.jsonl --count 2400

Each line is one message to the fictional retailer Aurora Mart (email, Zalo,
Facebook Messenger or the web form) with the answer key the demo scores
against: category, urgency, sentiment, flags and order number, labelled by the
same triage policy the model is given. Variation comes from per-category
templates, tone (calm, upset, angry), writing style (formal email, chat
shorthand, no diacritics, typos, a little English), threats, emoji and
personal data (phones, emails) that the demo masks before showing anything.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PRODUCTS, address, order_id, person, phone, strip_accents, vnd  # noqa: E402

CATEGORIES = ["delivery", "defect", "wrong_item", "return_refund", "billing", "warranty", "account",
              "inquiry", "praise", "spam"]
WEIGHTS = [20, 14, 8, 13, 9, 10, 6, 12, 5, 3]
# Categories that never need a person to fix something.
LOW = {"inquiry", "praise", "spam"}

GREET_FORMAL = ["Kính gửi Aurora Mart,", "Kính gửi bộ phận chăm sóc khách hàng,", "Chào Aurora Mart,", "Dear Aurora Mart team,"]
GREET_CHAT = ["shop ơi", "Chào shop", "Alo shop", "Ad ơi", "Shop ơi cho em hỏi", "", "", "hi shop"]
CLOSE_FORMAL = ["Trân trọng,", "Cảm ơn quý công ty.", "Mong sớm nhận được phản hồi.", "Xin cảm ơn,"]
CLOSE_CHAT = ["Cảm ơn shop", "mong shop phản hồi sớm", "thanks shop", "", "", "ạ"]
UPSET = ["Hơi thất vọng.", "Mong lần sau shop làm tốt hơn.", "Mình chờ lâu quá rồi.", "Không vui lắm."]
ANGRY = ["Quá thất vọng!!!", "Làm ăn kiểu gì vậy???", "Tôi cực kỳ bức xúc!", "Đây là lần thứ 3 tôi phải nhắn rồi đấy!!",
         "Gọi tổng đài mãi không ai nghe máy, quá tệ!", "Dịch vụ tệ hại!"]
POLITE = ["Mong shop hỗ trợ giúp em ạ.", "Nhờ shop kiểm tra giúp mình nhé.", "Cảm ơn shop nhiều ạ.",
          "Em cảm ơn ạ.", "Phiền shop xem giúp với ạ."]
HURRY = ["Cần gấp trong hôm nay.", "Mai mình đi công tác rồi, xử lý gấp giúp mình.", "Chiều nay nhà có khách, cần gấp lắm.",
         "Cần xử lý ngay trong ngày giúp mình."]
CHURN = ["Nếu không giải quyết tôi sẽ không bao giờ mua ở Aurora Mart nữa.", "Lần sau chắc qua bên khác mua cho rồi.",
         "Tôi sẽ hủy thẻ thành viên và không quay lại."]
SOCIAL = ["Tôi sẽ đăng lên Facebook cho mọi người biết.", "Mình sẽ review 1 sao và đăng lên các group.",
          "Tôi đã quay video lại và sẽ đăng TikTok."]
LEGAL = ["Nếu không giải quyết trong 3 ngày, tôi sẽ gửi đơn lên Hội Bảo vệ người tiêu dùng.",
         "Tôi sẽ nhờ luật sư làm việc với công ty.", "Tôi sẽ khiếu nại lên Sở Công Thương."]
EMOJI_ANGRY = ["😡", "😤", "🙄"]
EMOJI_HAPPY = ["❤️", "👍", "🥰", "😊"]


def templates(category: str, c: dict) -> list[tuple[str, str, list[str]]]:
    """(text, kind, flags) for one category. kind is "problem" (something went
    wrong: a complaint) or "request" (asks for a service, nothing went wrong yet)."""
    p, oid, d, amt = c["product"], c["order"], c["days"], vnd(c["amount"])
    other = c["other"]
    return {
        "delivery": [
            (f"Mình đặt {p} từ {d} ngày trước, mã đơn {oid}, đến giờ vẫn chưa nhận được hàng.", "problem", []),
            (f"Đơn {oid} báo đã giao thành công nhưng mình không hề nhận được {p}.", "problem", []),
            (f"Đơn hàng {oid} cứ ở trạng thái 'đang vận chuyển' {d} ngày nay, không ai liên hệ.", "problem", []),
            (f"Shipper hẹn giao {p} hôm qua mà không đến, gọi thì thuê bao. Đơn {oid}.", "problem", []),
            (f"Cho mình đổi địa chỉ giao đơn {oid} sang {c['address']} được không?", "request", []),
            (f"Đơn {oid} ({p}) giờ đang ở đâu vậy shop, khi nào giao tới?", "request", []),
        ],
        "defect": [
            (f"{p} mới nhận hôm qua đã không lên nguồn. Mã đơn {oid}.", "problem", []),
            (f"Mở hộp ra thấy {p} bị móp một góc, màn hình có vết nứt. Đơn {oid}.", "problem", []),
            (f"{p} dùng được {d} ngày thì kêu rè rè rất to, tắt mở lại vẫn vậy.", "problem", []),
            (f"{p} vừa cắm điện thì có mùi khét và khói bốc ra, mình phải rút điện ngay. Đơn {oid}.", "problem", ["safety"]),
            (f"{p} bị rò điện, chạm vào vỏ thấy tê tay. Nhà có trẻ nhỏ, rất nguy hiểm.", "problem", ["safety"]),
            (f"{p} báo lỗi E4 liên tục, không dùng được. Mua ở Aurora Mart, đơn {oid}.", "problem", []),
        ],
        "wrong_item": [
            (f"Mình đặt {p} nhưng nhận được {other}. Đơn {oid}.", "problem", []),
            (f"Đơn {oid} thiếu phụ kiện: hộp {p} không có dây nguồn và remote.", "problem", []),
            (f"Mình đặt 2 cái {p} mà chỉ nhận được 1 cái. Mã đơn {oid}.", "problem", []),
            (f"Giao nhầm màu rồi, mình đặt {p} màu đen mà nhận màu trắng. Đơn {oid}.", "problem", []),
        ],
        "return_refund": [
            (f"Mình muốn trả lại {p} vì không hợp nhu cầu, hàng còn nguyên hộp. Đơn {oid}.", "request", []),
            (f"Đã gửi trả {p} được {d} ngày mà chưa thấy hoàn tiền {amt}đ. Đơn {oid}.", "problem", ["refund_request"]),
            (f"Cho mình hỏi thủ tục đổi {p} sang mẫu cao hơn, mình bù thêm tiền được không? Đơn {oid}.", "request", []),
            (f"Đã hủy đơn {oid} mà tài khoản vẫn bị trừ {amt}đ, khi nào hoàn lại tiền?", "problem", ["refund_request"]),
            (f"Giao trễ quá nên mình không cần {p} nữa, hủy đơn {oid} và hoàn tiền giúp mình.", "problem", ["refund_request"]),
        ],
        "billing": [
            (f"Thẻ của mình bị trừ tiền 2 lần cho đơn {oid}, mỗi lần {amt}đ. Hoàn lại 1 lần giúp mình.", "problem",
             ["refund_request", "double_charge"]),
            (f"Công ty mình cần xuất hóa đơn VAT cho đơn {oid}, MST {c['tax']}. Gửi hóa đơn qua email giúp mình.", "request", []),
            (f"Mã giảm giá AURORA10 không áp dụng được cho đơn {oid}, mình bị tính đủ giá {amt}đ.", "problem", []),
            (f"Hóa đơn của đơn {oid} ghi sai tên công ty, nhờ shop điều chỉnh lại.", "problem", []),
        ],
        "warranty": [
            (f"{p} mua năm ngoái (đơn {oid}) giờ bị hỏng nguồn, còn bảo hành không?", "problem", []),
            (f"Mình cần đặt lịch lắp đặt {p} tại {c['address']}, cuối tuần này được không? Đơn {oid}.", "request", []),
            (f"Kỹ thuật viên hẹn đến bảo hành {p} 2 lần mà không đến.", "problem", []),
            (f"Trung tâm bảo hành giữ {p} của mình {d} ngày rồi chưa trả.", "problem", []),
            (f"Lắp {p} xong thì nước chảy ra sàn, nhờ kỹ thuật qua kiểm tra lại. Đơn {oid}.", "problem", []),
        ],
        "account": [
            ("Mình không nhận được mã OTP nên không đăng nhập được tài khoản Aurora Mart.", "problem", []),
            ("Tài khoản của mình bị đổi mật khẩu mà mình không hề làm, có người lạ đã đăng nhập.", "problem", ["security"]),
            (f"Điểm thành viên của mình bị mất sau khi đặt đơn {oid}.", "problem", []),
            ("Làm sao để xóa tài khoản và toàn bộ dữ liệu cá nhân của mình?", "request", []),
            (f"Đặt đơn {oid} trên app bị báo lỗi thanh toán nhưng tiền vẫn bị trừ {amt}đ.", "problem", ["refund_request"]),
        ],
        "inquiry": [
            (f"{p} còn hàng ở chi nhánh {c['city']} không shop?", "request", []),
            (f"{p} có chương trình khuyến mãi gì trong tháng này không ạ?", "request", []),
            (f"So sánh giúp mình {p} với {other}, cái nào đáng mua hơn?", "request", []),
            (f"{p} giá bao nhiêu, có giao trong ngày ở {c['city']} không?", "request", []),
            (f"Công ty mình cần mua 20 cái {p} cho văn phòng, có giá sỉ không?", "request", []),
            (f"Trả góp 0% khi mua {p} có cần chứng minh thu nhập không?", "request", []),
        ],
        "praise": [
            (f"Nhận được {p} rồi, đóng gói rất cẩn thận, giao nhanh hơn dự kiến.", "praise", []),
            (f"Cảm ơn bạn kỹ thuật viên lắp {p} hôm nay, rất nhiệt tình và chuyên nghiệp.", "praise", []),
            (f"Lần thứ 5 mua ở Aurora Mart, lần nào cũng hài lòng. {p} dùng rất tốt.", "praise", []),
            ("Tổng đài hỗ trợ đổi hàng rất nhanh, cảm ơn team.", "praise", []),
        ],
        "spam": [
            ("Chúc mừng bạn đã trúng thưởng điện thoại! Bấm vào link bit.ly/nhan-qua-ngay để nhận quà.", "spam", []),
            ("Dịch vụ tăng like, tăng follow Facebook giá rẻ, liên hệ Zalo để được tư vấn.", "spam", []),
            ("Cho vay tiền nhanh không cần thế chấp, lãi suất thấp, giải ngân trong 30 phút.", "spam", []),
            ("Tài khoản ngân hàng của bạn sẽ bị khóa, vui lòng cung cấp mã OTP để xác minh.", "spam", []),
        ],
    }[category]


def typo(r: random.Random, text: str) -> str:
    words = text.split()
    for _ in range(max(1, len(words) // 12)):
        i = r.randrange(len(words))
        w = words[i]
        if len(w) > 3 and w.isalpha():
            j = r.randrange(1, len(w) - 1)
            words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2:] if r.random() < 0.5 else w[:j] + w[j + 1:]
    return " ".join(words)


def chatify(text: str) -> str:
    """Vietnamese chat shorthand ("không" -> "ko", "được" -> "dc", ...)."""
    for a, b in [("không", "ko"), ("được", "dc"), ("mình", "mk"), ("vậy", "z"), ("gì", "j"), ("biết", "bít"),
                 ("rồi", "r"), ("với", "vs"), ("nhé", "nha")]:
        text = text.replace(a, b).replace(a.capitalize(), b)
    return text


def make(r: random.Random, n: int) -> dict:
    category = r.choices(CATEGORIES, weights=WEIGHTS)[0]
    prod = r.choice(PRODUCTS)
    c = {"product": prod[1], "order": order_id(r), "address": address(r), "amount": prod[2],
         "days": r.randint(3, 12), "other": r.choice([p for p in PRODUCTS if p != prod])[1],
         "city": r.choice(["Hà Nội", "TP.HCM", "Đà Nẵng", "Cần Thơ", "Hải Phòng", "Nha Trang"]),
         "tax": "03" + "".join(r.choice("0123456789") for _ in range(8))}
    body, kind, flags = r.choice(templates(category, c))
    flags = list(flags)
    channel = r.choices(["email", "zalo", "messenger", "webform"], weights=[35, 30, 25, 10])[0]
    formal = channel in ("email", "webform") and r.random() < 0.75

    # Tone, threats and urgency words. Requests and inquiries stay calm.
    tone = "calm"
    if kind == "problem":
        tone = r.choices(["calm", "upset", "angry"], weights=[30, 40, 30])[0]
        if "safety" in flags and tone == "calm":
            tone = "upset"
    extras: list[str] = []
    if tone == "upset":
        extras.append(r.choice(UPSET))
    elif tone == "angry":
        extras.append(r.choice(ANGRY))
        if r.random() < 0.35:
            extras.append(r.choice(SOCIAL)); flags.append("social_media")
        if r.random() < 0.15:
            extras.append(r.choice(LEGAL)); flags.append("legal_threat")
    if kind == "problem" and tone != "calm" and r.random() < 0.18:
        extras.append(r.choice(CHURN)); flags.append("churn_risk")
    hurry = kind in ("problem", "request") and r.random() < 0.14
    if hurry:
        extras.append(r.choice(HURRY)); flags.append("same_day")
    if tone == "calm" and kind != "spam" and not formal and r.random() < 0.6:
        extras.append(r.choice(POLITE))

    # The triage policy (the model gets the same rules in its instructions).
    if {"legal_threat", "safety", "security"} & set(flags):
        urgency = "critical"
    elif tone == "angry" or {"social_media", "churn_risk", "double_charge", "same_day"} & set(flags):
        urgency = "high"
    elif category in LOW:
        urgency = "low"
    else:
        urgency = "medium"
    sentiment = {"problem": "negative", "praise": "positive"}.get(kind, "neutral")

    name, ph = person(r), phone(r)
    email = (strip_accents(name).lower().replace(" ", ".") + str(r.randint(1, 99)) + "@" +
             r.choice(["gmail.com", "yahoo.com", "outlook.com", "icloud.com"]))
    if formal:
        sig = [name] + ([f"ĐT: {ph}"] if r.random() < 0.7 else []) + ([email] if r.random() < 0.3 else [])
        parts = [r.choice(GREET_FORMAL), (body + " " + " ".join(extras)).strip(), r.choice(CLOSE_FORMAL), "\n".join(sig)]
        text = "\n\n".join(p for p in parts if p.strip())
    else:
        g = r.choice(GREET_CHAT)
        line = (g + " " if g else "") + body + " " + " ".join(extras) + " " + r.choice(CLOSE_CHAT)
        if kind != "spam" and r.random() < 0.35:
            line += f" sđt {ph}" if r.random() < 0.5 else f" liên hệ mình qua số {ph}"
        if tone == "angry" and r.random() < 0.5:
            line += " " + r.choice(EMOJI_ANGRY)
        if kind == "praise" and r.random() < 0.6:
            line += " " + r.choice(EMOJI_HAPPY)
        text = " ".join(line.split())
        if r.random() < 0.45:
            text = chatify(text)
        if r.random() < 0.6:
            text = text[0].lower() + text[1:]
    style = ["formal" if formal else "chat"]
    if r.random() < 0.16:
        text = strip_accents(text); style.append("no_diacritics")
    if r.random() < 0.14:
        text = typo(r, text); style.append("typos")
    if r.random() < 0.05 and kind != "spam":
        text += " " + r.choice(["Pls help.", "ASAP please.", "Thanks a lot.", "So disappointed."]); style.append("english")
    order = c["order"] if c["order"] in text else None
    return {"id": f"MSG-{n:05d}", "channel": channel, "customer": name, "text": text,
            "truth": {"category": category, "urgency": urgency, "sentiment": sentiment,
                      "flags": sorted(set(flags) - {"double_charge", "same_day"}), "order_id": order,
                      "style": "+".join(style)}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=".run/enterprise/inbox/messages.jsonl")
    ap.add_argument("--count", type=int, default=2400)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    r = random.Random(args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = [make(r, n) for n in range(1, args.count + 1)]
    tmp = out.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(out)
    print(f"wrote {len(rows)} messages to {out}")
    print("  categories:", dict(Counter(x["truth"]["category"] for x in rows).most_common()))
    print("  urgency:   ", dict(Counter(x["truth"]["urgency"] for x in rows).most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
