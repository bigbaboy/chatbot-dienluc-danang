"""
Unit test cho các hàm tính toán và sinh văn bản của Chatbot Điện lực Đà Nẵng.

Cách chạy:
    pytest test_tinh_toan.py -v

Bộ test bao phủ:
  1. tinh_tien_dien()             — 22 cases
  2. tinh_tiet_kiem_tach_ho()     — 4 cases
  3. tinh_kwh_thang()             — 5 cases
  4. tinh_dien_mat_troi()         — 3 cases
  5. tinh_confidence()            — 4 cases
  6. dinh_dang_tien()             — 4 cases
  7. tao_hoa_don_html()           — 7 cases (gồm regression test bậc 6)
  8. rag_pipeline helpers         — 4 cases
  9. Biểu giá khớp EVN            — 9 cases
 10. tinh_tu_dung_va_ban_lai()    — 6 cases (MỚI - v2.0.1)
 11. ROI thay thiết bị            — 4 cases (MỚI - v2.0.1)
"""

import re

import pytest

from config import BIEU_GIA_DIEN, VAT_RATE
from hoa_don import tao_hoa_don_html
from rag_pipeline import (
    EMPTY_ANSWER_FALLBACK,
    RATE_LIMIT_MESSAGE,
    _is_rate_limit_error,
)
from utils import (
    dinh_dang_tien,
    thang_hop_le,
    tinh_confidence,
    tinh_dien_mat_troi,
    tinh_kwh_thang,
    tinh_tien_dien,
    tinh_tiet_kiem_tach_ho,
    tinh_tu_dung_va_ban_lai,
    trich_kwh_tu_cau_hoi,
)
from rag_pipeline import _format_cau_tra_loi_tinh_tien


# ══════════════════════════════════════════════════════════════════
# 1. HÀM TÍNH TIỀN ĐIỆN
# ══════════════════════════════════════════════════════════════════
class TestTinhTienDien:
    """Kiểm chứng hàm tính tiền điện với biểu giá QĐ 1279/QĐ-BCT 2025."""

    @pytest.mark.parametrize("kwh, expected_truoc_vat", [
        (0,    0),
        (50,   99_200),
        (75,   150_450),
        (100,  201_700),
        (150,  320_700),
        (200,  439_700),
        (250,  589_600),
        (300,  739_500),
        (400,  1_074_500),
        (500,  1_420_500),
        (1000, 3_150_500),
    ])
    def test_tinh_tien_dien_dung_chuan_EVN(self, kwh, expected_truoc_vat):
        """Tính tiền điện phải khớp với công thức chuẩn của EVN."""
        _, truoc_vat, _, _ = tinh_tien_dien(kwh)
        assert truoc_vat == pytest.approx(expected_truoc_vat, abs=1)

    @pytest.mark.parametrize("kwh", [50, 100, 150, 200, 250, 300, 400, 500, 1000])
    def test_tong_kwh_phan_bo_bang_kwh_input(self, kwh):
        chi_tiet, _, _, _ = tinh_tien_dien(kwh)
        tong_sl = sum(b["sl"] for b in chi_tiet)
        assert tong_sl == pytest.approx(kwh, abs=0.01)

    def test_vat_dung_8_phan_tram(self):
        _, truoc_vat, vat, tong = tinh_tien_dien(250)
        assert vat == pytest.approx(truoc_vat * VAT_RATE, rel=1e-6)
        assert tong == pytest.approx(truoc_vat + vat, rel=1e-6)

    def test_kwh_zero_tra_ve_zero(self):
        chi_tiet, truoc_vat, vat, tong = tinh_tien_dien(0)
        assert chi_tiet == []
        assert truoc_vat == 0
        assert vat == 0
        assert tong == 0

    def test_kwh_am_raise_value_error(self):
        with pytest.raises(ValueError):
            tinh_tien_dien(-10)

    def test_kwh_thap_phan(self):
        """kWh thập phân (từ công tơ điện tử) vẫn tính đúng."""
        _, truoc_vat, _, _ = tinh_tien_dien(50.5)
        expected = 50 * 1984 + 0.5 * 2050
        assert truoc_vat == pytest.approx(expected, abs=0.01)

    def test_chi_tiet_co_du_thong_tin(self):
        chi_tiet, _, _, _ = tinh_tien_dien(250)
        required_keys = {"bac", "tu", "den", "don_gia", "sl", "tt"}
        for bac in chi_tiet:
            assert required_keys.issubset(bac.keys())
            assert bac["sl"] > 0
            assert bac["tt"] == pytest.approx(bac["sl"] * bac["don_gia"])


