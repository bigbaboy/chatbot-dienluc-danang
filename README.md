# ⚡ Chatbot Điện lực Đà Nẵng

> Hệ thống hỗ trợ khách hàng ứng dụng kỹ thuật **RAG** (Retrieval-Augmented Generation) cho ngành điện lực.
> Đề án tốt nghiệp K29 — Khoa Thương mại Điện tử, Đại học Kinh tế Đà Nẵng.

## 🎯 Tính năng

| Tab | Tính năng | Mô tả |
|---|---|---|
| 1 | **Trợ lý Pháp lý (RAG)** | Hỏi-đáp về quy định EVN dựa trên văn bản QĐ 1199, 1279, NĐ 58/2025 |
| 2 | **Tính tiền điện** | Tính hóa đơn bậc thang theo QĐ 1279/QĐ-BCT 2025, hỗ trợ tách nhiều hộ |
| 3 | **Phân tích Tiêu thụ** | Ước tính kWh/tháng từ thiết bị, so sánh với benchmark hộ gia đình |
| 4 | **Điện Mặt Trời** | Tính sản lượng, tiết kiệm và ROI khi lắp điện mặt trời mái nhà |
| 5 | **ROI Thiết bị** | So sánh thiết bị cũ vs mới, tính thời gian hoàn vốn |
| 6 | **Quản lý Tài liệu** | Upload PDF mới, tự động cập nhật Vector DB |

## 🚀 Cài đặt nhanh

