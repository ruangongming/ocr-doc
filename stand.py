import streamlit as st
from PIL import Image
import requests, io, base64, json, time, os
from mistralai import Mistral  # Đảm bảo đã cài đặt client Mistral OCR API

# --- Cấu hình trang
st.set_page_config(layout="wide", page_title="Ứng dụng OCR", page_icon="📄")

# --- Tiêu đề
st.title("Ứng dụng OCR cho PDF và Hình ảnh")
with st.expander("Giới thiệu"):
    st.markdown("Ứng dụng này trích xuất văn bản từ PDF và ảnh bằng Mistral OCR.")

# --- Sidebar: Cấu hình và nhập liệu
with st.sidebar:
    st.header("Cấu hình OCR")
    ocr_method = st.selectbox('Chọn phương pháp OCR:', ['Mistral OCR (Local)', 'Mistral OCR (API)'])
    api_key = None
    if ocr_method == 'Mistral OCR (Local)':
        models = {'mistral-7b':'/models/mistral/7B.gguf', 'mistral-14b':'/models/mistral/14B.gguf'}
        choice = st.selectbox('Chọn mô hình cho Local:', list(models.keys()))
        st.markdown(f"**Đường dẫn:** `{models[choice]}`")
    else:
        api_key = st.text_input('Nhập API Key cho API:', type='password')
    st.markdown('---')
    st.subheader('Nguồn Tải lên')
    source_type = st.radio('Chọn nguồn:', ['Tải lên cục bộ','URL'])
    uploaded = None
    urls = ''
    if source_type == 'Tải lên cục bộ':
        uploaded = st.file_uploader('Chọn PDF hoặc ảnh', type=['pdf','png','jpg','jpeg'], accept_multiple_files=True)
    else:
        urls = st.text_area('Nhập URL (mỗi dòng một file)')
    # Nút kiểm tra và OCR
    check_file = st.button('Kiểm tra file')
    run_ocr = st.button('Thực hiện OCR')
    # Định dạng tải xuống
    fmt = st.selectbox('Định dạng tải xuống:', ['JSON','TXT','MD'])

# --- Helper

def fetch_url(url):
    try:
        r = requests.get(url); r.raise_for_status(); return r.content
    except Exception as e:
        st.error(f"Lỗi tải URL {url}: {e}")
        return None

# --- Kiểm tra file
if check_file:
    sources = urls.split('\n') if source_type=='URL' else uploaded
    if not sources:
        st.warning('Chưa có file hoặc URL nào.')
    else:
        st.success(f'Tìm thấy {len(sources)} nguồn.')

# --- Thực hiện OCR
if run_ocr:
    client = Mistral(api_key=api_key) if api_key else Mistral()
    st.session_state['results'] = []
    st.session_state['previews'] = []
    st.session_state['names'] = []
    sources = urls.split('\n') if source_type=='URL' else uploaded
    for src in sources:
        # đặt tên nguồn
        if isinstance(src, str) or source_type=='URL':
            name = os.path.basename(src.strip()) or src.strip()
        else:
            name = src.name
        st.session_state['names'].append(name)
        # preview data và document
        if isinstance(src, str) or source_type=='URL':
            data = src.strip(); preview_data = data
            doc_type = 'document_url' if data.lower().endswith('.pdf') else 'image_url'
            doc = {'type': doc_type, doc_type: data}
        else:
            raw = src.read(); mime = src.type; b64 = base64.b64encode(raw).decode()
            if mime=='application/pdf':
                doc = {'type':'document_url','document_url':f'data:application/pdf;base64,{b64}'}
                preview_data = doc['document_url']
            else:
                doc = {'type':'image_url','image_url':f'data:{mime};base64,{b64}'}
                preview_data = doc['image_url']
        st.session_state['previews'].append(preview_data)
        # call OCR
        with st.spinner(f'OCR {name}...'):
            try:
                resp = client.ocr.process(model='mistral-ocr-latest', document=doc, include_image_base64=True)
                pages = getattr(resp,'pages', resp if isinstance(resp,list) else [])
                text = '\n\n'.join(p.markdown for p in pages) if pages else ''
            except Exception as e:
                text = f'Error: {e}'
        st.session_state['results'].append(text)
    st.success('OCR hoàn thành!')

# --- Hiển thị kết quả với Tabs: Gốc | So sánh | Kết quả
if 'results' in st.session_state:
    for i, (name, preview, txt) in enumerate(zip(st.session_state['names'], st.session_state['previews'], st.session_state['results']), start=1):
        st.markdown(f"---\n## Nguồn: {name}")
        tab1, tab2, tab3 = st.tabs(["Gốc", "So sánh", "Kết quả"])
        with tab1:
            if preview.startswith('data:application/pdf') or preview.lower().endswith('.pdf'):
                st.markdown(f'<iframe src="{preview}" width="100%" height="500"></iframe>', unsafe_allow_html=True)
            else:
                st.image(preview)
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**File gốc**")
                if preview.startswith('data:application/pdf') or preview.lower().endswith('.pdf'):
                    st.markdown(f'<iframe src="{preview}" width="100%" height="300"></iframe>', unsafe_allow_html=True)
                else:
                    st.image(preview)
            with col2:
                st.markdown("**Text OCR**")
                st.code(txt, language='markdown')
        with tab3:
            st.markdown("**Kết quả trích xuất**")
            st.code(txt, language='markdown')
            # download
            if fmt=='JSON': data = json.dumps({'result':txt}, ensure_ascii=False)
            else: data = txt
            fname = f'Output_{name}.{fmt.lower()}'
            st.download_button(label=f'Tải xuống {fname}', data=data, file_name=fname, mime='application/octet-stream')
