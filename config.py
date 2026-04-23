"""
Cấu hình tập trung cho Chatbot Điện lực Đà Nẵng.

Tất cả các file khác import từ module này.
Khi có thay đổi biểu giá điện hoặc cấu hình mô hình AI, chỉ cần sửa ở đây.
"""

import os
import warnings
from dotenv import load_dotenv

# ────────────────────────────────────────────────────────────────
# NẠP BIẾN MÔI TRƯỜNG
# ────────────────────────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


# ────────────────────────────────────────────────────────────────
# ĐƯỜNG DẪN THƯ MỤC
# ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_DIR = os.path.join(BASE_DIR, "faiss_dienluc_db")

os.makedirs(DATA_DIR, exist_ok=True)


# ────────────────────────────────────────────────────────────────
# API KEYS — với validate rõ ràng
# ────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY", "").strip()


def _is_placeholder(key: str) -> bool:
    """Kiểm tra xem API key có phải là placeholder (chưa điền) hay không."""
    if not key:
        return True
    placeholders = ("your_key_here", "xxx", "placeholder")
    return any(p in key.lower() for p in placeholders)


# Trạng thái API key — các file khác dùng để hiển thị cảnh báo
GROQ_KEY_OK = not _is_placeholder(GROQ_API_KEY) and GROQ_API_KEY.startswith("gsk_")
LLAMA_KEY_OK = not _is_placeholder(LLAMA_CLOUD_API_KEY) and LLAMA_CLOUD_API_KEY.startswith("llx-")

if not GROQ_KEY_OK:
    warnings.warn(
        "GROQ_API_KEY chưa được cấu hình hoặc không hợp lệ. "
        "Tạo file .env và thêm: GROQ_API_KEY=gsk_...",
        RuntimeWarning,
    )

# Vẫn set vào environment để các thư viện đọc được
os.environ["GROQ_API_KEY"] = GROQ_API_KEY


# ────────────────────────────────────────────────────────────────
# MÔ HÌNH AI
# ────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
LLM_MODEL = "llama-3.1-8b-instant"
LLM_TEMPERATURE = 0.2  # Thấp = trả lời sát quy định hơn
LLM_MAX_TOKENS = 800   # Giới hạn output để tránh runaway/lặp vô tận
LLM_FREQUENCY_PENALTY = 0.6  # Phạt token đã xuất hiện → giảm lặp đoạn (0..2)


# ────────────────────────────────────────────────────────────────
# CHIA NHỎ TÀI LIỆU (CHUNKING)
# ────────────────────────────────────────────────────────────────
CHUNK_SIZE = 1200       # Đủ lớn để giữ nguyên 1 điều khoản
CHUNK_OVERLAP = 300     # Chồng lấp để không mất ngữ cảnh
SEPARATORS = [
    "\n\n",       # Đoạn văn
    "\n",         # Xuống dòng
    "Phần ",      # Phần I, II, III...
    "Chương ",    # Chương I, II...
    "Mục ",       # Mục 1, 2...
    "Điều ",      # Điều 1, 2, 3...
    "Khoản ",     # Khoản 1, 2...
    ". ",         # Câu
    " ",          # Từ
]


# ────────────────────────────────────────────────────────────────
# TÌM KIẾM VÀ RE-RANKING
# ────────────────────────────────────────────────────────────────
SEARCH_TOP_K = 5       # Số đoạn cuối cùng đưa vào prompt LLM
SEARCH_FETCH_K = 15    # Lấy nhiều hơn để re-rank, sau đó lọc còn TOP_K

# Confidence score (cosine similarity = 1 - L2²/2 với embeddings đã normalize)
CONFIDENCE_MIN_RELEVANCE = 0.30   # Dưới ngưỡng này → bỏ qua doc
CONFIDENCE_HIGH = 0.62            # ≥ ngưỡng này → badge xanh "Cao"
CONFIDENCE_MED = 0.45             # ≥ ngưỡng này → badge vàng "Trung bình"
                                  # <  ngưỡng này → badge đỏ "Hạn chế"


