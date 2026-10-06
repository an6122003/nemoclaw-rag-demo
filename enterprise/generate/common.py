# SPDX-License-Identifier: Apache-2.0
"""Shared, seeded building blocks for the enterprise demo data.

Everything here is invented: Aurora Mart is a fictional online retailer of
electronics and home appliances (a sister of Aurora Grid in the labs), and its
customers, suppliers, products, tax codes and phone numbers are random. The
generators keep the "true answer" for every item they make, so the demos can
measure accuracy instead of claiming it.
"""

from __future__ import annotations

import random
import unicodedata

COMPANY = "Aurora Mart"
COMPANY_LEGAL = "Công ty Cổ phần Thương mại Aurora Mart"
COMPANY_TAX = "0319" + "482765"
COMPANY_ADDRESS = "68 Nguyễn Huệ, Phường Sài Gòn, TP. Hồ Chí Minh"

FAMILY = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ",
          "Hồ", "Ngô", "Dương", "Lý", "Trịnh", "Mai", "Đinh", "Tạ"]
MIDDLE = ["Văn", "Thị", "Hữu", "Đức", "Minh", "Thanh", "Ngọc", "Quốc", "Gia", "Anh", "Bảo", "Thu",
          "Kim", "Hoàng", "Xuân", "Thùy", "Phương", "Công", "Khánh", "Mỹ"]
GIVEN = ["An", "Bình", "Châu", "Dũng", "Giang", "Hà", "Hải", "Hạnh", "Hiếu", "Hùng", "Hương", "Khánh",
         "Lan", "Linh", "Long", "Mai", "Minh", "Nam", "Ngân", "Nhung", "Phong", "Phúc", "Quân", "Quang",
         "Sơn", "Tâm", "Thảo", "Thắng", "Trang", "Trung", "Tuấn", "Vy", "Yến", "Khoa", "Duy", "Nhi",
         "Thư", "Đạt", "Huy", "Loan"]

# Two-level addresses (ward + province), as used since the 2025 reorganisation.
PLACES = [
    ("Phường Bến Thành", "TP. Hồ Chí Minh"), ("Phường Tân Định", "TP. Hồ Chí Minh"),
    ("Phường Thủ Đức", "TP. Hồ Chí Minh"), ("Phường Gò Vấp", "TP. Hồ Chí Minh"),
    ("Phường Bình Thạnh", "TP. Hồ Chí Minh"), ("Phường Hoàn Kiếm", "TP. Hà Nội"),
    ("Phường Cầu Giấy", "TP. Hà Nội"), ("Phường Đống Đa", "TP. Hà Nội"), ("Phường Hà Đông", "TP. Hà Nội"),
    ("Phường Hải Châu", "TP. Đà Nẵng"), ("Phường Sơn Trà", "TP. Đà Nẵng"), ("Phường Ninh Kiều", "TP. Cần Thơ"),
    ("Phường Ngô Quyền", "TP. Hải Phòng"), ("Phường Nha Trang", "Tỉnh Khánh Hòa"),
    ("Phường Thủ Dầu Một", "TP. Hồ Chí Minh"), ("Phường Biên Hòa", "Tỉnh Đồng Nai"),
    ("Phường Vinh Phú", "Tỉnh Nghệ An"), ("Phường Buôn Ma Thuột", "Tỉnh Đắk Lắk"),
]
STREETS = ["Nguyễn Trãi", "Lê Lợi", "Trần Hưng Đạo", "Hai Bà Trưng", "Lý Thường Kiệt", "Điện Biên Phủ",
           "Nguyễn Văn Linh", "Cách Mạng Tháng Tám", "Võ Văn Kiệt", "Phạm Văn Đồng", "Láng Hạ",
           "Hoàng Hoa Thám", "Bạch Đằng", "Hùng Vương", "Quang Trung", "Lê Duẩn", "Nguyễn Thị Minh Khai"]

