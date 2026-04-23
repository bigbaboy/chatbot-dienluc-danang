"""
Module chứa các hàm tính toán thuần (pure functions) không phụ thuộc Streamlit.

Việc tách các hàm này ra khỏi `app.py` giúp:
  - Viết unit test dễ dàng (không cần khởi tạo Streamlit)
  - Tái sử dụng trong script khác (ví dụ: batch processing, API)
  - Giảm độ phức tạp của file app.py
"""

import re
from typing import List, Tuple, Dict, Optional
from config import BIEU_GIA_DIEN, VAT_RATE

# Số ngày dùng để quy đổi kWh/ngày → kWh/tháng
DAYS_PER_MONTH = 30


# ────────────────────────────────────────────────────────────────
# PHÁT HIỆN CÂU HỎI TÍNH TIỀN ĐIỆN (intent detection)
# ────────────────────────────────────────────────────────────────
# Số (có thể có dấu thập phân) đi kèm đơn vị "kWh" / "chữ" / "số điện"
# Ví dụ khớp: "250 kWh", "300 chữ", "150 số điện", "75.5 kwh"
_KWH_PATTERN = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(?:k\s*wh|kwh|chữ\s+điện|chữ|số\s+điện)\b",
    re.IGNORECASE,
)
# Từ khóa thể hiện ý định hỏi về tiền/chi phí
_MONEY_KEYWORDS = (
    "tiền", "hết", "bao nhiêu", "hóa đơn", "phải trả",
    "chi phí", "tính tiền", "phải đóng", "tốn",
)
# Giới hạn kWh hợp lý cho hộ gia đình (tránh false positive với số quá lớn)
_KWH_BOUND_MAX = 10_000.0


def trich_kwh_tu_cau_hoi(cau_hoi: str) -> Optional[float]:
    """
    Phát hiện câu hỏi tính tiền điện và trích số kWh.

    Áp dụng cho các câu hỏi dạng:
      - "250 kWh hết bao nhiêu tiền?"
      - "Nếu tôi dùng 300 chữ thì tiền điện là bao nhiêu?"
      - "Tính tiền điện cho 150 kWh"

    Yêu cầu: câu hỏi phải có (1) số kWh và (2) ít nhất 1 từ khóa
    về tiền/chi phí. Nếu không thỏa cả 2 → trả về None (để câu hỏi
    đi vào RAG bình thường).

    Args:
        cau_hoi: Câu hỏi của người dùng (có thể đã có profile prefix)

    Returns:
        Số kWh nếu phát hiện ý định tính tiền, None nếu không.
    """
    if not cau_hoi:
        return None

    cau_hoi_lower = cau_hoi.lower()
    if not any(kw in cau_hoi_lower for kw in _MONEY_KEYWORDS):
        return None

    match = _KWH_PATTERN.search(cau_hoi_lower)
    if not match:
        return None

    try:
        kwh = float(match.group(1).replace(",", "."))
    except ValueError:
        return None

    if 0 < kwh <= _KWH_BOUND_MAX:
        return kwh
    return None


# ────────────────────────────────────────────────────────────────
# VALIDATE ĐỊNH DẠNG THÁNG (MM/YYYY)
# ────────────────────────────────────────────────────────────────
# Regex: "MM/YYYY" hoặc "M/YYYY", năm 2000-2099 (đủ dùng cho nhiều thập kỷ)
_THANG_PATTERN = re.compile(r"^(0?[1-9]|1[0-2])/20\d{2}$")


def thang_hop_le(s: str) -> bool:
    """
    Kiểm tra định dạng tháng tiêu thụ '03/2025' (MM/YYYY hoặc M/YYYY).

    Yêu cầu:
      - Tháng 1-12 (cho phép '03' hoặc '3')
      - Năm 4 chữ số, thuộc [2000, 2099]
      - Không có ký tự thừa

    Args:
        s: Chuỗi input (sẽ được strip tự động)

    Returns:
        True nếu format hợp lệ, False nếu sai.
    """
    if not s:
        return False
    return bool(_THANG_PATTERN.match(s.strip()))