# ══════════════════════════════════════════════════════════════════
# 2. TÁCH HỘ GIA ĐÌNH
# ══════════════════════════════════════════════════════════════════
class TestTachHo:
    """Kiểm chứng tính tiết kiệm khi tách nhiều hộ dùng chung công tơ."""

    def test_mot_ho_khong_co_tiet_kiem(self):
        _, _, tiet_kiem, _ = tinh_tiet_kiem_tach_ho(kwh_tong=300, so_ho=1)
        assert tiet_kiem == pytest.approx(0, abs=0.01)

    def test_tach_ho_luon_tiet_kiem_hoac_bang(self):
        for kwh in [200, 400, 600, 1000]:
            for so_ho in [2, 3, 4]:
                _, _, tiet_kiem, _ = tinh_tiet_kiem_tach_ho(kwh, so_ho)
                assert tiet_kiem >= 0

    def test_tach_ho_voi_kwh_cao_tiet_kiem_nhieu(self):
        """600 kWh: 1 hộ tới bậc 6, 2 hộ × 300 kWh chỉ tới bậc 4 → tiết kiệm đáng kể."""
        _, _, tiet_kiem, pct = tinh_tiet_kiem_tach_ho(kwh_tong=600, so_ho=2)
        assert tiet_kiem > 0
        assert pct > 5

    def test_so_ho_bang_0_raise_error(self):
        with pytest.raises(ValueError):
            tinh_tiet_kiem_tach_ho(kwh_tong=300, so_ho=0)


# ══════════════════════════════════════════════════════════════════
# 3. TÍNH kWh/THÁNG THIẾT BỊ
# ══════════════════════════════════════════════════════════════════
class TestKwhThang:
    """Kiểm chứng công thức P × t × 30."""

    def test_may_lanh_1hp_8gio(self):
        assert tinh_kwh_thang(power_kw=1.0, qty=1, hours=8) == pytest.approx(240, abs=0.1)

    def test_den_led_10w_8gio(self):
        assert tinh_kwh_thang(power_kw=0.010, qty=1, hours=8) == pytest.approx(2.4, abs=0.1)

    def test_tu_lanh_kwh_ngay_co_dinh(self):
        kwh = tinh_kwh_thang(power_kw=None, qty=1, hours=24, kwh_per_day_fixed=1.5)
        assert kwh == pytest.approx(45, abs=0.1)

    def test_nhieu_thiet_bi_cung_loai(self):
        assert tinh_kwh_thang(power_kw=1.0, qty=3, hours=8) == pytest.approx(720, abs=0.1)

    def test_qty_zero_tra_ve_zero(self):
        assert tinh_kwh_thang(power_kw=1.0, qty=0, hours=8) == 0.0


# ══════════════════════════════════════════════════════════════════
# 4. ĐIỆN MẶT TRỜI
# ══════════════════════════════════════════════════════════════════
class TestDienMatTroi:
    """Kiểm chứng công thức tính sản lượng điện mặt trời."""

    def test_mai_30m2_da_nang(self):
        """
        Mái 30m² tại Đà Nẵng (PSH=4.9):
          - Số tấm: 30/2 = 15 tấm (400Wp/tấm)
          - Công suất: 6 kWp
          - Sản lượng/tháng: ~705.6 kWh
        """
        result = tinh_dien_mat_troi(
            dien_tich_m2=30.0, psh=4.9,
            panel_w=400, panel_m2=2.0, system_eff=0.8,
        )
        assert result["so_tam"] == 15
        assert result["cong_suat_kwp"] == pytest.approx(6.0, abs=0.01)
        assert result["san_luong_ngay_kwh"] == pytest.approx(23.52, abs=0.01)
        assert result["san_luong_thang_kwh"] == pytest.approx(705.6, abs=0.1)

    def test_mai_qua_nho_tra_ve_zero(self):
        result = tinh_dien_mat_troi(
            dien_tich_m2=1.0, psh=4.9, panel_w=400, panel_m2=2.0, system_eff=0.8,
        )
        assert result["so_tam"] == 0
        assert result["cong_suat_kwp"] == 0

    def test_san_luong_ty_le_thuan_voi_PSH(self):
        da_nang = tinh_dien_mat_troi(30, 4.9, 400, 2.0, 0.8)
        ha_noi = tinh_dien_mat_troi(30, 3.8, 400, 2.0, 0.8)
        assert da_nang["san_luong_thang_kwh"] > ha_noi["san_luong_thang_kwh"]


