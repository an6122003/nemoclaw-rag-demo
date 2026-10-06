#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Synthetic call-centre recordings for the "call quality" demo.

    .run/tts-venv/bin/python enterprise/generate/calls.py --out .run/enterprise/calls \
        --voice .run/enterprise/voices/vi_VN-vais1000-medium.onnx --count 300

Writes call-0001.wav … (8 kHz stereo, like a telephone recording: the agent
on the left channel, the customer on the right) and truth.json: the script of
every call and the answer key for the quality checklist — greeting, the
"this call is recorded" notice, identity check, empathy, the outcome, the
closing, and violations (unauthorised promises, rudeness).

Voices: Piper (piper-tts, GPL-3.0, installed separately into .run/tts-venv)
with the vi_VN vais1000 voice (trained on the VAIS-1000 corpus, CC BY 4.0).
The customer is the same voice pitched up or down, so the two sides sound
like different people. Every call, person and order number is invented.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import random
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FAMILY, GIVEN, PRODUCTS, order_id  # noqa: E402

SR = 8000  # telephone audio
SCENARIOS = ["delivery", "defect", "refund", "install", "double_charge", "product_question"]
CHECKS = ["greeting", "disclosure", "verification", "empathy", "closing"]
# How the agents say the company name, so speech-to-text hears what was said.
BRAND = "Ô Rô Ra Mát"
AGENTS_F = ["Thu Trang", "Ngọc Anh", "Minh Thư", "Thanh Hà", "Bảo Ngọc", "Phương Linh"]
AGENTS_M = ["Quốc Huy", "Minh Đức", "Hoàng Nam", "Gia Bảo", "Thành Long"]


def digits(code: str) -> str:
    """'AM2615582' -> 'A M, hai sáu một, năm năm tám, hai': how people read codes aloud."""
    words = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
    head = " ".join(c for c in code if c.isalpha())
    nums = [words[int(c)] for c in code if c.isdigit()]
    groups = [" ".join(nums[i:i + 3]) for i in range(0, len(nums), 3)]
    return (head + ", " if head else "") + ", ".join(groups)


def phone_words(r: random.Random) -> str:
    words = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
    num = "09" + "".join(str(r.randint(0, 9)) for _ in range(8))
    return ", ".join(" ".join(words[int(c)] for c in num[i:i + 3]) for i in range(0, len(num), 3))