# ────────────────────────────────────────────────────────────────
# TÍNH TIỀN ĐIỆN BẬC THANG
# ────────────────────────────────────────────────────────────────
def tinh_tien_dien(kwh: float) -> Tuple[List[dict], float, float, float]:
    """
    Tính tiền điện sinh hoạt theo biểu giá bậc thang.

    Hàm này xử lý tổng quát cho N bậc — chỉ cần sửa danh sách BIEU_GIA_DIEN
    trong config.py khi có Quyết định mới (ví dụ chuyển từ 6 bậc sang 5 bậc),
    hàm vẫn chạy đúng mà không cần sửa code.

    Cách tính bậc thang:
      Mỗi bậc có một khoảng kWh cố định. Ví dụ với biểu giá 6 bậc QĐ 1279:
        - Bậc 1: 0–50 kWh     → 50 kWh đầu tiên
        - Bậc 2: 51–100 kWh   → 50 kWh tiếp theo
        - Bậc 3: 101–200 kWh  → 100 kWh tiếp theo
        - ...

    Args:
        kwh: Tổng số kWh tiêu thụ trong tháng (>= 0)

    Returns:
        Tuple (chi_tiet, tong, vat, tong_thanh_toan):
          - chi_tiet: list dict từng bậc đã tính, key: bac, tu, den, don_gia, sl, tt
          - tong: tiền trước VAT (float)
          - vat: tiền VAT (float)
          - tong_thanh_toan: tiền sau VAT = tong + vat (float)

    Raises:
        ValueError: nếu kwh < 0
    """
    if kwh < 0:
        raise ValueError(f"Số kWh phải >= 0, nhận được {kwh}")

    chi_tiet = []
    tong = 0.0
    kwh_con_lai = float(kwh)

    for bg in BIEU_GIA_DIEN:
        if kwh_con_lai <= 0:
            break

        # Tính số kWh rơi vào bậc này
        if bg["den"] is None:
            # Bậc cao nhất không giới hạn trên
            so_luong = kwh_con_lai
        else:
            # Giới hạn kWh của bậc này.
            # Bậc 1 bắt đầu từ 0 → kWh của bậc = den - tu
            # Các bậc khác bắt đầu từ (tu), kết thúc ở (den) → kWh = den - tu + 1
            # Ví dụ: bậc 2 "51-100" = 100 - 51 + 1 = 50 kWh
            gioi_han_bac = bg["den"] - bg["tu"] + (0 if bg["tu"] == 0 else 1)
            so_luong = min(kwh_con_lai, gioi_han_bac)

        thanh_tien = so_luong * bg["don_gia"]
        chi_tiet.append({
            "bac": bg["bac"],
            "tu": bg["tu"],
            "den": bg["den"] if bg["den"] is not None else "trở lên",
            "don_gia": bg["don_gia"],
            "sl": so_luong,
            "tt": thanh_tien,
        })
        tong += thanh_tien
        kwh_con_lai -= so_luong

    vat = tong * VAT_RATE
    return chi_tiet, tong, vat, tong + vat


# ────────────────────────────────────────────────────────────────
# TÍNH CONFIDENCE SCORE
# ────────────────────────────────────────────────────────────────
def tinh_confidence(l2_sq: float) -> float:
    """
    Chuyển L2² distance của FAISS sang cosine similarity [0, 1].

    Với embeddings đã được normalize (unit vectors):
        cosine(a, b) = 1 - ||a - b||² / 2

    Args:
        l2_sq: Bình phương khoảng cách L2 (từ FAISS)

    Returns:
        Cosine similarity, giới hạn trong [0, 1]
    """
    return max(0.0, min(1.0, 1.0 - l2_sq / 2.0))


# ────────────────────────────────────────────────────────────────
# ĐỊNH DẠNG TIỀN TỆ
# ────────────────────────────────────────────────────────────────
def dinh_dang_tien(so: float) -> str:
    """Chuyển số thành chuỗi VND có phân cách nghìn. Ví dụ: 1500000 → '1,500,000 đ'."""
    return f"{int(so):,} đ"


# ────────────────────────────────────────────────────────────────
# TÍNH kWh/THÁNG CỦA THIẾT BỊ
# ────────────────────────────────────────────────────────────────
def tinh_kwh_thang(
    power_kw: Optional[float],
    qty: int,
    hours: float,
    kwh_per_day_fixed: Optional[float] = None,
) -> float:
    """
    Tính tổng kWh/tháng của một thiết bị.

    Args:
        power_kw: Công suất của 1 thiết bị (kW). None nếu dùng kwh_per_day_fixed.
        qty: Số lượng thiết bị (>= 0)
        hours: Giờ sử dụng mỗi ngày
        kwh_per_day_fixed: kWh/ngày cố định (dùng cho tủ lạnh, router). Ưu tiên hơn power_kw nếu có.

    Returns:
        Tổng kWh/tháng (đã làm tròn 1 số thập phân)
    """
    if qty <= 0:
        return 0.0

    if kwh_per_day_fixed is not None:
        kwh = qty * kwh_per_day_fixed * DAYS_PER_MONTH
    elif power_kw is not None:
        kwh = qty * power_kw * hours * DAYS_PER_MONTH
    else:
        return 0.0

    return round(kwh, 1)