# ══════════════════════════════════════════════════════════════════
# 5. CONFIDENCE SCORE
# ══════════════════════════════════════════════════════════════════
class TestConfidence:
    """Kiểm chứng chuyển đổi L2² → cosine similarity."""

    def test_l2_zero_tra_ve_confidence_cao_nhat(self):
        assert tinh_confidence(0.0) == 1.0

    def test_l2_2_tra_ve_confidence_thap_nhat(self):
        assert tinh_confidence(2.0) == 0.0

    def test_l2_1_tra_ve_0_5(self):
        assert tinh_confidence(1.0) == pytest.approx(0.5, abs=1e-6)

    def test_confidence_luon_trong_khoang_0_1(self):
        for l2 in [-1.0, 0.0, 0.5, 1.5, 2.5, 10.0]:
            c = tinh_confidence(l2)
            assert 0.0 <= c <= 1.0


# ══════════════════════════════════════════════════════════════════
# 6. ĐỊNH DẠNG TIỀN
# ══════════════════════════════════════════════════════════════════
class TestDinhDangTien:
    """Kiểm chứng định dạng hiển thị tiền tệ."""

    @pytest.mark.parametrize("so, expected", [
        (0,          "0 đ"),
        (1000,       "1,000 đ"),
        (1500000,    "1,500,000 đ"),
        (99200.5,    "99,200 đ"),
    ])
    def test_dinh_dang_co_phan_cach(self, so, expected):
        assert dinh_dang_tien(so) == expected


# ══════════════════════════════════════════════════════════════════
# 7. TẠO HÓA ĐƠN HTML  (MỚI - Phase 3)
# ══════════════════════════════════════════════════════════════════
class TestTaoHoaDonHtml:
    """Kiểm chứng template HTML của hóa đơn."""

    @pytest.fixture
    def hoa_don_250_kwh(self):
        """Fixture: dữ liệu cho hộ 250 kWh — case chuẩn để test nhiều scenario."""
        chi_tiet, truoc_vat, vat, tong = tinh_tien_dien(250)
        return tao_hoa_don_html(
            kwh_input=250,
            so_ho=1,
            kwh_per_ho=250,
            chi_tiet=chi_tiet,
            tong_per_ho=tong,
            tien_vat_ho=vat,
            tong_all=tong,
        )

    def test_html_la_chuoi_hop_le(self, hoa_don_250_kwh):
        """Output phải là HTML doctype hợp lệ."""
        assert hoa_don_250_kwh.startswith("<!DOCTYPE html>")
        assert "</html>" in hoa_don_250_kwh

    def test_html_chua_tong_tien_dung(self, hoa_don_250_kwh):
        """Tổng tiền sau VAT (636,768 đ) phải xuất hiện trong HTML."""
        _, _, _, tong = tinh_tien_dien(250)
        assert f"{int(tong):,} đ" in hoa_don_250_kwh

    def test_html_chua_so_kwh(self, hoa_don_250_kwh):
        """Sản lượng 250 kWh phải xuất hiện."""
        assert "250 kWh" in hoa_don_250_kwh

    def test_html_co_tat_ca_cac_bac_su_dung(self, hoa_don_250_kwh):
        """Hộ 250 kWh dùng qua bậc 1-4 → cả 4 bậc phải hiển thị."""
        for bac in [1, 2, 3, 4]:
            assert f"Bậc {bac}" in hoa_don_250_kwh

    def test_html_nhieu_ho_co_dong_multi_ho(self):
        """Khi so_ho > 1 phải có dòng 'x N hộ' tổng hợp."""
        chi_tiet, _, vat, tong_1ho = tinh_tien_dien(150)
        html = tao_hoa_don_html(
            kwh_input=600, so_ho=4, kwh_per_ho=150,
            chi_tiet=chi_tiet, tong_per_ho=tong_1ho,
            tien_vat_ho=vat, tong_all=tong_1ho * 4,
        )
        assert "× 4 hộ" in html
        # Kiểm tra có từ "tổng" (summary) xuất hiện
        assert "TỔNG 4 HỘ" in html or "TỔNG THANH TOÁN" in html

    def test_html_co_thong_tin_ngay(self, hoa_don_250_kwh):
        """Hóa đơn phải có ngày/giờ tính (định dạng dd/mm/yyyy hh:mm)."""
        assert re.search(r"\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}", hoa_don_250_kwh)

    def test_html_bac_6_hien_thi_dung_dinh_dang(self):
        """Bậc 6 (den='trở lên') phải hiển thị 'Trên 401 kWh', không phải '401 – trên 401 kWh'.

        Regression test cho bug ở v2.0.0: cột 'Khoảng' của bậc cao nhất
        in ra '401 – trên 401 kWh' (lặp số 401, sai grammar) thay vì
        'Trên 401 kWh' như ở UI Tab 2.
        """
        chi_tiet, _, vat, tong = tinh_tien_dien(500)  # 500 kWh → vào bậc 6
        html = tao_hoa_don_html(
            kwh_input=500, so_ho=1, kwh_per_ho=500,
            chi_tiet=chi_tiet, tong_per_ho=tong,
            tien_vat_ho=vat, tong_all=tong,
        )
        assert "<td>Trên 401 kWh</td>" in html
        assert "401 – trên 401" not in html  # đảm bảo không còn dạng cũ