def make_call(r: random.Random, n: int) -> dict:
    scenario = r.choice(SCENARIOS)
    agent_female = r.random() < 0.6
    agent = r.choice(AGENTS_F if agent_female else AGENTS_M)
    cust_male = r.random() < 0.5
    you = "anh" if cust_male else "chị"
    You = you.capitalize()
    cname = f"{r.choice(FAMILY)} {r.choice(GIVEN)}"
    prod = r.choice(PRODUCTS)[1]
    oid = order_id(r)
    mood = r.choices(["calm", "upset", "angry"], weights=[40, 40, 20])[0]

    # The agent's behaviour: most agents follow the script, some skip steps,
    # a few break the rules. This is the answer key.
    tier = r.choices(["good", "ok", "poor"], weights=[58, 28, 14])[0]
    miss = {"good": 0.05, "ok": 0.3, "poor": 0.6}[tier]
    beh = {c: r.random() > miss for c in CHECKS}
    if scenario == "product_question":
        beh["verification"] = r.random() > 0.5  # nothing to verify for a price question… sometimes they still do
    violations = []
    if tier == "poor" and r.random() < 0.55:
        violations.append(r.choice(["unauthorized_promise", "rude"]))
    elif tier == "ok" and r.random() < 0.08:
        violations.append("unauthorized_promise")
    resolution = r.choices(["resolved", "follow_up", "unresolved"],
                           weights={"good": [70, 28, 2], "ok": [45, 40, 15], "poor": [20, 35, 45]}[tier])[0]

    A, C = "agent", "customer"
    turns: list[tuple[str, str]] = []
    # opening
    if beh["greeting"]:
        opening = r.choice([f"{BRAND} xin chào, em là {agent}.", f"Dạ, {BRAND} xin chào {you}, em tên là {agent}.",
                            f"Tổng đài {BRAND} xin nghe, em là {agent} ạ."])
    else:
        opening = r.choice(["Alô.", "Dạ alô, tổng đài nghe.", "Vâng, alô ạ."])
    if beh["disclosure"]:
        opening += " " + r.choice(["Cuộc gọi được ghi âm để nâng cao chất lượng dịch vụ.",
                                   "Cuộc gọi này sẽ được ghi âm để đảm bảo chất lượng phục vụ."])
    opening += " " + r.choice([f"Em có thể hỗ trợ gì cho {you} ạ?", f"{You} cần em hỗ trợ gì ạ?"])
    turns.append((A, opening))

    problem = {
        "delivery": [f"Tôi đặt cái {prod} hơn một tuần rồi mà chưa thấy giao.",
                     f"Đơn hàng {prod} của tôi báo đã giao mà tôi không nhận được gì cả."],
        "defect": [f"Cái {prod} tôi mới nhận hôm qua, cắm điện vào không lên nguồn.",
                   f"Tôi mua cái {prod} được ba ngày thì nó kêu rè rè rất to."],
        "refund": [f"Tôi trả lại cái {prod} hai tuần rồi mà vẫn chưa được hoàn tiền.",
                   f"Tôi hủy đơn {prod} rồi mà tài khoản vẫn bị trừ tiền."],
        "install": [f"Tôi muốn đặt lịch lắp cái {prod} vào cuối tuần này.",
                    f"Kỹ thuật viên hẹn lắp {prod} hôm qua mà không thấy đến."],
        "double_charge": [f"Thẻ của tôi bị trừ tiền hai lần cho đơn {prod}.",
                          "Tôi thanh toán một đơn mà ngân hàng báo trừ hai lần tiền."],
        "product_question": [f"Cho tôi hỏi cái {prod} còn hàng không, giá bao nhiêu?",
                             f"Tôi muốn hỏi {prod} có trả góp không phần trăm không?"],
    }[scenario]
    line = r.choice(problem)
    if mood == "upset":
        line += " " + r.choice(["Tôi chờ lâu quá rồi đấy.", "Thật sự là hơi thất vọng."])
    elif mood == "angry":
        line += " " + r.choice(["Làm ăn kiểu gì vậy?", "Tôi gọi lần thứ ba rồi đấy!", "Thật là quá đáng!"])
    turns.append((C, line))

    if beh["empathy"] and scenario != "product_question":
        turns.append((A, r.choice([f"Dạ em rất xin lỗi {you} vì sự bất tiện này ạ.",
                                   f"Em thành thật xin lỗi, em hiểu là {you} đang rất khó chịu.",
                                   f"Dạ em xin lỗi {you}, để em kiểm tra ngay cho {you} ạ."])))
    elif beh["empathy"]:
        turns.append((A, f"Dạ vâng, em cảm ơn {you} đã quan tâm đến sản phẩm bên em ạ."))
    else:
        turns.append((A, r.choice(["Rồi.", "Vâng.", "Ừ, để xem."])))

    if beh["verification"]:
        if r.random() < 0.6:
            turns.append((A, f"{You} cho em xin mã đơn hàng để em kiểm tra ạ."))
            turns.append((C, f"Mã đơn là {digits(oid)}."))
        else:
            turns.append((A, f"{You} cho em xin số điện thoại đặt hàng để em xác minh ạ."))
            turns.append((C, f"Số của tôi là {phone_words(r)}."))
        turns.append((A, f"Dạ em cảm ơn, em thấy thông tin của {you} rồi ạ."))

    clarify = {
        "delivery": [(A, f"{You} đặt hàng từ ngày nào và giao về địa chỉ nào ạ?"),
                     (C, "Tôi đặt từ thứ hai tuần trước, giao về nhà riêng, tôi ở nhà cả ngày mà không thấy ai gọi.")],
        "defect": [(A, f"{You} đã thử cắm sang ổ điện khác chưa ạ, và máy có báo đèn hay mã lỗi gì không?"),
                   (C, "Tôi thử hai ổ khác nhau rồi, đèn không sáng, không có tiếng gì hết.")],
        "refund": [(A, f"{You} thanh toán bằng thẻ hay chuyển khoản ạ?"),
                   (C, "Tôi trả bằng thẻ tín dụng, lúc trả hàng nhân viên bảo một tuần là có tiền.")],
        "install": [(A, f"Nhà {you} là nhà riêng hay chung cư, có cần khoan tường không ạ?"),
                    (C, "Chung cư, tầng mười hai, chắc là phải khoan để treo lên tường.")],
        "double_charge": [(A, f"{You} thấy hai lần trừ tiền vào cùng một ngày phải không ạ?"),
                          (C, "Đúng rồi, cùng một ngày, cùng số tiền, cách nhau có vài phút.")],
        "product_question": [(A, f"{You} định dùng cho gia đình mấy người ạ?"),
                             (C, "Nhà tôi bốn người, tôi muốn loại tiết kiệm điện một chút.")],
    }[scenario]
    turns.extend(clarify)
    followups = [
        [(C, "Thế tôi có phải ở nhà để chờ không?"), (A, f"Dạ {you} không cần chờ, bên em sẽ gọi trước khi đến ạ.")],
        [(C, "Có mất thêm phí gì không em?"), (A, "Dạ không mất thêm phí gì ạ.")],
        [(C, "Em gửi tin nhắn xác nhận cho tôi được không?"), (A, f"Dạ được ạ, em sẽ gửi tin nhắn cho {you} ngay sau cuộc gọi.")],
        [(C, "Lần trước tôi gọi cũng được hứa như vậy rồi đấy."), (A, f"Dạ em ghi chú lại để theo dõi riêng cho {you} ạ.")],
    ]

    if "rude" in violations:
        turns.append((C, r.choice(["Sao lâu thế, tôi cần biết ngay bây giờ.", "Tôi nói rồi mà, sao cứ hỏi lại mãi vậy?"])))
        turns.append((A, r.choice([f"{You} nói nhiều quá, để em làm việc đã.", f"Cái này là lỗi của {you} chứ không phải bên em.",
                                   f"{You} tự đọc hướng dẫn đi, em không giải thích lại đâu."])))

    outcome = {
        "resolved": {
            "delivery": f"Đơn của {you} đang ở kho giao vận, chiều mai sẽ giao tới, em đã đánh dấu giao ưu tiên.",
            "defect": f"Em đã tạo yêu cầu đổi mới, ngày mai nhân viên sẽ mang máy mới đến và nhận lại máy lỗi.",
            "refund": f"Em đã kiểm tra, tiền hoàn đã được duyệt, trong ba ngày làm việc sẽ về tài khoản của {you}.",
            "install": f"Em đã đặt lịch lắp đặt sáng thứ bảy, kỹ thuật viên sẽ gọi trước cho {you} ba mươi phút.",
            "double_charge": f"Em đã gửi yêu cầu hoàn lần trừ tiền thứ hai, trong năm ngày làm việc tiền sẽ về thẻ của {you}.",
            "product_question": f"Sản phẩm còn hàng ạ, có trả góp không phần trăm trong sáu tháng, em gửi thông tin qua tin nhắn cho {you} nhé.",
        },
        "follow_up": {
            s: f"Em cần kiểm tra thêm với bộ phận liên quan, em hứa sẽ gọi lại cho {you} trước năm giờ chiều nay ạ."
            for s in SCENARIOS
        },
        "unresolved": {
            s: r.choice(["Cái này em cũng không biết nữa, chắc phải chờ thôi.",
                         f"Em không xử lý được, {you} gọi lại sau nhé.", "Bên em không có thông tin, em chịu."])
            for s in SCENARIOS
        },
    }[resolution][scenario]
    turns.append((A, outcome))
    if "unauthorized_promise" in violations:
        turns.append((A, r.choice([f"Thôi em hoàn tiền gấp đôi cho {you} luôn cho {you} vui.",
                                   f"Em sẽ tặng {you} thêm một cái máy mới, không cần trả lại máy cũ đâu.",
                                   f"Em giảm cho {you} năm mươi phần trăm đơn sau, em tự quyết được."])))

    if resolution != "unresolved":
        for pair in r.sample(followups, r.randint(1, 2)):
            turns.extend(pair)

    # the customer's reaction, which decides how the call ends
    if resolution == "resolved" and not violations:
        cust_end = "satisfied"
        turns.append((C, r.choice(["Vậy thì tốt quá, cảm ơn em.", "Ừ được rồi, cảm ơn em nhiều.", "Thế thì ổn, cảm ơn em."])))
    elif resolution == "unresolved" or "rude" in violations:
        cust_end = "dissatisfied"
        turns.append((C, r.choice(["Thôi được rồi, tôi sẽ khiếu nại.", "Vậy thì tôi không biết nói sao nữa.",
                                   "Dịch vụ kiểu này thì tôi chịu rồi."])))
    else:
        cust_end = "neutral"
        turns.append((C, r.choice(["Ừ, vậy em nhớ gọi lại cho tôi nhé.", "Được, tôi chờ.", "Ừ, vậy cũng được."])))

    if beh["closing"]:
        turns.append((A, r.choice([f"{You} cần em hỗ trợ thêm gì nữa không ạ? Cảm ơn {you} đã gọi {BRAND}, chúc {you} một ngày tốt lành.",
                                   f"Dạ, {you} còn cần hỗ trợ gì thêm không ạ? Em cảm ơn {you}, chào {you} ạ."])))
        turns.append((C, r.choice(["Không, cảm ơn em.", "Thế thôi, chào em.", "Ừ, chào em."])))
    else:
        turns.append((A, r.choice(["Vâng, thế thôi nhé.", "Rồi, chào.", "Ok."])))

    score = score_from({**beh, "resolution": resolution, "violations": violations})
    return {"id": f"CALL-{n:04d}", "file": f"call-{n:04d}.wav", "scenario": scenario, "agent": agent,
            "customer": cname, "order_id": oid, "product": prod, "mood": mood,
            "voices": {"agent": "f" if agent_female else "m", "customer": "m" if cust_male else "f"},
            "turns": [{"speaker": s, "text": t} for s, t in turns],
            "truth": {**beh, "resolution": resolution, "violations": violations, "customer_end": cust_end,
                      "score": score, "passed": score >= 70 and not violations}}