# ────────────────────────────────────────────────────────────────
# TÍNH TIẾT KIỆM KHI TÁCH HỘ
# ────────────────────────────────────────────────────────────────
def tinh_tiet_kiem_tach_ho(
    kwh_tong: float, so_ho: int
) -> Tuple[float, float, float, float]:
    """
    So sánh tiền điện khi tính chung 1 hộ vs tách thành nhiều hộ.

    Ví dụ: 600 kWh tính 1 hộ sẽ vào bậc 6 (đắt), nhưng tính 2 hộ × 300 kWh
    chỉ vào bậc 4 (rẻ hơn).

    Args:
        kwh_tong: Tổng kWh tiêu thụ
        so_ho: Số hộ được phân bổ (>= 1)

    Returns:
        Tuple (tong_1_ho, tong_nhieu_ho, tiet_kiem, phan_tram_tiet_kiem)
    """
    if so_ho < 1:
        raise ValueError(f"Số hộ phải >= 1, nhận được {so_ho}")

    _, _, _, tong_1_ho = tinh_tien_dien(kwh_tong)

    kwh_moi_ho = kwh_tong / so_ho
    _, _, _, tong_per_ho = tinh_tien_dien(kwh_moi_ho)
    tong_nhieu_ho = tong_per_ho * so_ho

    tiet_kiem = tong_1_ho - tong_nhieu_ho
    phan_tram = (tiet_kiem / tong_1_ho * 100) if tong_1_ho > 0 else 0.0

    return tong_1_ho, tong_nhieu_ho, tiet_kiem, phan_tram


# ────────────────────────────────────────────────────────────────
# PHÂN CHIA ĐIỆN MẶT TRỜI: TỰ DÙNG vs BÁN LẠI EVN
# ────────────────────────────────────────────────────────────────
def tinh_tu_dung_va_ban_lai(
    san_luong_kwh: float,
    tu_dung_rate: float,
    tieu_thu_kwh: float,
) -> Tuple[float, float]:
    """
    Phân chia sản lượng điện mặt trời thành phần tự dùng và phần bán lại.

    Khái niệm "tỷ lệ tự dùng" (tu_dung_rate): **phần trăm tiêu thụ của hộ
    rơi vào ban ngày** khi ĐMT đang sản xuất. Ví dụ rate=70% nghĩa là
    trong 250 kWh tiêu thụ/tháng, có 250×0.7 = 175 kWh vào ban ngày
    (có thể được ĐMT phủ), còn 75 kWh vào ban đêm (không phủ được).

    Logic:
      - Nhu cầu ban ngày = tiêu_thụ × tu_dung_rate
      - kwh_tu_dung = min(sản_lượng, nhu_cầu_ban_ngày)
        (không tự dùng vượt quá: sản lượng có sẵn, hoặc nhu cầu ban ngày)
      - kwh_ban_lai = sản_lượng - kwh_tu_dung (phần dư bán cho EVN)

    Khác với logic cũ `min(sản_lượng × rate, tiêu_thụ)`: logic cũ sai vì
    khi sản_lượng lớn (dư), mọi rate đều cho cùng kết quả (bị chặn bởi
    tiêu_thụ), làm slider không có tác dụng.

    Args:
        san_luong_kwh: Sản lượng ĐMT tạo ra trong tháng (kWh, ≥ 0)
        tu_dung_rate: Tỷ lệ tiêu thụ rơi vào ban ngày, [0, 1]
        tieu_thu_kwh: Tổng tiêu thụ điện của hộ trong tháng (kWh, ≥ 0)

    Returns:
        Tuple (kwh_tu_dung, kwh_ban_lai)
    """
    if san_luong_kwh < 0 or tieu_thu_kwh < 0:
        raise ValueError("san_luong và tieu_thu phải >= 0")
    if not 0.0 <= tu_dung_rate <= 1.0:
        raise ValueError(f"tu_dung_rate phải trong [0, 1], nhận được {tu_dung_rate}")

    nhu_cau_ban_ngay = tieu_thu_kwh * tu_dung_rate
    kwh_tu_dung = min(san_luong_kwh, nhu_cau_ban_ngay)
    kwh_ban_lai = max(0.0, san_luong_kwh - kwh_tu_dung)
    return kwh_tu_dung, kwh_ban_lai


def tinh_dien_mat_troi(
    dien_tich_m2: float,
    psh: float,
    panel_w: int,
    panel_m2: float,
    system_eff: float,
) -> Dict[str, float]:
    """
    Tính sản lượng điện mặt trời mái nhà.

    Args:
        dien_tich_m2: Diện tích mái khả dụng (m²)
        psh: Peak Sun Hours — giờ nắng đỉnh trung bình (h/ngày)
        panel_w: Công suất 1 tấm pin (Wp)
        panel_m2: Diện tích 1 tấm (m²)
        system_eff: Hiệu suất hệ thống (0-1), đã tính hao phí inverter/dây/nhiệt độ

    Returns:
        Dict với key: so_tam, cong_suat_kwp, san_luong_ngay_kwh, san_luong_thang_kwh
    """
    if dien_tich_m2 < panel_m2:
        return {
            "so_tam": 0,
            "cong_suat_kwp": 0.0,
            "san_luong_ngay_kwh": 0.0,
            "san_luong_thang_kwh": 0.0,
        }

    so_tam = int(dien_tich_m2 / panel_m2)
    cong_suat_kwp = so_tam * panel_w / 1000
    san_luong_ngay = cong_suat_kwp * psh * system_eff

    return {
        "so_tam": so_tam,
        "cong_suat_kwp": round(cong_suat_kwp, 2),
        "san_luong_ngay_kwh": round(san_luong_ngay, 2),
        "san_luong_thang_kwh": round(san_luong_ngay * DAYS_PER_MONTH, 1),
    }
