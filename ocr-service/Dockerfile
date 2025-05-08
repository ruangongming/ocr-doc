# ocr-service/Dockerfile

FROM python:3.13-slim

# Cài poppler-utils để pdf2image hoạt động
RUN apt-get update && \
    apt-get install -y poppler-utils && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) Cài dependencies
COPY ocr-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copy common và cài editable
COPY common /common
RUN pip install --no-cache-dir -e /common

# 3) Copy server code
COPY ocr-service/server.py .

EXPOSE 9000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9000"]