def score_from(x: dict) -> int:
    """The checklist the QA team uses. The demo scores the AI's answers the same way."""
    s = 10 * bool(x.get("greeting")) + 10 * bool(x.get("disclosure")) + 15 * bool(x.get("verification")) \
        + 15 * bool(x.get("empathy")) + 10 * bool(x.get("closing"))
    s += {"resolved": 30, "follow_up": 15}.get(x.get("resolution"), 0)
    s += 10 if not x.get("violations") else 0
    return s


# ------------------------------------------------------------------- audio ---
_VOICE = None


def _voice(path: str):
    """One voice per worker process, on one CPU thread (the processes share the cores)."""
    global _VOICE
    if _VOICE is None:
        import onnxruntime as ort
        from piper import PiperVoice
        _VOICE = PiperVoice.load(path)
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        _VOICE.session = ort.InferenceSession(str(path), sess_options=opts, providers=["CPUExecutionProvider"])
    return _VOICE


def _fir(sr: int, fc: float, taps: int = 101):
    """Windowed-sinc low-pass filter taps."""
    import numpy as np
    n = np.arange(taps) - (taps - 1) / 2
    h = np.sinc(2 * fc / sr * n) * np.hamming(taps)
    return (h / h.sum()).astype(np.float32)


def synth(voice_path: str, text: str, pitch: float, speed: float):
    """Speech as float samples at 8 kHz; pitch < 1 sounds deeper, > 1 higher."""
    import numpy as np
    from piper import SynthesisConfig
    v = _voice(voice_path)
    cfg = SynthesisConfig(length_scale=speed * pitch, noise_scale=0.6, noise_w_scale=0.7)
    chunks = list(v.synthesize(text, syn_config=cfg))
    sr = chunks[0].sample_rate
    x = np.concatenate([c.audio_float_array for c in chunks]).astype(np.float32)
    # Keep what will still fit under 3.6 kHz after the pitch shift, then play it
    # back 1/pitch times as fast (the shift) straight at the telephone rate.
    x = np.convolve(x, _fir(sr, min(3600 / pitch, sr * 0.45)), mode="same")
    n_out = int(len(x) / pitch * SR / sr)
    x = np.interp(np.linspace(0, len(x) - 1, n_out), np.arange(len(x)), x).astype(np.float32)
    lp = _fir(SR, 300)  # telephone band starts around 300 Hz: subtract the lows
    return (x - np.convolve(x, lp, mode="same")).astype(np.float32)


