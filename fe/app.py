# fe/app.py
import streamlit as st
import requests
import json
import io
import base64
import zipfile
import uuid
import datetime
import os
import re
from dotenv import load_dotenv

# Nạp biến môi trường từ file .env
load_dotenv()

API_URL = "http://api:8000/ocr"

# ============================================================
# Cấu hình trang + CSS nhỏ
# ============================================================
st.set_page_config(layout="wide", page_title="Ứng dụng OCR", page_icon="📄")

st.markdown(
    """
    <style>
    .reportview-container .main .block-container{max-width:100%!important; padding:1rem 2rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# Tiện ích chung
# ============================================================

def show_toast(msg: str, dur: int = 3000):
    st.toast(msg, icon="ℹ️")

def build_data_uri(raw: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"

# Auto‑download helper (inject HTML + JS click)
def auto_download(bytes_data: bytes, mime: str, filename: str):
    b64 = base64.b64encode(bytes_data).decode()
    element_id = f"dl_{uuid.uuid4().hex}"
    href = f'<a id="{element_id}" href="data:{mime};base64,{b64}" download="{filename}"></a>'
    js = f"<script>document.getElementById('{element_id}').click();</script>"
    st.markdown(href + js, unsafe_allow_html=True)

# ============================================================
# Khởi tạo session_state mặc định
# ============================================================

st.session_state.setdefault("history", {})         # id → {names, previews, results}
st.session_state.setdefault("history_list", [])
st.session_state.setdefault("current_session", None)
st.session_state.setdefault("ocr_running", False)
st.session_state.setdefault("zip_buffer", None)
st.session_state.setdefault("zip_name", None)

# ============================================================
# Tiêu đề & mô tả
# ============================================================

st.title("Ứng dụng OCR cho PDF và Hình ảnh")
with st.expander("Giới thiệu"):
    st.markdown(
        "Ứng dụng trích xuất văn bản từ PDF/ảnh bằng Mistral OCR.\n"
        "- Hỗ trợ nhập URL (.pdf/.png/.jpg/.jpeg) hoặc upload file.\n"
        "- Mỗi lần chạy sinh phiên (`sess_YYYYMMDD_HHMMSS`) và lưu lịch sử.\n"
        "- Chọn phiên trong sidebar để xem lại & tải xuống.\n"
        "- Chọn định dạng trong tab **Tải xuống / Chỉnh sửa** là tự tải file."
    )

# ============================================================
# Sidebar: Cấu hình OCR, nguồn dữ liệu, phiên, tải zipfile
# ============================================================

with st.sidebar:
    # ---- Cấu hình OCR ----
    st.header("Cấu hình OCR")
    
    # Đọc OCR_MODE từ .env
    default_ocr_mode = os.getenv("OCR_MODE", "api")
    ocr_method = st.selectbox(
        "Phương pháp OCR:", 
        ["Mistral OCR (API)", "Mistral OCR (Local)"], 
        index=0 if default_ocr_mode == "api" else 1,
        key="ocr_method"
    )

    # Xử lý tùy theo phương pháp được chọn
    if ocr_method == "Mistral OCR (Local)":
        # Các model mặc định
        models = {
            "mistral-7b": "/models/mistral/7B.gguf",
            "mistral-small": "/models/gguf/mistral-small.gguf",
            "mistral-medium": "/models/gguf/mistral-medium.gguf",
        }
        
        # Nếu có đường dẫn model trong .env, thêm vào
        local_model_path = os.getenv("LOCAL_MODEL_PATH")
        if local_model_path:
            model_name = os.path.basename(local_model_path)
            models[model_name] = local_model_path
            
        local_model = st.selectbox("Mô hình Local:", list(models), key="local_model")
        st.markdown(f"**Đường dẫn:** `{models[local_model]}`")
    else:
        # Lấy API key từ .env
        api_key = os.getenv("MISTRAL_API_KEY", "")
        api_key_displayed = st.text_input(
            "API Key:", 
            value=api_key,
            type="password", 
            key="api_key", 
            disabled=True,
            help="API Key được cấu hình trong file .env"
        )
        if not api_key:
            st.error("Thiếu API Key trong file .env")

    st.markdown("---")

    # ---- Nguồn dữ liệu ----
    st.subheader("Nguồn Tải lên")
    source_type = st.radio("Loại nguồn:", ["Upload File", "URL"], key="source_type")

    uploaded_files, raw_urls = [], ""
    if source_type == "Upload File":
        uploaded_files = st.file_uploader(
            "Chọn PDF/Ảnh", accept_multiple_files=True, type=["pdf", "png", "jpg", "jpeg"]
        )
    else:
        raw_urls = st.text_area(
            "URL (.pdf/.png/.jpg/.jpeg):", 
            key="raw_urls", 
            height=150,
            placeholder="https://example.com/document.pdf\nhttps://example.com/image.jpg"
        )
        if raw_urls:
            urls = re.findall(r"https?://\S+?\.(?:pdf|png|jpe?g)", raw_urls, flags=re.I)
            if urls:
                st.success(f"Đã phát hiện {len(urls)} URL hợp lệ")
            else:
                st.warning("Không tìm thấy URL hợp lệ")

    # ---- Chuẩn bị danh sách sources ----
    sources = uploaded_files if source_type == "Upload File" else (
        re.findall(r"https?://\S+?\.(?:pdf|png|jpe?g)", raw_urls, flags=re.I) if raw_urls else []
    )
    
    # ---- Nút thực thi OCR ----
    run_disabled = (
        not sources or 
        st.session_state["ocr_running"] or 
        (ocr_method == "Mistral OCR (API)" and not api_key)
    )
    if st.button("Thực hiện OCR", disabled=run_disabled):
        st.session_state["zip_buffer"] = None
        st.session_state["zip_name"] = None
        st.session_state["ocr_running"] = True
        st.rerun()

    # ---- Chọn phiên lịch sử ----
    if st.session_state["history_list"]:
        sess_opts = st.session_state["history_list"][::-1]  # mới nhất trước
        sel_sess = st.selectbox(
            "Chọn phiên kết quả:", sess_opts,
            index=sess_opts.index(st.session_state["current_session"]) if st.session_state["current_session"] in sess_opts else 0,
            key="sess_select"
        )
        if sel_sess != st.session_state.get("current_session"):
            st.session_state["current_session"] = sel_sess
            st.rerun()

    # ---- Tải ZIP toàn phiên ----
    if st.session_state.get("zip_buffer"):
        st.download_button(
            "Tải ZIP kết quả phiên", st.session_state["zip_buffer"].getvalue(),
            file_name=f"{st.session_state['zip_name']}.zip", mime="application/zip", key="download_zip_full"
        )

# ============================================================
# Preview của sources (nếu chưa chạy)
# ============================================================

preview_container = st.container()
if sources and not st.session_state["ocr_running"]:
    with preview_container:
        st.markdown("---"); st.header("Xem trước nguồn")
        for src in sources:
            if isinstance(src, str):
                prev = src
            else:
                raw = src.read(); src.seek(0)
                prev = build_data_uri(raw, src.type)
            if prev.lower().endswith(".pdf") or prev.startswith("data:application/pdf"):
                st.markdown(f'<iframe src="{prev}" width="100%" height="400"></iframe>', unsafe_allow_html=True)
            else:
                st.image(prev)

# ============================================================
# Thực hiện OCR  (khi ocr_running == True)
# ============================================================

if st.session_state["ocr_running"] and sources:
    preview_container.empty()
    sess_id = f"sess_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    names, previews, results = [], [], {}

    progress = st.progress(0)
    total = len(sources)

    for i, src in enumerate(sources, 1):
        name = src.name if hasattr(src, "name") else os.path.basename(src) if isinstance(src, str) else f"file_{i}"
        try:
            if isinstance(src, str):  # URL
                with st.spinner(f"Tải {name} từ URL..."):
                    # Gửi URL trực tiếp đến API thay vì tải trước
                    res = requests.post(
                        API_URL,
                        data={"url": src}
                    )
                    res.raise_for_status()
                    data = res.json()
                    text = data.get("text", "")
                    prev = src
            else:  # File upload
                raw = src.read(); src.seek(0)
                prev = build_data_uri(raw, src.type)
                
                # OCR qua API
                with st.spinner(f"OCR {name} ..."):
                    files = {"file": (name, raw, src.type)}
                    res = requests.post(
                        API_URL,
                        files=files
                    )
                    res.raise_for_status()
                    data = res.json()
                    text = data.get("text", "")

            names.append(name); previews.append(prev); results[name] = text
        except Exception as e:
            show_toast(f"Lỗi {name}: {e}")
        finally:
            progress.progress(i / total)

    progress.empty()

    # Lưu lịch sử
    st.session_state["history"][sess_id] = {
        "names": names, "previews": previews, "results": results
    }
    st.session_state["history_list"].append(sess_id)
    st.session_state["current_session"] = sess_id

    # Đóng gói ZIP toàn phiên
    try:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for n, txt in results.items():
                base = os.path.splitext(n)[0]
                zf.writestr(f"{base}.txt", txt)
                zf.writestr(f"{base}.md", txt)
                zf.writestr(f"{base}.json", json.dumps({"result": txt}, ensure_ascii=False, indent=2))
        zip_buf.seek(0)
        st.session_state["zip_buffer"] = zip_buf
        st.session_state["zip_name"] = sess_id
        show_toast("OCR hoàn thành!")
    except Exception as e:
        show_toast(f"Lỗi đóng ZIP: {e}")

    st.session_state["ocr_running"] = False
    st.rerun()

# ============================================================
# Hiển thị kết quả phiên hiện tại
# ============================================================

if st.session_state.get("current_session"):
    data = st.session_state["history"][st.session_state["current_session"]]

    st.markdown("---"); st.header(f"Kết quả phiên: {st.session_state['current_session']}")

    for idx, fname in enumerate(data["names"], 1):
        prev = data["previews"][idx - 1]
        text = data["results"][fname]

        st.markdown(f"### Nguồn {idx}: {fname}")
        tab1, tab2, tab3 = st.tabs(["Gốc", "So sánh", "Tải xuống / Chỉnh sửa"])

        # ---------- Tab Gốc ----------
        with tab1:
            if prev.lower().endswith(".pdf") or "application/pdf" in prev:
                st.markdown(f'<iframe src="{prev}" width="100%" height="800"></iframe>', unsafe_allow_html=True)
            else:
                st.image(prev)

        # ---------- Tab So sánh ----------
        with tab2:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**File gốc**")
                if prev.lower().endswith(".pdf") or "application/pdf" in prev:
                    st.markdown(f'<iframe src="{prev}" width="100%" height="400"></iframe>', unsafe_allow_html=True)
                else:
                    st.image(prev)
            with c2:
                st.markdown("**Text OCR**")
                st.code(text, language="markdown")

        # ---------- Tab Tải xuống / Chỉnh sửa ----------
        with tab3:
            edited_key = f"edited_{st.session_state['current_session']}_{idx}"
            edited_text = st.text_area("Chỉnh sửa nội dung:", text, height=400, key=edited_key)

            # Chọn định dạng → tự tải
            fmt_key = f"fmt_{st.session_state['current_session']}_{idx}"
            fmt = st.selectbox("Định dạng tải xuống", ["TXT", "MD", "JSON"], key=fmt_key)

            if fmt == "TXT":
                bytes_data = edited_text.encode(); mime, ext = "text/plain", "txt"
            elif fmt == "MD":
                bytes_data = edited_text.encode(); mime, ext = "text/markdown", "md"
            else:
                bytes_data = json.dumps({"result": edited_text}, ensure_ascii=False, indent=2).encode(); mime, ext = "application/json", "json"

            # Auto-download khi đổi fmt (dựa trên state so sánh)
            last_key = f"last_fmt_{st.session_state['current_session']}_{idx}"
            if st.session_state.get(last_key) != fmt:
                st.session_state[last_key] = fmt
                auto_download(bytes_data, mime, f"{os.path.splitext(fname)[0]}.{ext}")

            # Hiển thị link/nút dự phòng
            st.download_button(
                label=f"Tải {ext.upper()} (thủ công)", data=bytes_data,
                file_name=f"{os.path.splitext(fname)[0]}.{ext}", mime=mime,
                key=f"dl_btn_{idx}_{ext}"
            )