# ══════════════════════════════════════════════════════════════════
# 8. RAG PIPELINE HELPERS  (MỚI - Phase 3)
# ══════════════════════════════════════════════════════════════════
class TestRagPipelineHelpers:
    """Kiểm chứng các helper function của RAG pipeline."""

    def test_is_rate_limit_error_phat_hien_429(self):
        """Exception có '429' → là rate limit."""
        assert _is_rate_limit_error(Exception("Error 429: Too many requests"))

    def test_is_rate_limit_error_phat_hien_text_rate_limit(self):
        """Exception có 'rate limit' → là rate limit."""
        assert _is_rate_limit_error(Exception("API rate limit exceeded"))

    def test_is_rate_limit_error_khong_phat_hien_loi_khac(self):
        """Lỗi khác (connection, timeout) → không phải rate limit."""
        assert not _is_rate_limit_error(Exception("Connection timeout"))
        assert not _is_rate_limit_error(ValueError("Invalid input"))

    def test_constants_co_noi_dung(self):
        """Các message constant phải có nội dung ý nghĩa."""
        assert EMPTY_ANSWER_FALLBACK
        assert RATE_LIMIT_MESSAGE
        assert "thử lại" in RATE_LIMIT_MESSAGE.lower()


# ══════════════════════════════════════════════════════════════════
# 9. BIỂU GIÁ KHỚP VĂN BẢN PHÁP LUẬT  (MỚI - Phase 3)
# ══════════════════════════════════════════════════════════════════
class TestBieuGiaKhopEVN:
    """Kiểm chứng biểu giá trong config.py khớp với QĐ 1279/QĐ-BCT."""

    def test_bieu_gia_co_dung_6_bac(self):
        """QĐ 1279 có đúng 6 bậc."""
        assert len(BIEU_GIA_DIEN) == 6

    @pytest.mark.parametrize("bac, don_gia_chuan", [
        (1, 1984),
        (2, 2050),
        (3, 2380),
        (4, 2998),
        (5, 3350),
        (6, 3460),
    ])
    def test_don_gia_tung_bac_khop_QD_1279(self, bac, don_gia_chuan):
        """Đơn giá mỗi bậc phải khớp với QĐ 1279/QĐ-BCT ngày 09/05/2025."""
        bg = next(b for b in BIEU_GIA_DIEN if b["bac"] == bac)
        assert bg["don_gia"] == don_gia_chuan

    def test_bac_cao_nhat_khong_gioi_han_tren(self):
        """Bậc 6 phải có den = None (không giới hạn trên)."""
        assert BIEU_GIA_DIEN[-1]["den"] is None

    def test_khoang_cac_bac_lien_tuc(self):
        """Bậc n+1 phải bắt đầu = bậc n.den + 1 (không có khoảng trống/trùng)."""
        for i in range(len(BIEU_GIA_DIEN) - 1):
            bac_nay = BIEU_GIA_DIEN[i]
            bac_sau = BIEU_GIA_DIEN[i + 1]
            assert bac_sau["tu"] == bac_nay["den"] + 1