# ────────────────────────────────────────────────────────────────
# BIỂU GIÁ ĐIỆN SINH HOẠT BẬC THANG
# Theo QĐ 1279/QĐ-BCT ngày 09/05/2025, hiệu lực từ 10/05/2025
#
# LƯU Ý: QĐ 14/2025/QĐ-TTg đã quy định chuyển sang 5 bậc, sẽ áp dụng
# từ kỳ điều chỉnh giá điện gần nhất. Khi áp dụng, chỉ cần cập nhật
# danh sách bên dưới — hàm tinh_tien_dien() xử lý tổng quát N bậc.
# ────────────────────────────────────────────────────────────────
BIEU_GIA_DIEN = [
    {"bac": 1, "tu": 0,   "den": 50,   "don_gia": 1984},
    {"bac": 2, "tu": 51,  "den": 100,  "don_gia": 2050},
    {"bac": 3, "tu": 101, "den": 200,  "don_gia": 2380},
    {"bac": 4, "tu": 201, "den": 300,  "don_gia": 2998},
    {"bac": 5, "tu": 301, "den": 400,  "don_gia": 3350},
    {"bac": 6, "tu": 401, "den": None, "don_gia": 3460},
]
VAT_RATE = 0.08  # Thuế VAT 8%


# ────────────────────────────────────────────────────────────────
# PROMPT CHO LLM
# ────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Bạn là nhân viên hỗ trợ khách hàng của Điện lực Đà Nẵng.

QUY TẮC TRẢ LỜI BẮT BUỘC:
1. Chỉ dựa trên "Thông tin tham chiếu" bên dưới. KHÔNG bịa thông tin.
2. Trả lời NGẮN GỌN, tối đa khoảng 250 từ. KHÔNG lặp lại cùng một ý/câu.
3. Khi trích dẫn, ghi rõ nguồn: "Theo Điều X, Phần Y, Quy trình Z..."
4. Nếu thông tin tham chiếu KHÔNG liên quan đến câu hỏi, hãy trả lời ngắn gọn:
   "Tôi không tìm thấy thông tin phù hợp trong cơ sở dữ liệu cho câu hỏi này.
   Vui lòng dùng tab khác phù hợp hơn (ví dụ: 'Tính tiền điện') hoặc gọi
   tổng đài 19001909."
   ĐỪNG cố trả lời bằng nội dung không liên quan (ví dụ: HĐMBĐ công nghiệp
   không phải điện sinh hoạt).
5. Câu hỏi tính tiền cụ thể (ví dụ "X kWh hết bao nhiêu") đã có hệ thống
   tính riêng — nếu được hỏi, hãy hướng dẫn dùng tab "Tính tiền điện".
6. Trả lời bằng tiếng Việt, rõ ràng, dễ hiểu.

Thông tin tham chiếu:
{context}

{history_section}Câu hỏi hiện tại: {question}

Câu trả lời (ngắn gọn, không lặp):"""

HISTORY_TEMPLATE = """Lịch sử hội thoại (để tham khảo ngữ cảnh):
{history}

