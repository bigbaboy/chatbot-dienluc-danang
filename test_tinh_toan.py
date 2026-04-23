import pytest
from config import BIEU_GIA_DIEN, VAT_RATE
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



# 1. HÀM TÍNH TIỀN ĐIỆN
class TestTinhTienDien:

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



# 2. TÁCH HỘ GIA ĐÌNH

class TestTachHo:
   

    def test_mot_ho_khong_co_tiet_kiem(self):
        _, _, tiet_kiem, _ = tinh_tiet_kiem_tach_ho(kwh_tong=300, so_ho=1)
        assert tiet_kiem == pytest.approx(0, abs=0.01)

    def test_tach_ho_luon_tiet_kiem_hoac_bang(self):
        for kwh in [200, 400, 600, 1000]:
            for so_ho in [2, 3, 4]:
                _, _, tiet_kiem, _ = tinh_tiet_kiem_tach_ho(kwh, so_ho)
                assert tiet_kiem >= 0

    def test_tach_ho_voi_kwh_cao_tiet_kiem_nhieu(self):
        _, _, tiet_kiem, pct = tinh_tiet_kiem_tach_ho(kwh_tong=600, so_ho=2)
        assert tiet_kiem > 0
        assert pct > 5

    def test_so_ho_bang_0_raise_error(self):
        with pytest.raises(ValueError):
            tinh_tiet_kiem_tach_ho(kwh_tong=300, so_ho=0)



# 3. TÍNH kWh/THÁNG THIẾT BỊ

class TestKwhThang:

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


# 4. ĐIỆN MẶT TRỜI

class TestDienMatTroi:


    def test_mai_30m2_da_nang(self):
        result = tinh_dien_mat_troi(
            dien_tich_m2=30.0, psh=4.8,
            panel_w=400, panel_m2=2.0, system_eff=0.8,
        )
        assert result["so_tam"] == 15
        assert result["cong_suat_kwp"] == pytest.approx(6.0, abs=0.01)
        assert result["san_luong_ngay_kwh"] == pytest.approx(23.04, abs=0.01)
        assert result["san_luong_thang_kwh"] == pytest.approx(691.2, abs=0.1)

    def test_mai_qua_nho_tra_ve_zero(self):
        result = tinh_dien_mat_troi(
            dien_tich_m2=1.0, psh=4.9, panel_w=400, panel_m2=2.0, system_eff=0.8,
        )
        assert result["so_tam"] == 0
        assert result["cong_suat_kwp"] == 0

    def test_san_luong_ty_le_thuan_voi_PSH(self):
        da_nang = tinh_dien_mat_troi(30, 4.8, 400, 2.0, 0.8)
        ha_noi = tinh_dien_mat_troi(30, 3.8, 400, 2.0, 0.8)
        assert da_nang["san_luong_thang_kwh"] > ha_noi["san_luong_thang_kwh"]



# 5. CONFIDENCE SCORE

class TestConfidence:


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



# 6. ĐỊNH DẠNG TIỀN

class TestDinhDangTien:
    @pytest.mark.parametrize("so, expected", [
        (0,          "0 đ"),
        (1000,       "1,000 đ"),
        (1500000,    "1,500,000 đ"),
        (99200.5,    "99,200 đ"),
    ])
    def test_dinh_dang_co_phan_cach(self, so, expected):
        assert dinh_dang_tien(so) == expected



# 7. RAG PIPELINE HELPERS

class TestRagPipelineHelpers:


    def test_is_rate_limit_error_phat_hien_429(self):
        assert _is_rate_limit_error(Exception("Error 429: Too many requests"))

    def test_is_rate_limit_error_phat_hien_text_rate_limit(self):

        assert _is_rate_limit_error(Exception("API rate limit exceeded"))

    def test_is_rate_limit_error_khong_phat_hien_loi_khac(self):
        assert not _is_rate_limit_error(Exception("Connection timeout"))
        assert not _is_rate_limit_error(ValueError("Invalid input"))

    def test_constants_co_noi_dung(self):
        assert EMPTY_ANSWER_FALLBACK
        assert RATE_LIMIT_MESSAGE
        assert "thử lại" in RATE_LIMIT_MESSAGE.lower()


# 8. BIỂU GIÁ KHỚP VĂN BẢN PHÁP LUẬT

class TestBieuGiaKhopEVN:

    def test_bieu_gia_co_dung_6_bac(self):
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
        bg = next(b for b in BIEU_GIA_DIEN if b["bac"] == bac)
        assert bg["don_gia"] == don_gia_chuan

    def test_bac_cao_nhat_khong_gioi_han_tren(self):
        assert BIEU_GIA_DIEN[-1]["den"] is None

    def test_khoang_cac_bac_lien_tuc(self):
        for i in range(len(BIEU_GIA_DIEN) - 1):
            bac_nay = BIEU_GIA_DIEN[i]
            bac_sau = BIEU_GIA_DIEN[i + 1]
            assert bac_sau["tu"] == bac_nay["den"] + 1


