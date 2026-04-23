import re
from typing import List, Tuple, Dict, Optional
from config import BIEU_GIA_DIEN, VAT_RATE

# Số ngày dùng để quy đổi kWh/ngày → kWh/tháng
DAYS_PER_MONTH = 30


# PHÁT HIỆN CÂU HỎI TÍNH TIỀN ĐIỆN 

_KWH_PATTERN = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(?:k\s*wh|kwh|chữ\s+điện|chữ|số\s+điện)\b",
    re.IGNORECASE,
)

_MONEY_KEYWORDS = (
    "tiền", "hết", "bao nhiêu", "hóa đơn", "phải trả",
    "chi phí", "tính tiền", "phải đóng", "tốn",
)

_KWH_BOUND_MAX = 10_000.0


def trich_kwh_tu_cau_hoi(cau_hoi: str) -> Optional[float]:
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


# VALIDATE ĐỊNH DẠNG THÁNG (MM/YYYY)

_THANG_PATTERN = re.compile(r"^(0?[1-9]|1[0-2])/20\d{2}$")


def thang_hop_le(s: str) -> bool:
    if not s:
        return False
    return bool(_THANG_PATTERN.match(s.strip()))


# TÍNH TIỀN ĐIỆN BẬC THANG
def tinh_tien_dien(kwh: float) -> Tuple[List[dict], float, float, float]:
    if kwh < 0:
        raise ValueError(f"Số kWh phải >= 0, nhận được {kwh}")

    chi_tiet = []
    tong = 0.0
    kwh_con_lai = float(kwh)

    for bg in BIEU_GIA_DIEN:
        if kwh_con_lai <= 0:
            break

        if bg["den"] is None:
            so_luong = kwh_con_lai
        else:

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



# TÍNH CONFIDENCE SCORE

def tinh_confidence(l2_sq: float) -> float:
    return max(0.0, min(1.0, 1.0 - l2_sq / 2.0))



# ĐỊNH DẠNG TIỀN TỆ

def dinh_dang_tien(so: float) -> str:
    return f"{int(so):,} đ"


# TÍNH kWh/THÁNG CỦA THIẾT BỊ

def tinh_kwh_thang(
    power_kw: Optional[float],
    qty: int,
    hours: float,
    kwh_per_day_fixed: Optional[float] = None,
) -> float:
    if qty <= 0:
        return 0.0

    if kwh_per_day_fixed is not None:
        kwh = qty * kwh_per_day_fixed * DAYS_PER_MONTH
    elif power_kw is not None:
        kwh = qty * power_kw * hours * DAYS_PER_MONTH
    else:
        return 0.0

    return round(kwh, 1)


# TÍNH TIẾT KIỆM KHI TÁCH HỘ

def tinh_tiet_kiem_tach_ho(
    kwh_tong: float, so_ho: int
) -> Tuple[float, float, float, float]:
    if so_ho < 1:
        raise ValueError(f"Số hộ phải >= 1, nhận được {so_ho}")

    _, _, _, tong_1_ho = tinh_tien_dien(kwh_tong)

    kwh_moi_ho = kwh_tong / so_ho
    _, _, _, tong_per_ho = tinh_tien_dien(kwh_moi_ho)
    tong_nhieu_ho = tong_per_ho * so_ho

    tiet_kiem = tong_1_ho - tong_nhieu_ho
    phan_tram = (tiet_kiem / tong_1_ho * 100) if tong_1_ho > 0 else 0.0

    return tong_1_ho, tong_nhieu_ho, tiet_kiem, phan_tram


# PHÂN CHIA ĐIỆN MẶT TRỜI: TỰ DÙNG vs BÁN LẠI EVN

def tinh_tu_dung_va_ban_lai(
    san_luong_kwh: float,
    tu_dung_rate: float,
    tieu_thu_kwh: float,
) -> Tuple[float, float]:

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
