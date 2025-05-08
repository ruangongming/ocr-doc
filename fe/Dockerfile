# fe/Dockerfile

FROM python:3.13-slim

WORKDIR /app

# 1) Cài dependencies
COPY fe/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copy code frontend
COPY fe/ .

# 3) Expose & run Streamlit
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