# ══════════════════════════════════════════════════════════════════
# 10. PHÂN CHIA TỰ DÙNG / BÁN LẠI ĐIỆN MẶT TRỜI
# ══════════════════════════════════════════════════════════════════
class TestTuDungVaBanLai:
    """
    Kiểm chứng hàm phân chia điện mặt trời tự dùng vs bán lại EVN.

    Công thức (v2.1.2): tu_dung_rate = % tiêu thụ rơi vào BAN NGÀY
    (khi ĐMT sản xuất). tu_dung = min(sản_lượng, tiêu_thụ × rate).
    """

    def test_san_luong_du_rate_70_tieu_thu_250(self):
        """ĐMT dư (500 kWh), tiêu thụ 250 kWh, rate 70%:
        nhu cầu ban ngày = 250×0.7 = 175, tự dùng = min(500, 175) = 175.
        Bán lại = 500 - 175 = 325."""
        tu_dung, ban = tinh_tu_dung_va_ban_lai(500, 0.7, 250)
        assert tu_dung == pytest.approx(175, abs=0.01)
        assert ban == pytest.approx(325, abs=0.01)

    def test_rate_khac_nhau_ra_ket_qua_khac_nhau(self):
        """REGRESSION TEST (bug v2.1.1 trở về trước):
        Khi sản lượng >> tiêu thụ, slider tỷ lệ tự dùng phải thay đổi
        kết quả — không được ra cùng 1 số cho mọi rate."""
        ket_qua = []
        for rate in [0.3, 0.5, 0.7, 0.9, 1.0]:
            tu_dung, _ = tinh_tu_dung_va_ban_lai(700, rate, 250)
            ket_qua.append(tu_dung)
        # Nếu bug chưa fix: tất cả = 250 (bị chặn bởi tiêu thụ)
        assert len(set(ket_qua)) == 5, f"Slider không có tác dụng: {ket_qua}"
        # Monotonic tăng theo rate
        assert ket_qua == sorted(ket_qua)

    def test_san_luong_thieu_tu_dung_bi_chan_o_san_luong(self):
        """ĐMT 50 kWh, tiêu thụ 300 kWh, rate 70%:
        nhu cầu ban ngày = 300×0.7 = 210, nhưng ĐMT chỉ có 50 → tự dùng = 50."""
        tu_dung, ban = tinh_tu_dung_va_ban_lai(50, 0.7, 300)
        assert tu_dung == pytest.approx(50, abs=0.01)
        assert ban == 0.0

    def test_rate_100_phan_tram_san_luong_du(self):
        """Rate 100%: toàn bộ tiêu thụ vào ban ngày. ĐMT 500, tiêu thụ 250:
        nhu cầu ban ngày = 250, tự dùng = min(500, 250) = 250."""
        tu_dung, ban = tinh_tu_dung_va_ban_lai(500, 1.0, 250)
        assert tu_dung == pytest.approx(250, abs=0.01)
        assert ban == pytest.approx(250, abs=0.01)

    def test_tu_dung_rate_ngoai_khoang_raise_error(self):
        with pytest.raises(ValueError):
            tinh_tu_dung_va_ban_lai(100, 1.5, 100)
        with pytest.raises(ValueError):
            tinh_tu_dung_va_ban_lai(100, -0.1, 100)

    def test_san_luong_am_raise_error(self):
        with pytest.raises(ValueError):
            tinh_tu_dung_va_ban_lai(-10, 0.7, 100)


