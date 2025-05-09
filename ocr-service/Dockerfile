# ocr-service/Dockerfile

# ocr-service/Dockerfile

FROM python:3.13-slim

RUN apt-get update && apt-get install -y poppler-utils && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy và cài thư viện chung
COPY common /app/common
RUN pip install --no-cache-dir -e /app/common

# Copy requirements & cài dependencies service
COPY ocr-service/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy code và chạy
COPY ocr-service/server.py /app/
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9000"]