def render(job: tuple) -> str:
    call, out, voice_path, seed = job
    import numpy as np
    r = random.Random(seed)
    pitch = {"agent": 1.0 if call["voices"]["agent"] == "f" else 0.8,
             "customer": 1.12 if call["voices"]["customer"] == "f" else 0.78}
    speed = {"agent": r.uniform(0.9, 1.0), "customer": r.uniform(0.95, 1.1)}
    if call["mood"] == "angry":
        speed["customer"] *= 0.9
    t = r.uniform(0.4, 0.9)
    pieces = []
    for i, turn in enumerate(call["turns"]):
        y = synth(voice_path, turn["text"], pitch[turn["speaker"]], speed[turn["speaker"]])
        turn["start"] = round(t, 2)
        turn["end"] = round(t + len(y) / SR, 2)
        pieces.append((turn["speaker"], int(t * SR), y))
        t = turn["end"] + r.uniform(0.3, 1.0)
    total = int((t + 0.6) * SR)
    stereo = np.zeros((total, 2), dtype=np.float32)
    for speaker, at, y in pieces:
        ch = 0 if speaker == "agent" else 1
        stereo[at:at + len(y), ch] += y * (0.8 if ch == 0 else r.uniform(0.6, 0.85))
    stereo += np.random.default_rng(seed).normal(0, 0.003, stereo.shape).astype(np.float32)  # line hiss
    pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(str(Path(out) / call["file"]), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    call["seconds"] = round(total / SR, 1)
    return json.dumps(call, ensure_ascii=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=".run/enterprise/calls")
    ap.add_argument("--voice", required=True, help="Piper voice (.onnx, with its .onnx.json beside it)")
    ap.add_argument("--count", type=int, default=300)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--workers", type=int, default=0)
    args = ap.parse_args()
    r = random.Random(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    calls = [make_call(r, n) for n in range(1, args.count + 1)]
    jobs = [(c, str(out), args.voice, args.seed * 7919 + i * 101) for i, c in enumerate(calls)]
    workers = args.workers or min(16, os.cpu_count() or 2)
    t0 = time.time()
    done = []
    with multiprocessing.Pool(workers) as pool:
        for k, res in enumerate(pool.imap(render, jobs, chunksize=2), 1):
            done.append(json.loads(res))
            if k % 50 == 0:
                print(f"  {k}/{len(jobs)} calls recorded", flush=True)
    (out / "truth.json").write_text(json.dumps(done, ensure_ascii=False, indent=1))
    hours = sum(c["seconds"] for c in done) / 3600
    print(f"wrote {len(done)} calls ({hours:.1f} hours of audio) to {out} in {time.time() - t0:.0f} s on {workers} processes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