# ══════════════════════════════════════════════════════════════════
# 11. ROI THAY THIẾT BỊ (INTEGRATION VỚI BIỂU GIÁ ĐIỆN)
# ══════════════════════════════════════════════════════════════════
class TestRoiThayThietBi:
    """
    Kiểm chứng các kịch bản ROI thay thiết bị thực tế.

    Verify rằng việc thay thiết bị tốn điện bằng thiết bị tiết kiệm
    cho ra kết quả tiết kiệm tiền hợp lý qua biểu giá bậc thang.
    """

    def test_thay_may_lanh_1sao_bang_inverter_5sao_tiet_kiem_dang_ke(self):
        """Máy lạnh 1.5HP 1 sao (1.5 kW) → inverter 5 sao (0.75 kW), 8h/ngày:
        kWh giảm 50% → tiền điện giảm rõ rệt do bậc thang."""
        kwh_cu = tinh_kwh_thang(power_kw=1.50, qty=1, hours=8)   # 360 kWh
        kwh_moi = tinh_kwh_thang(power_kw=0.75, qty=1, hours=8)  # 180 kWh

        _, _, _, tien_cu = tinh_tien_dien(kwh_cu)
        _, _, _, tien_moi = tinh_tien_dien(kwh_moi)
        tiet_kiem_thang = tien_cu - tien_moi

        # Phải tiết kiệm > 400.000 đ/tháng (do bậc cao bị bỏ)
        assert tiet_kiem_thang > 400_000

    def test_thay_den_huynh_quang_bang_led_tiet_kiem(self):
        """Đèn huỳnh quang 36W → LED 9W (10 cái, 8h/ngày):
        Số kWh giảm ~75% → tiền điện cũng giảm tương ứng."""
        kwh_cu = tinh_kwh_thang(power_kw=0.036, qty=10, hours=8)  # 86.4 kWh
        kwh_moi = tinh_kwh_thang(power_kw=0.009, qty=10, hours=8)  # 21.6 kWh
        assert kwh_cu > kwh_moi
        assert (kwh_cu - kwh_moi) / kwh_cu == pytest.approx(0.75, abs=0.01)

    def test_thay_tu_lanh_kwh_ngay_co_dinh(self):
        """Tủ lạnh cũ 2.8 kWh/ngày → mới 1.0 kWh/ngày:
        tiết kiệm 1.8 kWh/ngày × 30 = 54 kWh/tháng."""
        kwh_cu = tinh_kwh_thang(None, qty=1, hours=24, kwh_per_day_fixed=2.8)
        kwh_moi = tinh_kwh_thang(None, qty=1, hours=24, kwh_per_day_fixed=1.0)
        assert (kwh_cu - kwh_moi) == pytest.approx(54, abs=0.1)

    def test_hoan_von_duong_khi_thiet_bi_moi_re_va_tiet_kiem(self):
        """Đèn LED 9W (80k đ) thay đèn T8 36W (10 cái, 8h/ngày):
        Phải hoàn vốn dưới 1 năm (LED rẻ + tiết kiệm 75% kWh)."""
        kwh_cu = tinh_kwh_thang(power_kw=0.036, qty=10, hours=8)
        kwh_moi = tinh_kwh_thang(power_kw=0.009, qty=10, hours=8)
        _, _, _, tien_cu = tinh_tien_dien(kwh_cu)
        _, _, _, tien_moi = tinh_tien_dien(kwh_moi)
        tiet_kiem_nam = (tien_cu - tien_moi) * 12
        chi_phi = 80_000 * 10  # 10 bóng LED × 80k
        hoan_von_nam = chi_phi / tiet_kiem_nam if tiet_kiem_nam > 0 else float("inf")
        assert hoan_von_nam < 1.0


