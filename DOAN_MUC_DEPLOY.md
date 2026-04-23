# Đoạn mô tả Deploy cho Báo cáo Đề án

> Đoạn này bạn có thể copy-paste vào chương "Triển khai" hoặc "Deployment" trong BaoCao_DeAn.docx.

---

## 5.X. Triển khai ứng dụng lên môi trường cloud

### 5.X.1. Lựa chọn nền tảng

Ứng dụng được triển khai trên **Streamlit Community Cloud** – nền tảng PaaS miễn phí của Streamlit Inc., được lựa chọn sau khi đánh giá ba phương án: (1) Streamlit Cloud, (2) Render, (3) Docker trên VPS. Lý do lựa chọn Streamlit Cloud:

- Tích hợp trực tiếp với GitHub, không cần cấu hình CI/CD.
- Hỗ trợ sẵn runtime Python 3.11 và các thư viện khoa học dữ liệu phổ biến.
- Cung cấp 1 GB RAM miễn phí – đủ để chạy mô hình embedding 470 MB (`paraphrase-multilingual-MiniLM-L12-v2`) kèm FAISS Vector DB và Streamlit runtime.
- Có cơ chế quản lý secrets an toàn, tách biệt với mã nguồn.

### 5.X.2. Kiến trúc triển khai

Ứng dụng chạy trên một instance duy nhất với các thành phần:

- **Mã nguồn**: lưu trên GitHub (repository công khai hoặc riêng tư tùy chọn).
- **Vector Database**: commit trực tiếp vào repo (thư mục `faiss_dienluc_db/`, dung lượng ~1.5 MB) để tránh phải rebuild sau mỗi lần redeploy.
- **API keys**: lưu trong Streamlit Cloud Secrets, inject vào biến môi trường khi khởi động – không bao giờ xuất hiện trong mã nguồn.
- **LLM backend**: Groq API (`llama-3.1-8b-instant`), truy cập qua HTTPS.

Sơ đồ luồng request:

```
[User Browser]  ⇄  [Streamlit Cloud Instance]  ⇄  [Groq API]
                        │
                        ├── FAISS DB (local disk)
                        ├── HuggingFace Embedding (in-memory)
                        └── PDF source (data/)
```

### 5.X.3. Quy trình triển khai

Quy trình gồm bốn bước, tổng thời gian khoảng 10–15 phút:

**Bước 1**: Chuẩn bị mã nguồn – xóa file `.env`, xóa thư mục `__pycache__/`, cập nhật `.gitignore` để giữ Vector DB trong repo.

**Bước 2**: Push code lên GitHub bằng `git push`. Dung lượng repo khoảng 14 MB, bao gồm mã nguồn, Vector DB và 3 file PDF văn bản pháp luật nguồn.

**Bước 3**: Tạo app trên https://share.streamlit.io, trỏ đến file `app.py` trên branch `main`, cấu hình secrets `GROQ_API_KEY` và `LLAMA_CLOUD_API_KEY` theo định dạng TOML.

**Bước 4**: Streamlit Cloud tự động clone repo, cài đặt các thư viện trong `requirements.txt`, download mô hình embedding từ HuggingFace, sau đó khởi động app. Cold start lần đầu khoảng 3–5 phút, các lần mở sau chỉ mất khoảng 10 giây.

### 5.X.4. Bảo mật

- **Secrets**: API keys được quản lý qua Streamlit Secrets thay vì hard-code hay file `.env` commit lên Git, phù hợp với OWASP Top 10 – khuyến nghị A07:2021 về Identification and Authentication Failures.
- **HTTPS**: Streamlit Cloud tự động cấp và gia hạn chứng chỉ TLS của Let's Encrypt cho mọi app.
- **Input sanitization**: Toàn bộ nội dung từ tài liệu PDF và user upload đều được escape HTML trước khi render (sử dụng `html.escape()` trong `tabs/chat.py`), phòng ngừa tấn công Cross-Site Scripting (XSS).
- **Vector DB**: Khi load FAISS từ pickle, bật cờ `allow_dangerous_deserialization=True` – đây là hạn chế hiện tại của phiên bản v2.1.2. Trong môi trường production thực tế, cần migrate sang vector store an toàn hơn như ChromaDB hoặc Weaviate. Với phạm vi đề án học tập (chỉ admin upload PDF), rủi ro này chấp nhận được.

### 5.X.5. Hạn chế của bản triển khai miễn phí

Cần lưu ý cho các phiên bản tương lai:

1. **Filesystem ephemeral**: Mọi file được upload qua tính năng "Quản lý Tài liệu" sẽ bị xóa khi Streamlit Cloud restart hoặc redeploy. Phù hợp cho demo, chưa phù hợp cho production thật. Giải pháp: tích hợp cloud storage như AWS S3 hoặc Google Cloud Storage.

2. **Single instance, single-tenant session**: Tất cả người dùng cùng chia sẻ một instance Streamlit. Khi có nhiều người truy cập đồng thời, session state có thể gây xung đột. Để scale cần chuyển sang kiến trúc multi-instance với Redis làm session backend.

3. **Rate limit của Groq free tier**: Giới hạn 30 requests/phút và 14.400 requests/ngày. Đủ cho demo và sử dụng cá nhân, nhưng nếu deploy cho nhiều user thật cần nâng cấp lên gói trả phí (~0.05 USD/1M tokens input).

### 5.X.6. Chi phí vận hành

Toàn bộ hệ thống được triển khai với chi phí **0 đồng/tháng** nhờ tận dụng các gói miễn phí của Streamlit Community Cloud, Groq, GitHub và LlamaParse. Phù hợp cho dự án học tập và là bằng chứng khả thi (proof-of-concept) cho việc xây dựng chatbot AI ngành điện với ngân sách hạn chế.

---

*Đoạn trên dài khoảng 2 trang A4 khi đặt vào Word với font Times New Roman 13, hợp với dung lượng thường yêu cầu của một mục con trong đề án cử nhân.*