"""


# ────────────────────────────────────────────────────────────────
# THIẾT BỊ MẶC ĐỊNH (TAB PHÂN TÍCH TIÊU THỤ)
# Định dạng: (tên, công_suất_kW, giờ_mặc_định, ghi_chú)
# công_suất_kW = None → tính theo kWh/ngày cố định
# ────────────────────────────────────────────────────────────────
THIET_BI_MAC_DINH = [
    ("Máy lạnh",      1.0,   8,  "Công suất trung bình 1HP"),
    ("Tủ lạnh",       None,  24, "Tính cố định 1.5 kWh/ngày"),
    ("Quạt điện",     0.055, 10, "Quạt đứng/trần"),
    ("TV / Màn hình", 0.1,   5,  "TV LED 40-55 inch"),
    ("Máy tính",      0.065, 8,  "Laptop"),
    ("Đèn LED",       0.01,  8,  "Đèn LED 10W"),
]
TU_LANH_KWH_NGAY = 1.5        # Tủ lạnh 100–200L (giá trị mặc định)


# ────────────────────────────────────────────────────────────────
# THƯ VIỆN THIẾT BỊ GIA ĐÌNH
# (tên_hiển_thị): (công_suất_kW_hoặc_None, giờ_mặc_định, ghi_chú)
# None = tính kWh/ngày cố định (như tủ lạnh)
# ────────────────────────────────────────────────────────────────
THU_VIEN_THIET_BI = {
    # ── Điều hòa ────────────────────────────────────────────────
    "Điều hòa 9.000 BTU 1HP (1–2 sao)":         (0.90,  8,  "Phòng ngủ nhỏ ≤15m²"),
    "Điều hòa 9.000 BTU 1HP (inverter 5 sao)":  (0.60,  8,  "Tiết kiệm ~33% so với thường"),
    "Điều hòa 12.000 BTU 1.5HP (1–2 sao)":      (1.35,  8,  "Phòng 15–20m²"),
    "Điều hòa 12.000 BTU 1.5HP (inverter 5*)":  (0.85,  8,  "Tiết kiệm ~37%"),
    "Điều hòa 18.000 BTU 2HP (1–2 sao)":        (1.80,  8,  "Phòng khách 20–30m²"),
    "Điều hòa 18.000 BTU 2HP (inverter 5*)":    (1.15,  8,  "Tiết kiệm ~36%"),
    "Điều hòa 24.000 BTU 2.5HP":                (2.20,  8,  "Văn phòng / phòng lớn"),

    # ── Tủ lạnh (None = kWh/ngày cố định) ──────────────────────
    "Tủ lạnh mini < 100L":                      (None,  24, "0.6 kWh/ngày"),
    "Tủ lạnh 100–200L (1–2 sao)":               (None,  24, "1.5 kWh/ngày"),
    "Tủ lạnh 100–200L (4–5 sao)":               (None,  24, "0.9 kWh/ngày"),
    "Tủ lạnh 200–350L (1–2 sao)":               (None,  24, "2.5 kWh/ngày"),
    "Tủ lạnh 200–350L (4–5 sao)":               (None,  24, "1.5 kWh/ngày"),
    "Tủ lạnh Side-by-Side > 500L":              (None,  24, "3.5 kWh/ngày"),

    # ── Nấu ăn ──────────────────────────────────────────────────
    "Bếp từ đơn 2.000W":                        (2.00,  1,  "Nấu ~1h/ngày"),
    "Bếp từ đôi 3.500W":                        (3.50,  1,  "Nấu ~1h/ngày"),
    "Bếp hồng ngoại 2.000W":                    (2.00,  1,  "Tương đương bếp từ đơn"),
    "Nồi cơm điện 0.7–1.0L":                    (0.40,  0.5,"Nấu 30 phút/bữa"),
    "Nồi cơm điện 1.5–1.8L":                    (0.55,  0.5,"Nấu 30 phút/bữa"),
    "Lò vi sóng 700–900W":                      (0.80,  0.3,"Hâm thức ăn ~18 phút/ngày"),
    "Lò nướng điện 1.500W":                     (1.50,  0.5,"Nướng 30 phút/ngày"),
    "Nồi chiên không dầu 1.400W":               (1.40,  0.5,"Chiên 30 phút/ngày"),

    # ── Nước nóng ───────────────────────────────────────────────
    "Bình nóng lạnh gián tiếp 15L (2.000W)":    (2.00,  0.5,"Đun 30 phút × 1 lần"),
    "Bình nóng lạnh trực tiếp 4.500W":          (4.50,  0.3,"Chỉ dùng khi tắm ~18 phút"),

    # ── Giặt giũ ────────────────────────────────────────────────
    "Máy giặt cửa trên 7–9kg":                  (0.50,  1,  "1 mẻ giặt ~1h/ngày"),
    "Máy giặt cửa trước 7–9kg":                 (0.45,  1,  "Tiết kiệm nước hơn"),
    "Máy giặt 9–12kg inverter":                 (0.38,  1,  "Tiết kiệm điện ~16%"),
    "Máy sấy quần áo 2.000W":                   (2.00,  0.5,"Sấy 30 phút/mẻ"),

    # ── Giải trí & văn phòng ────────────────────────────────────
    "TV LED 32 inch":                           (0.055, 5,  "Phòng nhỏ, ngủ"),
    "TV LED 43–50 inch":                        (0.090, 5,  "Phòng khách"),
    "TV LED/OLED 55–65 inch":                   (0.130, 5,  "Màn hình lớn"),
    "Máy tính để bàn + màn hình":               (0.180, 8,  "PC gaming ~250W"),
    "Laptop":                                   (0.065, 8,  "Tiêu thụ thấp"),
    "Máy tính bảng (sạc)":                      (0.010, 2,  "10W × 2h"),
    "Game console (PS5/Xbox)":                  (0.120, 3,  "Chơi game ~3h/ngày"),

    # ── Quạt & đèn ──────────────────────────────────────────────
    "Quạt đứng / bàn 40–45W":                   (0.042, 10, "Thay thế điều hòa"),
    "Quạt trần 55–75W":                         (0.065, 10, "Hiệu quả cho phòng lớn"),
    "Quạt inverter 10–25W":                     (0.018, 10, "Tiết kiệm điện ~57%"),
    "Đèn LED 5W":                               (0.005, 8,  "Đèn trang trí / hành lang"),
    "Đèn LED 9–10W":                            (0.010, 8,  "Thay đèn compact 25W"),
    "Đèn LED 15–18W":                           (0.016, 8,  "Đèn trần phòng lớn"),
    "Đèn huỳnh quang T8 36W (cũ)":              (0.036, 8,  "Tốn gấp 3–4 lần LED"),

    # ── Thiết bị khác ───────────────────────────────────────────
    "Máy bơm nước 250–400W":                    (0.35,  0.5,"Bơm 30 phút/ngày"),
    "Bình đun nước (ấm điện) 1.500W":           (1.50,  0.3,"Đun sôi 300ml × 3 lần"),
    "Máy lọc không khí 50–60W":                 (0.055, 8,  "Chạy liên tục"),
    "Máy hút bụi 1.000W":                       (1.00,  0.2,"Hút 12 phút/ngày"),
    "Router WiFi":                              (0.010, 24, "Chạy liên tục 24/7"),
    "Camera an ninh 4 cổng":                    (0.020, 24, "Chạy liên tục 24/7"),
}


# ────────────────────────────────────────────────────────────────
# BENCHMARK TIÊU THỤ ĐIỆN HỘ GIA ĐÌNH (kWh/tháng)
# (trung_bình, thấp, cao, mô_tả) — tổng hợp từ dữ liệu EVN & khảo sát
# ────────────────────────────────────────────────────────────────
BENCHMARK_HO_GIA_DINH = {
    # ── Phòng trọ ──
    (1, "Phòng trọ"):     (65,   35,  110, "Sinh viên, 1 phòng"),
    (2, "Phòng trọ"):     (100,  60,  155, "Cặp đôi, phòng có máy lạnh"),
    (3, "Phòng trọ"):     (130,  80,  195, "3 người, phòng trọ rộng hơn"),
    (4, "Phòng trọ"):     (160, 100,  230, "4 người, phòng trọ có bếp"),
    # ── Chung cư ──
    (1, "Chung cư"):      (90,   55,  140, "1 người, căn hộ nhỏ"),
    (2, "Chung cư"):      (140,  90,  210, "Căn hộ 1–2 phòng ngủ"),
    (3, "Chung cư"):      (195, 130,  280, "Gia đình nhỏ"),
    (4, "Chung cư"):      (245, 165,  350, "Gia đình 4 người, căn hộ"),
    (5, "Chung cư"):      (300, 210,  420, "Gia đình lớn, căn hộ rộng"),
    (6, "Chung cư"):      (360, 250,  500, "Nhiều người, căn hộ đủ tiện nghi"),
    # ── Nhà phố ──
    (1, "Nhà phố"):       (120,  70,  180, "1 người, nhà riêng nhỏ"),
    (2, "Nhà phố"):       (160, 100,  240, "Nhà 1–2 tầng"),
    (3, "Nhà phố"):       (220, 150,  320, "Nhà 2–3 tầng, đủ tiện nghi"),
    (4, "Nhà phố"):       (290, 200,  420, "Đủ tiện nghi: máy lạnh, tủ lạnh lớn"),
    (5, "Nhà phố"):       (360, 250,  510, "Gia đình lớn, nhiều thiết bị"),
    (6, "Nhà phố"):       (440, 310,  620, "Nhiều phòng, nhiều máy lạnh"),
    # ── Nhà biệt thự ──
    (3, "Nhà biệt thự"):  (420, 280,  600, "Biệt thự nhỏ, đủ tiện nghi"),
    (4, "Nhà biệt thự"):  (520, 360,  730, "Bể bơi, sân vườn, nhiều điều hòa"),
    (5, "Nhà biệt thự"):  (620, 430,  860, "Biệt thự lớn, nhiều thiết bị cao cấp"),
    (6, "Nhà biệt thự"):  (720, 500,  980, "Biệt thự rộng, hệ thống điện lớn"),
}
LOAI_NHA_OPTIONS = ["Phòng trọ", "Chung cư", "Nhà phố", "Nhà biệt thự"]


# ────────────────────────────────────────────────────────────────
# ĐIỆN MẶT TRỜI MÁI NHÀ
# ────────────────────────────────────────────────────────────────
SOLAR_PSH = {  # Peak Sun Hours theo khu vực
    "Đà Nẵng / Nam Trung Bộ":            4.9,
    "TP.HCM / Đông Nam Bộ":              5.2,
    "Hà Nội / Đồng bằng Bắc Bộ":         3.8,
    "Huế / Bắc Trung Bộ":                4.3,
    "Nha Trang / Khánh Hòa":             5.1,
    "Đà Lạt / Tây Nguyên":               4.6,
    "Cần Thơ / Đồng bằng sông Cửu Long": 5.0,
    "Thanh Hóa / Nghệ An":               4.1,
}
SOLAR_PANEL_W = 400            # Công suất 1 tấm pin (Wp)
SOLAR_PANEL_M2 = 2.0           # Diện tích 1 tấm (m²)
SOLAR_SYSTEM_EFF = 0.80        # Hiệu suất hệ thống (inverter + dây + nhiệt độ)
SOLAR_COST_PER_WP = 15_000     # Chi phí lắp đặt trọn gói: ~15.000 đ/Wp (2025)
SOLAR_FEED_IN = 671            # Giá EVN mua điện dư: 671 đ/kWh (theo TT 18/2020/TT-BCT)
SOLAR_SELF_USE_RATE = 0.70     # 70% tự dùng, 30% bán lại


# ────────────────────────────────────────────────────────────────
# DỮ LIỆU ROI THAY THIẾT BỊ CŨ
# cong_suat_theo_sao: kW (hoặc kWh/ngày với tủ lạnh)
# ────────────────────────────────────────────────────────────────
LOAI_THIET_BI_ROI = {
    "Máy lạnh": {
        "don_vi": "HP",
        "mo_ta_cu": "Máy lạnh 12.000 BTU (1.5HP)",
        "loai_tinh": "kw",
        "cong_suat_theo_sao": {1: 1.50, 2: 1.30, 3: 1.10, 4: 1.00, 5: 0.85},
        "gio_mac_dinh": 8,
        "thay_the": [
            {"ten": "Máy lạnh 1.5HP inverter 5 sao", "cong_suat": 0.75, "gia":  9_500_000},
            {"ten": "Máy lạnh 1.5HP inverter 4 sao", "cong_suat": 0.90, "gia":  7_500_000},
            {"ten": "Máy lạnh 2HP inverter 5 sao",   "cong_suat": 1.10, "gia": 13_000_000},
        ],
    },
    "Tủ lạnh": {
        "don_vi": "Lít",
        "mo_ta_cu": "Tủ lạnh 200–300L",
        "loai_tinh": "kwh_ngay",
        "cong_suat_theo_sao": {1: 2.8, 2: 2.2, 3: 1.8, 4: 1.4, 5: 1.0},
        "gio_mac_dinh": 24,
        "thay_the": [
            {"ten": "Tủ lạnh 2 cửa 5 sao 300L",        "kwh_ngay": 1.0, "gia": 12_000_000},
            {"ten": "Tủ lạnh inverter 5 sao 400L",     "kwh_ngay": 1.2, "gia": 18_000_000},
            {"ten": "Tủ lạnh side-by-side 5 sao 560L", "kwh_ngay": 1.5, "gia": 28_000_000},
        ],
    },
    "Đèn điện": {
        "don_vi": "W",
        "mo_ta_cu": "Đèn huỳnh quang / compact cũ",
        "loai_tinh": "kw",
        "cong_suat_theo_sao": {1: 0.060, 2: 0.040, 3: 0.025, 4: 0.015, 5: 0.010},
        "gio_mac_dinh": 8,
        "thay_the": [
            {"ten": "Đèn LED 9W (thay bóng 60W)",    "cong_suat": 0.009, "gia":  80_000},
            {"ten": "Đèn LED 12W (thay bóng 75W)",   "cong_suat": 0.012, "gia":  95_000},
            {"ten": "Đèn LED 18W (thay đèn T8 36W)", "cong_suat": 0.018, "gia": 120_000},
        ],
    },
    "Máy nước nóng": {
        "don_vi": "Lít",
        "mo_ta_cu": "Bình nóng lạnh gián tiếp",
        "loai_tinh": "kw",
        "cong_suat_theo_sao": {1: 2.5, 2: 2.2, 3: 2.0, 4: 1.8, 5: 1.5},
        "gio_mac_dinh": 1,
        "thay_the": [
            {"ten": "Bình nóng lạnh 5 sao 20L",     "cong_suat": 1.5, "gia":  4_500_000},
            {"ten": "Bình nóng lạnh 5 sao 30L",     "cong_suat": 1.5, "gia":  5_500_000},
            {"ten": "Máy năng lượng mặt trời 200L", "cong_suat": 0.2, "gia": 22_000_000},
        ],
    },
    "Máy giặt": {
        "don_vi": "kg",
        "mo_ta_cu": "Máy giặt cửa trên",
        "loai_tinh": "kw",
        "cong_suat_theo_sao": {1: 0.65, 2: 0.55, 3: 0.48, 4: 0.42, 5: 0.35},
        "gio_mac_dinh": 1,
        "thay_the": [
            {"ten": "Máy giặt cửa trước 9kg inverter", "cong_suat": 0.35, "gia":  9_000_000},
            {"ten": "Máy giặt 12kg inverter 5 sao",    "cong_suat": 0.38, "gia": 12_000_000},
        ],
    },
}