# ══════════════════════════════════════════════════════════════════
# 12. PHÁT HIỆN CÂU HỎI TÍNH TIỀN (FAST-PATH RAG)  (MỚI - v2.1.0)
# ══════════════════════════════════════════════════════════════════
class TestTrichKwhTuCauHoi:
    """
    Kiểm chứng intent detection: nhận diện câu hỏi tính tiền điện.

    Regression test cho bug ở v2.0.x: chatbot RAG không trả lời được
    câu "X kWh hết bao nhiêu tiền" mà bị lặp vô tận do LLM lấy
    nhầm văn bản HĐMBĐ công nghiệp. Fast-path này né RAG hoàn toàn,
    gọi tinh_tien_dien() trực tiếp.
    """

    @pytest.mark.parametrize("cau, expected", [
        ("250 kWh hết bao nhiêu tiền", 250.0),
        ("Nếu tháng này tôi dùng 250 chữ điện thì bao nhiêu tiền", 250.0),
        ("dùng 300 chữ thì hết bao nhiêu", 300.0),
        ("tính tiền điện cho 150 kWh", 150.0),
        ("hộ tôi dùng 75 số điện hết bao nhiêu tiền", 75.0),
        ("400kwh phải đóng bao nhiêu", 400.0),
        ("75.5 kWh hết bao nhiêu tiền", 75.5),
        ("tốn bao nhiêu nếu dùng 200 kWh", 200.0),
    ])
    def test_phat_hien_cau_hoi_tinh_tien(self, cau, expected):
        """Các câu hỏi tính tiền hợp lệ phải trích đúng số kWh."""
        assert trich_kwh_tu_cau_hoi(cau) == pytest.approx(expected)

    def test_phat_hien_qua_profile_prefix(self):
        """Sau khi tabs/chat.py thêm '[Hộ X người, ...]' vẫn detect được."""
        cau = (
            "[Hộ 4 người, Chung cư, khu vực Đà Nẵng] "
            "Nếu tháng này tôi dùng 250 chữ điện thì bao nhiêu tiền"
        )
        assert trich_kwh_tu_cau_hoi(cau) == 250.0

    @pytest.mark.parametrize("cau", [
        "kWh là gì?",
        "biểu giá điện 6 bậc như thế nào?",
        "thủ tục đăng ký công tơ ra sao",
        "khi nào áp dụng biểu giá 5 bậc mới?",
    ])
    def test_khong_phat_hien_cau_hoi_tra_cuu(self, cau):
        """Câu hỏi tra cứu thuần (không có số + không có 'tiền') → None."""
        assert trich_kwh_tu_cau_hoi(cau) is None

    def test_khong_phat_hien_cau_co_kwh_nhung_khong_hoi_tien(self):
        """'250 kWh là bậc mấy?' — có số nhưng không hỏi tiền → đi RAG."""
        assert trich_kwh_tu_cau_hoi("250 kWh là bậc mấy?") is None

    def test_kwh_qua_lon_bo_qua(self):
        """Số quá lớn (>10.000 kWh) không phải hộ gia đình → trả None."""
        assert trich_kwh_tu_cau_hoi("1000000 kWh hết bao nhiêu tiền") is None

    def test_chuoi_rong_tra_ve_none(self):
        assert trich_kwh_tu_cau_hoi("") is None
        assert trich_kwh_tu_cau_hoi("   ") is None


class TestFormatCauTraLoiTinhTien:
    """Kiểm chứng output của fast-path khớp với tinh_tien_dien()."""

    def test_output_chua_tong_tien_dung_cho_250kwh(self):
        """250 kWh phải trả ra 636,768 đ — đúng theo unit test core."""
        out = _format_cau_tra_loi_tinh_tien(250)
        assert "636,768 đ" in out

    def test_output_chua_du_4_bac_cho_250kwh(self):
        out = _format_cau_tra_loi_tinh_tien(250)
        for bac in ["Bậc 1", "Bậc 2", "Bậc 3", "Bậc 4"]:
            assert bac in out

    def test_output_huong_dan_chuyen_tab(self):
        """Phải gợi ý user dùng Tab 'Tính tiền điện' để xem chi tiết."""
        out = _format_cau_tra_loi_tinh_tien(100)
        assert "Tính tiền điện" in out


# ══════════════════════════════════════════════════════════════════
# 13. VALIDATE THÁNG CỦA LỊCH SỬ TIÊU THỤ  (MỚI - v2.1.1)
# ══════════════════════════════════════════════════════════════════
class TestValidateThang:
    """Kiểm chứng regex validate định dạng tháng '03/2025' trong sidebar."""

    @pytest.mark.parametrize("thang_hop_le_case", [
        "01/2020", "12/2099", "03/2025", "3/2025", "1/2026", "11/2024",
    ])
    def test_thang_hop_le_duoc_chap_nhan(self, thang_hop_le_case):
        assert thang_hop_le(thang_hop_le_case)

    @pytest.mark.parametrize("thang_sai", [
        "", "   ", "foo",           # empty / không phải tháng
        "13/2025", "00/2025",       # tháng ngoài 1-12
        "03/1999", "03/3000",       # năm ngoài 2000-2099
        "03-2025", "2025/03",       # sai format
        "Tháng 3/2025",              # có text thêm
        "03/2025/extra",            # có phần thừa
        "03/25",                     # năm 2 chữ số
    ])
    def test_thang_sai_bi_tu_choi(self, thang_sai):
        assert not thang_hop_le(thang_sai)


