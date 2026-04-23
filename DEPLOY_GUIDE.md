# 🚀 Hướng dẫn Deploy Chatbot Điện lực Đà Nẵng lên Streamlit Cloud

> Phiên bản: v2.1.2 · Cập nhật: 04/2026
>
> Thời gian deploy dự kiến: **10–15 phút**.

---

## 1. Tổng quan

Ứng dụng sẽ được deploy miễn phí lên **Streamlit Community Cloud** (https://share.streamlit.io), chạy trên Python 3.10+, RAM 1 GB. Quy trình gồm 3 bước lớn:

1. Chuẩn bị repo GitHub (xóa secrets, dọn file rác, giữ Vector DB).
2. Cấu hình secrets trên Streamlit Cloud.
3. Deploy và kiểm thử.

---

## 2. Chuẩn bị repo trước khi push

### 2.1. Xóa file không nên commit

```bash
# Xóa .env chứa API key (tuyệt đối không đẩy lên GitHub)
rm .env

# Xóa cache Python
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
```

### 2.2. Cập nhật `.gitignore`

Lưu ý quan trọng: phải **bỏ ignore** thư mục Vector DB để Streamlit Cloud đọc được DB đã build sẵn (khi deploy, Streamlit không tự chạy `tao_vector_db.py`):

File `.gitignore` mới đã gỡ 3 dòng:

```
# faiss_dienluc_db/
# *.faiss
# *.pkl
```

### 2.3. Verify Vector DB và dữ liệu đều có

```bash
# Kiểm tra Vector DB đã build
ls -lh faiss_dienluc_db/
# Phải thấy index.faiss (~817 KB) và index.pkl (~706 KB)

# Kiểm tra PDF nguồn
ls -lh data/*.pdf
# Phải thấy 3 file QĐ 1199, QĐ 1279, NĐ 58/2025
```

Tổng dung lượng repo sẽ ~14–15 MB — vẫn nhỏ hơn giới hạn 100 MB của GitHub rất nhiều.

### 2.4. Push lên GitHub

```bash
git init
git add .
git commit -m "Deploy v2.1.2"
git branch -M main
git remote add origin https://github.com/<username>/chatbot-dienluc-danang.git
git push -u origin main
```

Kiểm tra trên GitHub đã có:
- ✅ `faiss_dienluc_db/index.faiss`
- ✅ `data/1199-QD-EVNCPC_cap_dien_sinh_hoat.pdf`
- ❌ `.env` (phải KHÔNG có)
- ❌ `__pycache__/` (phải KHÔNG có)

---

## 3. Deploy lên Streamlit Cloud

### 3.1. Tạo app mới

1. Truy cập https://share.streamlit.io
2. Đăng nhập bằng GitHub
3. Bấm **New app**
4. Điền form:
   - **Repository**: `<username>/chatbot-dienluc-danang`
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL (tùy chọn)**: `chatbot-dienluc-danang`

5. Bấm **Advanced settings** → chọn **Python 3.11** (ổn định nhất với LangChain).

### 3.2. Cấu hình Secrets

Đây là bước **bắt buộc** để thay thế file `.env` không đẩy lên GitHub. Trên dashboard app, vào **Settings → Secrets**, paste nội dung sau (định dạng TOML):

```toml
GROQ_API_KEY = "gsk_xxxxxxxxxxxxxxxxxxxxxxxx"
LLAMA_CLOUD_API_KEY = "llx-xxxxxxxxxxxxxxxxxxxxxxxx"
```

Bấm **Save**. Streamlit sẽ inject các biến này vào `os.environ`, nên `config.py` đọc được qua `os.getenv()` mà không cần sửa code.

### 3.3. Deploy

Bấm **Deploy!** — Streamlit sẽ:
1. Clone repo về (~5 giây)
2. Cài thư viện từ `requirements.txt` (~2–3 phút)
3. Download model embedding từ HuggingFace `paraphrase-multilingual-MiniLM-L12-v2` (~1 phút, ~470 MB)
4. Chạy `streamlit run app.py`

**Cold start tổng: 3–5 phút cho lần đầu**. Sau đó mỗi lần mở URL chỉ mất ~10 giây.

---

## 4. Kiểm thử sau khi deploy

Mở URL app và test các kịch bản quan trọng theo thứ tự:

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Mở app, đợi load xong | Sidebar hiện: `Vector DB: ✅  LLM: ✅` |
| 2 | Tab "Trợ lý Pháp lý" → bấm câu hỏi gợi ý "Giấy tờ cần thiết để cấp điện sinh hoạt?" | Có câu trả lời + citation + badge confidence |
| 3 | Tab "Trợ lý Pháp lý" → gõ "250 kWh hết bao nhiêu tiền" | Kích hoạt fast-path, ra 636,768 đ (không tốn LLM call) |
| 4 | Tab "Tính tiền điện" → nhập 500 kWh, 2 hộ → bấm Tính | Metric + waterfall chart hiện đủ, tiết kiệm > 0 |
| 5 | Tab "Điện Mặt Trời" → nhập 30 m², 250 kWh, rate 70% → Tính | ~15 tấm pin, hoàn vốn ~4–5 năm |
| 6 | Sidebar → "Xuất hóa đơn" | Tải được file `.html`, mở bằng trình duyệt thấy đúng format |

Nếu bước 1 thấy `Vector DB: ❌` → quay lại mục 2.3, chắc chắn chưa commit `faiss_dienluc_db/`.

---

## 5. Xử lý sự cố thường gặp

### 5.1. Lỗi `ModuleNotFoundError: No module named 'xxx'`

→ Thiếu thư viện trong `requirements.txt`. Sửa file, commit, Streamlit tự redeploy.

### 5.2. App crash với `MemoryError` hoặc bị kill lúc load

→ Vượt giới hạn 1 GB RAM. Khả năng cao do user đang upload PDF lớn trong tab "Quản lý Tài liệu". 

**Giải pháp tạm thời cho bản demo**: comment dòng `with tab_docs` trong `app.py` để ẩn tab này trước khi bảo vệ.

### 5.3. Lỗi `401 Unauthorized` khi gọi Groq

→ API key hết hạn hoặc sai. Kiểm tra lại Settings → Secrets trên Streamlit Cloud. Có thể vào https://console.groq.com/keys tạo key mới.

### 5.4. Cold start bị timeout

→ Mạng HuggingFace đang chậm. Đợi 2–3 phút rồi F5 lại là được.

### 5.5. Groq rate limit (HTTP 429)

→ Đã vượt 30 req/phút hoặc 14.400 req/ngày của free tier. App đã có `RATE_LIMIT_MESSAGE` xử lý thân thiện. Đợi 1 phút rồi thử lại, hoặc tạo key mới.

---

## 6. Lưu ý quan trọng cho buổi bảo vệ

### 6.1. Trước khi demo

- ☐ Tạo Groq API key **riêng** dành cho demo, tránh share với ai khác (tránh bị rate limit lúc đang chạy trước hội đồng).
- ☐ Test lại toàn bộ 6 kịch bản ở mục 4 trước buổi bảo vệ **1 ngày** và **1 giờ** trước khi vào.
- ☐ Chuẩn bị phương án B: nếu mất mạng / server down, có thể chạy local qua `streamlit run app.py`.
- ☐ Mở sẵn tab URL trước khi vào phòng, tránh cold start lúc hội đồng đang xem.

### 6.2. Hạn chế của bản deploy

Cần note với hội đồng nếu bị hỏi:

1. **Filesystem ephemeral**: Mọi file user upload qua tab "Quản lý Tài liệu" sẽ mất khi Streamlit Cloud redeploy. Phù hợp cho demo, không dùng cho production thật.
2. **Single instance**: Streamlit Cloud free chỉ có 1 instance, mọi user cùng share 1 session state. Nếu nhiều người vào cùng lúc → session có thể xung đột. Production cần multi-instance + Redis.
3. **LLM phụ thuộc Groq**: Nếu Groq đổi pricing / ngừng free tier, cần migrate sang provider khác (OpenAI, Together, local Ollama). Code đã tách LLM ra `config.py` nên chỉ sửa 1 chỗ.

### 6.3. Khi deploy xong cho đề án

- ☐ Lưu URL vào slide bảo vệ (trang cuối).
- ☐ Tạo QR code dẫn về URL, in vào góc slide để hội đồng quét thử trên điện thoại.
- ☐ Screenshot 5–6 trang của app đưa vào báo cáo cuối để minh chứng đã deploy thành công.

---

## 7. Chi phí

| Dịch vụ | Gói | Chi phí |
|---|---|---|
| Streamlit Community Cloud | Free | 0 đ |
| Groq API | Free tier (14.400 req/ngày) | 0 đ |
| GitHub (public repo) | Free | 0 đ |
| LlamaParse (optional, OCR) | Free 1000 trang/ngày | 0 đ |
| **Tổng** | | **0 đ/tháng** |

Đủ thoải mái cho đề án học tập và demo trước hội đồng.

---

**Tác giả**: Sinh viên K29 – Khoa Thương mại Điện tử, Đại học Kinh tế – Đại học Đà Nẵng.