### 1. Yêu cầu
- Python 3.10 trở lên
- 4GB RAM (để chạy embedding model)
- API key Groq miễn phí (đăng ký tại https://console.groq.com)

### 2. Các bước

```bash
# Clone / giải nén thư mục đề án
cd DeAn2

# Cài thư viện
pip install -r requirements.txt

# Cấu hình API key
cp .env.example .env
# Mở file .env, điền GROQ_API_KEY thật vào

# Tạo Vector Database (lần đầu, mất ~2 phút)
python tao_vector_db.py

# Chạy ứng dụng
streamlit run app.py
```

Mở trình duyệt tại `http://localhost:8501`.

## 🧪 Kiểm thử (Testing)

Dự án có **116 unit test** kiểm tra các hàm tính toán cốt lõi, helper của RAG pipeline và bảo mật:

```bash
# Cài pytest
pip install pytest

# Chạy toàn bộ test
pytest test_tinh_toan.py -v

# Hoặc chạy nhanh không cần pytest
python test_tinh_toan.py
```

Kết quả mong đợi: `116 passed`

### Test coverage
- ✅ `tinh_tien_dien()`: 11 mức kWh (0, 50, 100, 150, …, 1000)
- ✅ Tổng phân bổ bậc = kWh input (9 cases)
- ✅ Tách hộ gia đình (4 cases)
- ✅ Tính kWh/tháng của thiết bị (5 cases)
- ✅ Tính sản lượng điện mặt trời (3 cases)
- ✅ Confidence score từ L2 distance (4 cases)
- ✅ Định dạng tiền tệ (4 cases)
- ✅ Template hóa đơn HTML (7 cases, gồm regression test bậc 6)
- ✅ RAG pipeline helpers (4 cases)
- ✅ Biểu giá khớp QĐ 1279 (9 cases)
- ✅ Phân chia tự dùng/bán lại ĐMT (6 cases)
- ✅ ROI thay thiết bị qua biểu giá bậc thang (4 cases)
- ✅ Phát hiện câu hỏi tính tiền — fast-path RAG (16 cases)
- ✅ Format câu trả lời tính tiền (3 cases)
- ✅ **Mới (v2.1.1)**: Validate định dạng tháng MM/YYYY (18 cases)
- ✅ **Mới (v2.1.1)**: Regression XSS escape cho citation card (4 cases)

## 📁 Cấu trúc project

```
DeAn2/
├── app.py                       # Entry point Streamlit (chỉ điều phối, ~115 dòng)
├── config.py                    # Cấu hình tập trung (API keys, biểu giá, prompts)
├── utils.py                     # Hàm tính toán thuần (để dễ test)
├── rag_pipeline.py              # RAG: retrieve → re-rank → LLM generate
├── db_manager.py                # Build / load / merge FAISS DB
├── hoa_don.py                   # Tạo hóa đơn HTML (có unit test)
├── doc_pdf_smart.py             # Đọc PDF (PyMuPDF + LlamaParse fallback)
├── ui_helpers.py                # Load CSS, init session state
├── sidebar.py                   # Sidebar (hồ sơ, lịch sử, trạng thái)
├── tabs/                        # Mỗi tab 1 file
│   ├── chat.py                  # Tab 1: Trợ lý Pháp lý (RAG chatbot)
│   ├── tien_dien.py             # Tab 2: Tính tiền điện bậc thang
│   ├── tieu_thu.py              # Tab 3: Phân tích tiêu thụ
│   ├── solar.py                 # Tab 4: Điện mặt trời
│   ├── roi.py                   # Tab 5: ROI thay thiết bị
│   └── docs.py                  # Tab 6: Quản lý tài liệu
├── assets/
│   └── styles.css               # CSS tách ra khỏi app.py
├── tao_vector_db.py             # CLI build Vector DB lần đầu
├── tao_bao_cao.py               # Script tạo báo cáo Word (tùy chọn)
├── test_tinh_toan.py            # Unit test với pytest (64 tests)
├── VERSION                      # Phiên bản hiện tại
├── CHANGELOG.md                 # Lịch sử thay đổi
├── .env.example                 # File mẫu cho API key
├── .gitignore
├── requirements.txt
├── data/                        # Văn bản pháp luật nguồn
│   ├── 1199-QD-EVNCPC_cap_dien_sinh_hoat.pdf
│   ├── 1279-QD-BCT_bieu_gia_dien_2025.pdf
│   └── 58-2025-ND-CP_dien_mat_troi.pdf
└── faiss_dienluc_db/            # Vector Database (tự tạo từ data/)
```

## 🏗️ Kiến trúc hệ thống

```
┌──────────────────┐     ┌──────────────────┐     ┌───────────────┐
│   Người dùng     │────▶│  Streamlit UI    │────▶│  RAG Pipeline │
└──────────────────┘     └──────────────────┘     └───────┬───────┘
                                                          │
                    ┌─────────────────────────────────────┤
                    ▼                                     ▼
         ┌──────────────────────┐           ┌─────────────────────┐
         │  FAISS Vector DB     │           │  Groq LLaMA 3.1 8B  │
         │  (384-dim MiniLM)    │           │  (Temperature 0.2)  │
         └──────────┬───────────┘           └─────────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │   Tài liệu PDF        │
         │   (Quyết định, NĐ,   │
         │    Quy trình EVN)    │
         └──────────────────────┘
```

### Điểm kỹ thuật nổi bật

- **Multilingual Embedding**: Dùng `paraphrase-multilingual-MiniLM-L12-v2` để hiểu tiếng Việt
- **Re-ranking**: Lấy 15 docs → lọc theo ngưỡng → giữ top 5 có điểm cao nhất
- **Confidence Score**: Chuyển L2² distance sang cosine similarity [0,1] để hiển thị độ tin cậy
- **Fallback PDF Reader**: PyMuPDF (nhanh) → LlamaParse (OCR) nếu file scan
- **Prompt Engineering**: System prompt yêu cầu trích dẫn nguồn, không bịa thông tin
- **Session State**: Lưu kết quả AI để không mất khi Streamlit rerun

## 🔒 Bảo mật

- ⚠️ **KHÔNG BAO GIỜ** commit file `.env` lên git — đã có sẵn trong `.gitignore`
- Vector DB và embedding chạy **local**, không gửi dữ liệu ra ngoài
- Chỉ có câu hỏi người dùng được gửi đến Groq API

## 🔄 Khả năng mở rộng

Khi có Quyết định mới thay thế biểu giá điện (ví dụ QĐ 14/2025/QĐ-TTg chuyển sang 5 bậc), chỉ cần cập nhật biến `BIEU_GIA_DIEN` trong `config.py`. Hàm `tinh_tien_dien()` xử lý tổng quát cho N bậc, không cần sửa code logic.

```python
# Ví dụ chuyển sang 5 bậc
BIEU_GIA_DIEN = [
    {"bac": 1, "tu": 0,   "den": 100,  "don_gia": 1984},
    {"bac": 2, "tu": 101, "den": 200,  "don_gia": 2380},
    # ...
]
```

## 📜 Nguồn văn bản pháp luật

- **QĐ 1199/QĐ-EVNCPC**: Quy trình cấp điện sinh hoạt (EVN CPC)
- **QĐ 1279/QĐ-BCT** (09/05/2025): Biểu giá điện hiện hành
- **QĐ 14/2025/QĐ-TTg** (29/05/2025): Cơ cấu biểu giá 5 bậc (áp dụng sau)
- **NĐ 58/2025/NĐ-CP**: Cơ chế khuyến khích điện mặt trời mái nhà tự sản tự tiêu

## 👤 Tác giả

Sinh viên K29 – Khoa Thương mại Điện tử
Đại học Kinh tế – Đại học Đà Nẵng

---

> **Lưu ý**: Đây là đề án học tập, các ước tính chỉ mang tính tham khảo.
> Hóa đơn chính thức do Điện lực Đà Nẵng phát hành.