# Aurora Mart's catalogue: (category, product, typical price in VND).
PRODUCTS = [
    ("tivi", "Tivi Nova QLED 55 inch", 12_990_000), ("tivi", "Tivi Nova 4K 43 inch", 7_490_000),
    ("tủ lạnh", "Tủ lạnh FrostLine 420L", 11_290_000), ("tủ lạnh", "Tủ lạnh FrostLine Mini 90L", 3_190_000),
    ("máy giặt", "Máy giặt AquaPro 9kg", 8_790_000), ("máy giặt", "Máy sấy AquaPro 8kg", 9_990_000),
    ("điều hòa", "Điều hòa CoolAir Inverter 1.5HP", 10_490_000), ("điều hòa", "Điều hòa CoolAir 1HP", 7_290_000),
    ("laptop", "Laptop Aster 14 Pro", 21_990_000), ("laptop", "Laptop Aster 15 Student", 13_490_000),
    ("điện thoại", "Điện thoại Zenit X5", 8_990_000), ("điện thoại", "Điện thoại Zenit Lite", 4_290_000),
    ("tai nghe", "Tai nghe không dây Pulse Buds", 1_290_000), ("tai nghe", "Tai nghe chống ồn Pulse Max", 3_490_000),
    ("máy lọc không khí", "Máy lọc không khí PureBreeze 300", 4_590_000),
    ("nồi cơm điện", "Nồi cơm điện RiceMaster 1.8L", 1_590_000), ("lò vi sóng", "Lò vi sóng HeatWave 25L", 2_290_000),
    ("máy hút bụi", "Robot hút bụi CleanBot S7", 7_990_000), ("bàn ủi", "Bàn ủi hơi nước SteamGo", 690_000),
    ("loa", "Loa thanh SoundBar 3.1", 4_990_000),
]

# Fictional suppliers that invoice Aurora Mart (goods and services).
SUPPLIERS = [
    ("Công ty TNHH Thiết bị Điện tử Nova Việt Nam", "goods"),
    ("Công ty Cổ phần Điện lạnh FrostLine", "goods"),
    ("Công ty TNHH Gia dụng Thông minh AquaPro", "goods"),
    ("Công ty TNHH Phân phối Zenit Mobile", "goods"),
    ("Công ty Cổ phần Âm thanh Pulse Audio", "goods"),
    ("Công ty TNHH Giao nhận Nhanh Bách Việt", "logistics"),
    ("Công ty Cổ phần Kho vận Đông Á Express", "logistics"),
    ("Công ty TNHH In ấn Bao bì Phúc Thịnh", "packaging"),
    ("Công ty TNHH Dịch vụ Vệ sinh Công nghiệp Sạch Xanh", "services"),
    ("Công ty Cổ phần Giải pháp Phần mềm Hưng Long", "software"),
    ("Công ty TNHH Quảng cáo Truyền thông Mặt Trời Mới", "marketing"),
    ("Công ty TNHH Bảo trì Điện lạnh Minh Khôi", "services"),
    ("Công ty TNHH Linh kiện Điện tử Sao Bắc", "goods"),
    ("Công ty Cổ phần Phân phối Gia dụng Ánh Dương", "goods"),
    ("Công ty TNHH Thiết bị Văn phòng Trường Thịnh", "goods"),
    ("Công ty TNHH Vận tải Hàng hóa Phương Nam", "logistics"),
    ("Công ty TNHH Giao hàng Chặng cuối Xanh", "logistics"),
    ("Công ty TNHH Bao bì Nhựa An Khang", "packaging"),
    ("Công ty TNHH Dịch vụ Bảo vệ Toàn Tâm", "services"),
    ("Công ty Cổ phần Công nghệ Đám mây Lạc Hồng", "software"),
    ("Công ty TNHH Tổ chức Sự kiện Ngân Hà", "marketing"),
    ("Công ty TNHH Sửa chữa Gia dụng Tâm Đức", "services"),
    ("Công ty TNHH Phần mềm Kế toán Minh Bạch", "software"),
    ("Công ty Cổ phần In Kỹ thuật số Sắc Màu", "packaging"),
]

