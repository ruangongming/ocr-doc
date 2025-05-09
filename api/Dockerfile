# api/Dockerfile

# api/Dockerfile

FROM python:3.13-slim

WORKDIR /app

# Copy & install chung
COPY common /app/common
RUN pip install --no-cache-dir -e /app/common

# Copy requirements & cài
COPY api/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy code và chạy
COPY api/app /app/app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
