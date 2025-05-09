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
    /* Ẩn tất cả các nút hiển thị mật khẩu */
    button[title="Show password"],
    button[title="Show password text"],
    div[data-testid="stPasswordField"] button,
    div[data-testid="stTextInput"] button,
    input[type="password"] ~ button {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        width: 0 !important;
        height: 0 !important;
        position: absolute !important;
        pointer-events: none !important;
    }
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

# Kiểm tra tính hợp lệ của API key
def validate_api_key(api_key):
    try:
        # Gửi request kiểm tra đến API
        response = requests.post(
            "http://api:8000/ocr/validate",
            json={"api_key": api_key}
        )
        
        # Kiểm tra kết quả
        if response.status_code == 200:
            data = response.json()
            return data.get("valid", False)
        return False
    except Exception as e:
        st.error(f"Lỗi kiểm tra API key: {str(e)}")
        return False

# ============================================================
# Khởi tạo session_state mặc định
# ============================================================

st.session_state.setdefault("history", {})         # id → {names, previews, results}
st.session_state.setdefault("history_list", [])
st.session_state.setdefault("current_session", None)
st.session_state.setdefault("ocr_running", False)
st.session_state.setdefault("zip_buffer", None)
st.session_state.setdefault("zip_name", None)
st.session_state.setdefault("custom_api_key", "")
st.session_state.setdefault("use_custom_api_key", False)

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
        key="ocr_method",
        help="Lựa chọn phương pháp OCR!"
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
        default_api_key = os.getenv("MISTRAL_API_KEY", "")
        
        # Thêm chức năng thay đổi API key
        change_api = st.checkbox("Thay đổi API Key", value=st.session_state.get("change_api_key", False))
        
        # Kiểm tra nếu trạng thái checkbox thay đổi
        if change_api != st.session_state.get("change_api_key", False):
            # Nếu vừa mới check, reset giá trị input
            if change_api:
                st.session_state["temp_api_key"] = ""
            st.session_state["change_api_key"] = change_api
        
        # Hiển thị API key đã được cấu hình hoặc ô nhập API key mới
        if change_api:
            # Hiển thị ô nhập API key mới
            custom_api_key = st.text_input(
                "API Key:", 
                value=st.session_state.get("temp_api_key", ""),
                type="password", 
                key="input_custom_api_key",
                help="API Key đã được cấu hình, không hiển thị!"
            )
            
            # Lưu giá trị tạm thời
            st.session_state["temp_api_key"] = custom_api_key
            
            if custom_api_key and custom_api_key != st.session_state.get("custom_api_key", ""):
                # Tự động kiểm tra khi API key thay đổi
                is_valid = validate_api_key(custom_api_key)
                if is_valid:
                    st.session_state["custom_api_key"] = custom_api_key
                    st.session_state["use_custom_api_key"] = True
                    # Tự động ẩn ô input sau khi nhập thành công
                    st.session_state["change_api_key"] = False
                    st.session_state["temp_api_key"] = ""
                    st.success("API Key hợp lệ và đã được áp dụng!")
                    st.rerun()  # Rerun để cập nhật UI ngay lập tức
                else:
                    st.error("API Key không hợp lệ, vui lòng kiểm tra lại!")
        else:
            # Hiển thị API key đã được cấu hình với help text
            if default_api_key or st.session_state.get("use_custom_api_key", False):
                st.text_input(
                    "API Key:", 
                    value="••••••••••••••••••••••••",
                    disabled=True,
                    key="api_key_display",
                    help="API Key đã được cấu hình, không hiển thị!"
                )
            else:
                st.error("Thiếu API Key trong file .env")
        
        # Sử dụng API key nào
        api_key = st.session_state.get("custom_api_key", "") if st.session_state.get("use_custom_api_key", False) else default_api_key

    st.markdown("---")

    # ---- Nguồn dữ liệu ----
    st.subheader("Nguồn Tải lên")
    source_type = st.radio("Loại nguồn:", ["Upload File", "URL"], key="source_type")

    uploaded_files, raw_urls = [], ""
    if source_type == "Upload File":
        # Lấy trạng thái trước đó để biết khi nào số lượng file thay đổi
        prev_upload_count = st.session_state.get("prev_upload_count", 0)
        
        uploaded_files = st.file_uploader(
            "Chọn PDF/Ảnh", accept_multiple_files=True, type=["pdf", "png", "jpg", "jpeg"]
        )
        
        # Hiển thị số lượng file đã upload
        if uploaded_files:
            current_count = len(uploaded_files)
            # Hiển thị thông báo nếu số lượng file thay đổi
            if current_count != prev_upload_count:
                st.session_state["prev_upload_count"] = current_count
                # Sử dụng success message thay vì toast
                st.success(f"Đã tải lên {current_count} file")
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
        (ocr_method == "Mistral OCR (API)" and not (st.session_state.get("custom_api_key", "") if st.session_state.get("use_custom_api_key", False) else default_api_key))
    )
    if st.button("Thực hiện OCR", disabled=run_disabled):
        st.session_state["zip_buffer"] = None
        st.session_state["zip_name"] = None
        st.session_state["ocr_running"] = True
        
        # Lưu API key hiện tại vào session state để sử dụng khi gọi OCR
        if ocr_method == "Mistral OCR (API)":
            st.session_state["current_api_key"] = st.session_state.get("custom_api_key", "") if st.session_state.get("use_custom_api_key", False) else default_api_key
        
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
# Preview của sources (nếu chưa chạy và không có kết quả hiển thị)
# ============================================================