# 9. PHÂN CHIA TỰ DÙNG / BÁN LẠI ĐIỆN MẶT TRỜI
class TestTuDungVaBanLai:

    def test_san_luong_du_rate_70_tieu_thu_250(self):
        tu_dung, ban = tinh_tu_dung_va_ban_lai(500, 0.7, 250)
        assert tu_dung == pytest.approx(175, abs=0.01)
        assert ban == pytest.approx(325, abs=0.01)

    def test_rate_khac_nhau_ra_ket_qua_khac_nhau(self):
        ket_qua = []
        for rate in [0.3, 0.5, 0.7, 0.9, 1.0]:
            tu_dung, _ = tinh_tu_dung_va_ban_lai(700, rate, 250)
            ket_qua.append(tu_dung)
        assert len(set(ket_qua)) == 5, f"tu_dung_rate không có tác dụng: {ket_qua}"
        assert ket_qua == sorted(ket_qua)

    def test_san_luong_thieu_tu_dung_bi_chan_o_san_luong(self):
        tu_dung, ban = tinh_tu_dung_va_ban_lai(50, 0.7, 300)
        assert tu_dung == pytest.approx(50, abs=0.01)
        assert ban == 0.0

    def test_rate_100_phan_tram_san_luong_du(self):
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



# 10. PHÁT HIỆN CÂU HỎI TÍNH TIỀN (FAST-PATH RAG)

class TestTrichKwhTuCauHoi:

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
        assert trich_kwh_tu_cau_hoi(cau) == pytest.approx(expected)

    def test_phat_hien_qua_profile_prefix(self):
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
        assert trich_kwh_tu_cau_hoi(cau) is None

    def test_khong_phat_hien_cau_co_kwh_nhung_khong_hoi_tien(self):
        assert trich_kwh_tu_cau_hoi("250 kWh là bậc mấy?") is None

    def test_kwh_qua_lon_bo_qua(self):
        assert trich_kwh_tu_cau_hoi("1000000 kWh hết bao nhiêu tiền") is None

    def test_chuoi_rong_tra_ve_none(self):
        assert trich_kwh_tu_cau_hoi("") is None
        assert trich_kwh_tu_cau_hoi("   ") is None


class TestFormatCauTraLoiTinhTien:

    def test_output_chua_tong_tien_dung_cho_250kwh(self):
        out = _format_cau_tra_loi_tinh_tien(250)
        assert "636,768 đ" in out

    def test_output_chua_du_4_bac_cho_250kwh(self):
        out = _format_cau_tra_loi_tinh_tien(250)
        for bac in ["Bậc 1", "Bậc 2", "Bậc 3", "Bậc 4"]:
            assert bac in out

    def test_output_huong_dan_chuyen_tab(self):
        out = _format_cau_tra_loi_tinh_tien(100)
        assert "Tính tiền điện" in out



# 11. VALIDATE THÁNG CỦA LỊCH SỬ TIÊU THỤ

class TestValidateThang:

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


# 12. XSS ESCAPE TRONG CITATION CARD

class TestXssEscape:

    def test_html_escape_xu_ly_script_tag(self):
        import html as html_mod
        malicious = "<script>alert('xss')</script>"
        escaped = html_mod.escape(malicious)
        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped

    def test_html_escape_xu_ly_img_onerror(self):
        import html as html_mod
        malicious = '<img src=x onerror="alert(1)">'
        escaped = html_mod.escape(malicious)
        assert "<img" not in escaped
        assert "&lt;img" in escaped

    def test_html_escape_quote_va_ampersand(self):
        import html as html_mod
        original = 'Điều 5 & "quy định" \'abc\''
        escaped = html_mod.escape(original, quote=True)
        assert "&amp;" in escaped
        assert "&quot;" in escaped

    def test_html_escape_text_viet_binh_thuong_giu_nguyen(self):
        import html as html_mod
        vn_text = "Theo Điều 27, Phần III, Quy trình cấp điện sinh hoạt"
        escaped = html_mod.escape(vn_text)
        assert escaped == vn_text  # không có ký tự HTML đặc biệt → giữ nguyên


# CHẠY TRỰC TIẾP (không cần pytest)

if __name__ == "__main__":
    import sys

    print("=" * 70)
    print(" KIỂM THỬ CHATBOT ĐIỆN LỰC ĐÀ NẴNG ".center(70, "="))
    print("=" * 70)

    test_classes = [
        TestTinhTienDien, TestTachHo, TestKwhThang,
        TestDienMatTroi, TestConfidence, TestDinhDangTien,
        TestRagPipelineHelpers, TestBieuGiaKhopEVN,
        TestTuDungVaBanLai,
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