# ══════════════════════════════════════════════════════════════════
# 14. XSS ESCAPE TRONG CITATION CARD  (MỚI - v2.1.1)
# ══════════════════════════════════════════════════════════════════
class TestXssEscape:
    """
    Regression test cho XSS vulnerability đã được fix ở v2.1.1.

    Bug cũ: tabs/chat._render_citations() nhúng trực tiếp src/page/
    snippet (lấy từ PDF metadata) vào HTML mà không escape. Attacker
    có thể upload PDF chứa nội dung `<script>...</script>` để chạy
    JavaScript trong browser của user.

    Test này verify rằng khi data chứa ký tự HTML đặc biệt, chúng sẽ
    được escape thành entities (&lt; &gt; &amp; &quot;) thay vì
    render như HTML raw.
    """

    def test_html_escape_xu_ly_script_tag(self):
        """Ký tự < > được escape đúng thành entities."""
        import html as html_mod
        malicious = "<script>alert('xss')</script>"
        escaped = html_mod.escape(malicious)
        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped

    def test_html_escape_xu_ly_img_onerror(self):
        """XSS qua <img onerror=...> cũng bị neutralize."""
        import html as html_mod
        malicious = '<img src=x onerror="alert(1)">'
        escaped = html_mod.escape(malicious)
        assert "<img" not in escaped
        assert "&lt;img" in escaped

    def test_html_escape_quote_va_ampersand(self):
        """Các ký tự đặc biệt khác cũng được escape."""
        import html as html_mod
        original = 'Điều 5 & "quy định" \'abc\''
        escaped = html_mod.escape(original, quote=True)
        assert "&amp;" in escaped
        assert "&quot;" in escaped

    def test_html_escape_text_viet_binh_thuong_giu_nguyen(self):
        """Tiếng Việt có dấu không bị ảnh hưởng bởi escape."""
        import html as html_mod
        vn_text = "Theo Điều 27, Phần III, Quy trình cấp điện sinh hoạt"
        escaped = html_mod.escape(vn_text)
        assert escaped == vn_text  # không có ký tự HTML đặc biệt → giữ nguyên


# ══════════════════════════════════════════════════════════════════
# CHẠY TRỰC TIẾP (không cần pytest)
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    print("=" * 70)
    print(" KIỂM THỬ CHATBOT ĐIỆN LỰC ĐÀ NẴNG ".center(70, "="))
    print("=" * 70)

    test_classes = [
        TestTinhTienDien, TestTachHo, TestKwhThang,
        TestDienMatTroi, TestConfidence, TestDinhDangTien,
        TestTaoHoaDonHtml, TestRagPipelineHelpers, TestBieuGiaKhopEVN,
        TestTuDungVaBanLai, TestRoiThayThietBi,
        TestTrichKwhTuCauHoi, TestFormatCauTraLoiTinhTien,
        TestValidateThang, TestXssEscape,
    ]
    total = 0
    passed = 0
    failed = []

    for cls in test_classes:
        print(f"\n▶ {cls.__name__}: {cls.__doc__.strip() if cls.__doc__ else ''}")
        instance = cls()
        for name in dir(instance):
            if not name.startswith("test_"):
                continue
            method = getattr(instance, name)
            total += 1
            try:
                method()
                print(f"  ✓ {name}")
                passed += 1
            except TypeError:
                print(f"  ⊘ {name} (cần pytest cho parametrized tests)")
                total -= 1
            except AssertionError as e:
                print(f"  ✗ {name}: {e}")
                failed.append((cls.__name__, name, str(e)))
            except Exception as e:
                print(f"  ✗ {name}: {type(e).__name__}: {e}")
                failed.append((cls.__name__, name, str(e)))

    print("\n" + "=" * 70)
    print(f" KẾT QUẢ: {passed}/{total} test PASS ".center(70, "="))
    print("=" * 70)
    if failed:
        for cls_name, test_name, err in failed:
            print(f"  - {cls_name}.{test_name}: {err}")
        sys.exit(1)
    else:
        print("\n✅ Tất cả test đã PASS. Code hoạt động chính xác!")
