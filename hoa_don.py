"""
Tạo hóa đơn tiền điện dạng HTML (có thể in ra PDF).

Tách khỏi `app.py` để:
  - Test được output HTML có chứa đúng các con số quan trọng
  - Dễ chỉnh sửa template mà không ảnh hưởng đến logic UI
"""

from __future__ import annotations

from datetime import datetime
from typing import List


def _format_khoang(b: dict) -> str:
    """Định dạng cột 'Khoảng' cho 1 bậc.

    Bậc 6 (den='trở lên') hiển thị 'Trên 401 kWh' thay vì
    '401 – trên 401 kWh' (cách cũ bị lặp số 401 và sai grammar).
    Khớp với cách hiển thị trong UI (tabs/tien_dien.py).
    """
    if b["den"] == "trở lên":
        return f"Trên {b['tu']} kWh"
    return f"{b['tu']} – {b['den']} kWh"


def _row_html(b: dict) -> str:
    """Render 1 dòng bậc thành HTML <tr>."""
    return f"""
        <tr>
            <td>Bậc {b['bac']}</td>
            <td>{_format_khoang(b)}</td>
            <td>{b['don_gia']:,} đ/kWh</td>
            <td>{b['sl']:.1f} kWh</td>
            <td style="text-align:right">{int(b['tt']):,} đ</td>
        </tr>"""


def tao_hoa_don_html(
    kwh_input: float,
    so_ho: int,
    kwh_per_ho: float,
    chi_tiet: List[dict],
    tong_per_ho: float,
    tien_vat_ho: float,
    tong_all: float,
) -> str:
    """
    Tạo hóa đơn tiền điện dạng HTML.

    Args:
        kwh_input: Tổng kWh tiêu thụ
        so_ho: Số hộ
        kwh_per_ho: kWh trung bình mỗi hộ
        chi_tiet: List dict từ tinh_tien_dien() — từng bậc đã tính
        tong_per_ho: Tiền 1 hộ (sau VAT)
        tien_vat_ho: VAT 1 hộ
        tong_all: Tiền tất cả hộ (sau VAT)

    Returns:
        HTML string đầy đủ, có thể save thành .html và mở bằng trình duyệt.
    """
    bacs = [b for b in chi_tiet if b["sl"] > 0]
    ngay = datetime.now().strftime("%d/%m/%Y %H:%M")

    rows_html = "".join(_row_html(b) for b in bacs)

    # Dòng tổng hợp khi tách nhiều hộ — gắn vào cuối bảng
    multi_ho_row = ""
    if so_ho > 1:
        multi_ho_row = f"""
      <tr style="background:#e0f2fe;font-weight:bold">
        <td colspan="4">× {so_ho} hộ (tổng {kwh_input:.0f} kWh)</td>
        <td style="text-align:right">{int(tong_all):,} đ</td>
      </tr>"""

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <title>Hóa đơn tiền điện — {kwh_input:.0f} kWh</title>
  <style>
    body {{
        font-family: "Segoe UI", "Arial", "Noto Sans", "Liberation Sans",
                     "DejaVu Sans", "Helvetica Neue", sans-serif;
        max-width: 720px; margin: 32px auto; padding: 24px;
    }}
    h1 {{ text-align: center; color: #0ea5a0; }}
    .meta {{ color: #64748b; font-size: 13px; margin-bottom: 16px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px; font-size: 13px; }}
    th {{ background: #f1f5f9; text-align: center; }}
    .summary {{ background: #f0fdfa; padding: 12px; border-radius: 6px; margin-top: 16px; }}
    .summary div {{ display: flex; justify-content: space-between; padding: 4px 0; }}
    .total {{ font-size: 16px; font-weight: bold; color: #0ea5a0; border-top: 2px solid #0ea5a0; padding-top: 8px; }}
    .footer {{ text-align: center; color: #94a3b8; font-size: 11px; margin-top: 24px; }}
  </style>
</head>
<body>
  <h1>HÓA ĐƠN TIỀN ĐIỆN (ƯỚC TÍNH)</h1>
  <div class="meta">
    Ngày tính: {ngay}<br>
    Sản lượng: {kwh_input:.0f} kWh ({so_ho} hộ × {kwh_per_ho:.1f} kWh/hộ)
  </div>

  <table>
    <thead>
      <tr>
        <th>Bậc</th>
        <th>Khoảng (kWh)</th>
        <th>Đơn giá</th>
        <th>Sản lượng</th>
        <th>Thành tiền</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}{multi_ho_row}
    </tbody>
  </table>

  <div class="summary">
    <div><span>Tiền điện 1 hộ (trước VAT)</span><span>{int(tong_per_ho - tien_vat_ho):,} đ</span></div>
    <div><span>VAT (8%)</span><span>{int(tien_vat_ho):,} đ</span></div>
    <div><span>Tổng 1 hộ</span><span>{int(tong_per_ho):,} đ</span></div>
    {f'<div class="total"><span>TỔNG {so_ho} HỘ</span><span>{int(tong_all):,} đ</span></div>' if so_ho > 1 else f'<div class="total"><span>TỔNG THANH TOÁN</span><span>{int(tong_per_ho):,} đ</span></div>'}
  </div>

  <div class="footer">
    Hóa đơn ước tính. Số tiền chính thức được ghi nhận trên hóa đơn của EVN.<br>
    Sinh bởi Chatbot Điện lực Đà Nẵng — {ngay}
  </div>
</body>
</html>"""
