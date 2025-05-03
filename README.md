📄 OCR Micro‑service Suite

Bộ ứng dụng trích xuất văn bản (OCR) đa nền tảng, tách rời API (FastAPI) và Front‑End (Streamlit), sử dụng mô hình Mistral (local .gguf hoặc Cloud API). Dự án hỗ trợ chạy cục bộ, Docker‑Compose và triển khai CI/CD qua GitLab CI.

TL;DR: docker compose -f docker/docker-compose.yaml up --build → mở http://localhost:8501.



✨ Tính năng

Kiến trúc micro‑service

api/ : FastAPI REST – nhận file/URL, trả về JSON OCR.

fe/ : Streamlit UI – upload, so sánh, chỉnh sửa & tải kết quả.

Ba chế độ nhận diện local‑7b · local‑14b · cloud (qua MISTRAL_API_KEY).

Upload đa định dạng PDF/PNG/JPG/JPEG, hỗ trợ kéo‑thả nhiều file.

Chỉnh sửa trực tiếp & tải xuống TXT / Markdown / JSON / ZIP phiên.

Docker hoá : một lệnh khởi chạy toàn bộ stack (API + FE + worker).

CI/CD : .gitlab-ci.yml build image, chạy test & deploy.

🚀 Khởi chạy nhanh

0. Thiết lập môi trường Python

Yêu cầu Python ≥ 3.10.

# (a) Dùng venv mặc định
```
python -m venv .venv
```
# macOS / Linux
```
source .venv/bin/activate
```
# Windows (PowerShell)
```
.venv\Scripts\Activate.ps1
```

# (b) Hoặc dùng Conda
```
conda create -n ocr python=3.10
conda activate ocr
```
1. Tái sử dụng mã nguồn & cấu hình

# Clone

```
git clone https://github.com/ruangongming/ocr-doc.git
cd ocr-doc
```

# Tạo file .env
```
cp config/.env.sample config/.env
```

2. Cài phụ thuộc Python

requirements.txt gom tất cả thư viện chung cho API và FE.

```
pip install --upgrade pip
pip install -r requirements.txt
```


3. Chạy bằng Docker Compose (production‑like)

docker compose -f docker/docker-compose.yaml up --build

FE: http://localhost:8501

API: http://localhost:8000/docs (Swagger UI)

4. Chạy thủ công (môi trường phát triển)

# API – Tab 1
```
cd api
uvicorn app:app --reload --port 8000
```

# FE – Tab 2
```
cd fe
export API_URL=http://localhost:8000   # Windows: set API_URL=http://localhost:8000
streamlit run main.py
```

☝️ One‑file demo (tuỳ chọn)

Muốn thử nhanh tất cả trong một, chỉ cần:

streamlit run stand.py

Ứng dụng sẽ tự khởi tạo cả OCR và giao diện.

🗂 Cấu trúc dự án
```
.
├── api/                  # FastAPI service
│   └── app.py
├── fe/                   # Streamlit front‑end
│   └── main.py
├── config/
│   ├── .env              # Biến môi trường (không commit)
│   └── .env.sample
├── docker/
│   └── docker-compose.yaml
├── requirements.txt      # Phụ thuộc chung
├── stand.py              # Phiên bản Streamlit đơn lẻ (legacy)
├── .gitlab-ci.yml        # Pipeline CI/CD
└── README.md
```
🔧 Biến môi trường quan trọng (config/.env)

Tên biến

Mô tả

Giá trị mẫu
```
MISTRAL_API_KEY
```
Khoá truy cập Mistral Cloud
```
sk‑...

OCR_MODEL_7B

Đường dẫn .gguf của model 7B

models/7B.gguf

OCR_MODEL_14B

Đường dẫn .gguf của model 14B

models/14B.gguf
```
```
API_PORT

Cổng phục vụ FastAPI

8000

FE_PORT

Cổng phục vụ Streamlit

8501
```
```
♾️ CI/CD (GitLab)

Pipeline gồm 3 stage chính:

test – chạy pytest + ruff.

build – đóng gói image Docker, đẩy lên Registry.

deploy – triển khai tới server qua SSH.

Tuỳ chỉnh trong .gitlab-ci.yml.
```
```
🗺️ Lộ trình tương lai

```

Đóng góp ý tưởng bằng Issue / Merge‑Request ❤️

🤝 Đóng góp

Fork & tạo nhánh feature.

Chạy pre-commit install.

Viết test kèm theo.

Mở MR kèm mô tả chi tiết.

📜 License

MIT © 2025 [Nguyen Cong Minh]

