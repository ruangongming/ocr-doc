import streamlit as st
import requests

API_URL = "http://api:8000/ocr"

st.title("OCR Demo")
uploaded = st.file_uploader("Chọn ảnh/PDF", type=["jpg","png","pdf"])
if uploaded:
    with st.spinner("Đang xử lý…"):
        res = requests.post(API_URL, files={"file": uploaded.getvalue()})
        res.raise_for_status()
        data = res.json()

    st.subheader("Kết quả Text")
    st.code(data.get("text", ""))

    st.subheader("Markdown Preview")
    st.markdown(data.get("markdown", ""))

    # Luôn hiển thị JSON (dùng {} nếu None)
    st.subheader("Raw JSON")
    st.json(data.get("raw_json") or {})
