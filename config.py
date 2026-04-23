import os
import warnings
from dotenv import load_dotenv


load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_DIR = os.path.join(BASE_DIR, "faiss_dienluc_db")
os.makedirs(DATA_DIR, exist_ok=True)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY", "").strip()


def _is_placeholder(key: str) -> bool:
    if not key:
        return True
    placeholders = ("your_key_here", "xxx", "placeholder")
    return any(p in key.lower() for p in placeholders)



GROQ_KEY_OK = not _is_placeholder(GROQ_API_KEY) and GROQ_API_KEY.startswith("gsk_")
LLAMA_KEY_OK = not _is_placeholder(LLAMA_CLOUD_API_KEY) and LLAMA_CLOUD_API_KEY.startswith("llx-")

if not GROQ_KEY_OK:
    warnings.warn(
        "GROQ_API_KEY chưa được cấu hình hoặc không hợp lệ. "
        "Tạo file .env và thêm: GROQ_API_KEY=gsk_...",
        RuntimeWarning,
    )


os.environ["GROQ_API_KEY"] = GROQ_API_KEY


EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
LLM_MODEL = "llama-3.1-8b-instant"
LLM_TEMPERATURE = 0.2  
LLM_MAX_TOKENS = 800  
LLM_FREQUENCY_PENALTY = 0.6


CHUNK_SIZE = 1200       
CHUNK_OVERLAP = 300     
SEPARATORS = [
    "\n\n",       
    "\n",         
    "Phần ",      
    "Chương ",    
    "Mục ",       
    "Điều ",      
    "Khoản ",    
    ". ",         
    " ",          
]


SEARCH_TOP_K = 5       
SEARCH_FETCH_K = 15    

CONFIDENCE_MIN_RELEVANCE = 0.30   
CONFIDENCE_HIGH = 0.62           
CONFIDENCE_MED = 0.45            
                                  


BIEU_GIA_DIEN = [
    {"bac": 1, "tu": 0,   "den": 50,   "don_gia": 1984},
    {"bac": 2, "tu": 51,  "den": 100,  "don_gia": 2050},
    {"bac": 3, "tu": 101, "den": 200,  "don_gia": 2380},
    {"bac": 4, "tu": 201, "den": 300,  "don_gia": 2998},
    {"bac": 5, "tu": 301, "den": 400,  "don_gia": 3350},
    {"bac": 6, "tu": 401, "den": None, "don_gia": 3460},
]
VAT_RATE = 0.08  


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


THIET_BI_MAC_DINH = [
    ("Máy lạnh",      1.0,   8,  "Công suất trung bình 1HP"),
    ("Tủ lạnh",       None,  24, "Tính cố định 1.5 kWh/ngày"),
    ("Quạt điện",     0.055, 10, "Quạt đứng/trần"),
    ("TV / Màn hình", 0.1,   5,  "TV LED 40-55 inch"),
    ("Máy tính",      0.065, 8,  "Laptop"),
    ("Đèn LED",       0.01,  8,  "Đèn LED 10W"),
]
TU_LANH_KWH_NGAY = 1.5        # Tủ lạnh 100–200L (giá trị mặc định)




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



# ĐIỆN MẶT TRỜI MÁI NHÀ

SOLAR_PSH = {
    "Hà Nội và Bắc Bộ":           3.8,
    "Đà Nẵng và Trung Bộ":        4.8,
    "TP.HCM và Nam Bộ":           5.2,
    "Tây Nguyên":                  5.1,
    "Ninh Thuận – Bình Thuận":    5.8,
}
SOLAR_PANEL_W = 400            
SOLAR_PANEL_M2 = 2.0          
SOLAR_SYSTEM_EFF = 0.80        
SOLAR_COST_PER_WP = 15_000     
SOLAR_FEED_IN = 671           
SOLAR_SELF_USE_RATE = 0.70     