preview_container = st.container()
show_preview = sources and not st.session_state["ocr_running"] and not st.session_state.get("current_session")

if show_preview:
    with preview_container:
        st.markdown("---"); st.header("Xem trước nguồn")
        
        # Tạo list tên nguồn cho selectbox
        source_names = []
        for i, src in enumerate(sources, 1):
            if isinstance(src, str):
                name = os.path.basename(src)
            else:
                name = src.name if hasattr(src, "name") else f"File {i}"
            source_names.append(name)
        
        # Nếu có nhiều nguồn, sử dụng selectbox để chọn nguồn xem trước
        if len(sources) > 1:
            st.write(f"**Số nguồn: {len(sources)}**")
            selected_idx = st.selectbox(
                "Chọn nguồn để xem trước:",
                range(len(sources)),
                format_func=lambda i: source_names[i],
                key="preview_selectbox"
            )
            selected_sources = [sources[selected_idx]]
            st.write(f"**Đang xem: {source_names[selected_idx]}**")
        else:
            selected_sources = sources
        
        # Hiển thị nguồn được chọn
        for i, src in enumerate(selected_sources):
            if isinstance(src, str):
                prev = src
                name = os.path.basename(src)
            else:
                raw = src.read(); src.seek(0)
                prev = build_data_uri(raw, src.type)
                name = src.name if hasattr(src, "name") else f"File {i+1}"
            
            # Tạo card với container để hiển thị file
            if len(sources) == 1:  # Chỉ hiển thị tên file khi không có selectbox
                st.write(f"**File: {name}**")
            
            preview_col = st.container()
            with preview_col:
                if prev.lower().endswith(".pdf") or prev.startswith("data:application/pdf"):
                    # Sử dụng layout toàn màn hình cho PDF với chiều cao lớn hơn
                    st.markdown(
                        f"""
                        <div style="width:100%; height:90vh; overflow:hidden; border:1px solid #ccc; border-radius:5px; margin-bottom:20px;">
                            <iframe src="{prev}" width="100%" height="100%" 
                                style="transform:scale(1); transform-origin:top left; border:none;"
                                allowfullscreen></iframe>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                else:
                    # Hiển thị ảnh với kích thước tối đa
                    st.image(prev, use_container_width=True)
                    st.markdown(
                        """
                        <div style="text-align:center; margin-top:-15px; margin-bottom:15px;">
                            <small>💡 Nhấn vào ảnh để xem phóng to</small>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
else:
    preview_container.empty()

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
        name = src.name if hasattr(src, "name") else (os.path.basename(src) if isinstance(src, str) else f"file_{i}")
        try:
            if isinstance(src, str):  # URL
                with st.spinner(f"Tải {name} từ URL..."):
                    # Gửi URL trực tiếp đến API thay vì tải trước
                    res = requests.post(
                        API_URL,
                        data={
                            "url": src,
                            "api_key": st.session_state.get("current_api_key", "")
                        }
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
                    data = {"api_key": st.session_state.get("current_api_key", "")}
                    res = requests.post(
                        API_URL,
                        files=files,
                        data=data
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
    
    # Thêm selectbox để dễ dàng chọn nguồn khi có nhiều kết quả
    if len(data["names"]) > 1:
        st.write(f"**Số kết quả: {len(data['names'])}**")
        selected_idx = st.selectbox(
            "Chọn nguồn để xem kết quả:",
            range(len(data["names"])),
            format_func=lambda i: data["names"][i],
            key="results_selectbox"
        )
        # Hiển thị chỉ nguồn được chọn
        selected_indices = [selected_idx]
        st.write(f"**Đang xem: {data['names'][selected_idx]}**")
    else:
        # Hiển thị tất cả nếu chỉ có 1 nguồn
        selected_indices = range(len(data["names"]))
    
    # Hiển thị cho mỗi nguồn được chọn
    for selected_idx in selected_indices:
        fname = data["names"][selected_idx]
        prev = data["previews"][selected_idx]
        text = data["results"][fname]

        # Chỉ hiển thị số nguồn nếu không có selectbox
        if len(data["names"]) == 1:
            st.markdown(f"### Nguồn: {fname}")
        
        tab1, tab2, tab3 = st.tabs(["Gốc", "So sánh", "Tải xuống / Chỉnh sửa"])

        # ---------- Tab Gốc ----------
        with tab1:
            if prev.lower().endswith(".pdf") or "application/pdf" in prev:
                st.markdown(
                    f"""
                    <div style="width:100%; height:90vh; overflow:hidden; border:1px solid #ccc; border-radius:5px; margin-bottom:20px;">
                        <iframe src="{prev}" width="100%" height="100%" 
                            style="transform:scale(1); transform-origin:top left; border:none;"
                            allowfullscreen></iframe>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            else:
                st.image(prev, use_container_width=True)
                st.markdown(
                    """
                    <div style="text-align:center; margin-top:-15px; margin-bottom:15px;">
                        <small>💡 Nhấn vào ảnh để xem phóng to</small>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # ---------- Tab So sánh ----------
        with tab2:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**File gốc**")
                if prev.lower().endswith(".pdf") or "application/pdf" in prev:
                    st.markdown(
                        f"""
                        <div style="width:100%; height:70vh; overflow:hidden; border:1px solid #ccc; border-radius:5px;">
                            <iframe src="{prev}" width="100%" height="100%" 
                                style="transform:scale(1); transform-origin:top left; border:none;"
                                allowfullscreen></iframe>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                else:
                    st.image(prev, use_container_width=True)
            with c2:
                st.markdown("**Text OCR**")
                # Sử dụng container có thể cuộn với chiều cao phù hợp với khung PDF
                st.markdown(
                    f"""
                    <div style="width:100%; height:70vh; overflow:auto; border:1px solid #ccc; border-radius:5px; padding:10px; font-family:monospace; white-space:pre-wrap;">
                    {text.replace("<", "&lt;").replace(">", "&gt;")}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # ---------- Tab Tải xuống / Chỉnh sửa ----------
        with tab3:
            edited_key = f"edited_{st.session_state['current_session']}_{selected_idx}"
            edited_text = st.text_area("Chỉnh sửa nội dung:", text, height=400, key=edited_key)

            # Chọn định dạng → tự tải
            fmt_key = f"fmt_{st.session_state['current_session']}_{selected_idx}"
            fmt = st.selectbox("Định dạng tải xuống", ["TXT", "MD", "JSON"], key=fmt_key)

            if fmt == "TXT":
                bytes_data = edited_text.encode(); mime, ext = "text/plain", "txt"
            elif fmt == "MD":
                bytes_data = edited_text.encode(); mime, ext = "text/markdown", "md"
            else:
                bytes_data = json.dumps({"result": edited_text}, ensure_ascii=False, indent=2).encode(); mime, ext = "application/json", "json"

            # Auto-download khi đổi fmt (dựa trên state so sánh)
            last_key = f"last_fmt_{st.session_state['current_session']}_{selected_idx}"
            if st.session_state.get(last_key) != fmt:
                st.session_state[last_key] = fmt
                auto_download(bytes_data, mime, f"{os.path.splitext(fname)[0]}.{ext}")

            # Hiển thị link/nút dự phòng
            st.download_button(
                label=f"Tải {ext.upper()} (thủ công)", data=bytes_data,
                file_name=f"{os.path.splitext(fname)[0]}.{ext}", mime=mime,
                key=f"dl_btn_{selected_idx}_{ext}"
            )