SERVICE_LINES = {
    "logistics": [("Phí vận chuyển nội thành", "chuyến", 350_000), ("Phí vận chuyển liên tỉnh", "chuyến", 2_400_000),
                  ("Phí lưu kho", "m³/tháng", 180_000), ("Phí bốc xếp hàng hóa", "giờ", 120_000)],
    "packaging": [("Thùng carton 5 lớp 60x40x40", "thùng", 18_500), ("Băng keo in logo", "cuộn", 32_000),
                  ("Xốp chèn hàng", "kg", 45_000), ("Túi khí chống sốc", "cuộn", 260_000)],
    "services": [("Vệ sinh kho định kỳ", "lần", 4_500_000), ("Bảo trì hệ thống điều hòa kho", "lần", 6_800_000),
                 ("Thay lõi lọc máy lọc nước", "bộ", 850_000), ("Dịch vụ bảo vệ kho 24/7", "tháng", 18_000_000),
                 ("Sửa chữa thiết bị trưng bày", "lần", 1_200_000)],
    "software": [("Phí bản quyền phần mềm quản lý kho", "tháng", 12_000_000), ("Phí hỗ trợ kỹ thuật", "giờ", 650_000),
                 ("Phí lưu trữ dữ liệu", "tháng", 3_200_000)],
    "marketing": [("Thiết kế banner khuyến mãi", "bộ", 7_500_000), ("Chạy quảng cáo mạng xã hội", "chiến dịch", 25_000_000),
                  ("In tờ rơi A5", "tờ", 900), ("Tổ chức sự kiện khai trương", "gói", 45_000_000),
                  ("Standee quảng cáo", "cái", 650_000)],
}


def rng(seed: int) -> random.Random:
    return random.Random(seed)


def person(r: random.Random) -> str:
    mid = r.choice(MIDDLE)
    return f"{r.choice(FAMILY)} {mid} {r.choice(GIVEN)}"


def phone(r: random.Random) -> str:
    return r.choice(["090", "091", "093", "096", "097", "098", "070", "077", "081", "085"]) + "".join(r.choice("0123456789") for _ in range(7))


def tax_code(r: random.Random) -> str:
    return r.choice(["01", "02", "03", "04", "31", "37", "48"]) + "".join(r.choice("0123456789") for _ in range(8))


def address(r: random.Random) -> str:
    ward, prov = r.choice(PLACES)
    return f"{r.randint(1, 450)} {r.choice(STREETS)}, {ward}, {prov}"


def order_id(r: random.Random) -> str:
    return f"AM{r.randint(2600000, 2699999)}"


def strip_accents(text: str) -> str:
    """'Tôi muốn đổi trả' -> 'Toi muon doi tra': how many people type on their phones."""
    text = text.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def vnd(n: int) -> str:
    return f"{n:,}".replace(",", ".")


_DIGITS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _three(n: int, full: bool) -> list[str]:
    h, t, u = n // 100, n // 10 % 10, n % 10
    out: list[str] = []
    if full or h:
        out += [_DIGITS[h], "trăm"]
    if t == 0:
        if u and (full or h):
            out.append("lẻ")
    elif t == 1:
        out.append("mười")
    else:
        out += [_DIGITS[t], "mươi"]
    if u:
        if u == 1 and t >= 2:
            out.append("mốt")
        elif u == 5 and t >= 1:
            out.append("lăm")
        elif u == 4 and t >= 2:
            out.append("tư")
        else:
            out.append(_DIGITS[u])
    return out


def amount_in_words(n: int) -> str:
    """Vietnamese reading of an amount, as printed on invoices ("Số tiền viết bằng chữ")."""
    if n == 0:
        return "Không đồng"
    units = ["", "nghìn", "triệu", "tỷ"]
    groups = []
    while n:
        groups.append(n % 1000)
        n //= 1000
    words: list[str] = []
    for i in range(len(groups) - 1, -1, -1):
        g = groups[i]
        if g == 0:
            continue
        words += _three(g, full=i < len(groups) - 1)
        if units[i % 4]:
            words.append(units[i % 4])
        if i >= 4 and i % 4 == 0:
            words.append("tỷ")
    text = " ".join(words) + " đồng"
    return text[0].upper() + text[1:]
