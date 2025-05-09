# ocr-service/server.py

import os
import io
import base64
import time
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Body, Header
from ocr_doc_utils import utils, postprocess, schemas
from pdf2image import convert_from_bytes
from mistralai import Mistral
import requests
from PIL import Image

logger = utils.setup_logging()
app = FastAPI()

# 1) Đọc API key từ biến môi trường
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
OCR_MODE = os.getenv("OCR_MODE", "api")  # api | local

if not MISTRAL_API_KEY and OCR_MODE == "api":
    raise RuntimeError("MISSING MISTRAL_API_KEY! Required when OCR_MODE=api")

# 2) Khởi tạo client
ocr_client = Mistral(api_key=MISTRAL_API_KEY) if OCR_MODE == "api" else None

@app.post("/ocr", response_model=schemas.OCRResponse)
async def do_ocr(
    file: UploadFile = File(...), 
    background_tasks: BackgroundTasks = None, 
    x_api_key: Optional[str] = Header(None)
):
    """
    Process a file (PDF or image) and extract text using OCR.
    Returns a structured OCRResponse with comprehensive metadata similar to stand.py.
    """
    start_time = time.time()  # Track processing time
    
    # Use custom API key if provided in header, otherwise use the default
    api_key_to_use = x_api_key or MISTRAL_API_KEY
    
    # Initialize client with the appropriate API key
    if OCR_MODE == "api":
        # Create client with potentially custom API key
        current_client = Mistral(api_key=api_key_to_use)
    else:
        current_client = ocr_client
    
    # 1) Đọc raw bytes
    data = await file.read()
    
    # 2) Tạo thư mục phiên mới
    session_dir = utils.new_session_dir("/data")
    in_path = os.path.join(session_dir, file.filename or "unnamed_file")
    with open(in_path, "wb") as f:
        f.write(data)
    
    # 3) Lấy thông tin file
    filename = file.filename or "unnamed_file"
    file_size = len(data)
    content_type = file.content_type or "application/octet-stream"
    
    # 4) Tạo data URI
    data_uri = f"data:{content_type};base64,{base64.b64encode(data).decode()}"
    
    try:
        # 5) Xác định loại document
        doc_type = "document_url" if content_type == "application/pdf" else "image_url"
        doc = {"type": doc_type, doc_type: data_uri}
        
        # 6) Gọi Mistral OCR API (giống stand.py)
        logger.info(f"Processing {filename} with Mistral OCR API")
        ocr_result = current_client.ocr.process(
            model="mistral-ocr-latest", 
            document=doc,
            include_image_base64=True
        )
        
        # 7) Lấy text từ kết quả - GIỮ ĐỊNH DẠNG
        texts = []
        for i, page in enumerate(ocr_result.pages):
            # Nếu có nhiều trang, đánh dấu rõ ràng ranh giới giữa các trang
            if len(ocr_result.pages) > 1:
                page_header = f"--- Trang {i+1}/{len(ocr_result.pages)} ---\n\n"
                texts.append(page_header + page.markdown)
            else:
                texts.append(page.markdown)
        
        # Kết hợp văn bản với ngắt trang rõ ràng
        combined_text = "\n\n" + "\n\n" + "\n\n".join(texts)
        
        # Áp dụng hậu xử lý nhưng giữ định dạng
        clean_text = postprocess.correct(combined_text)
        
        # 8) Tạo markdown có định dạng tốt hơn
        markdown = f"""```markdown
{clean_text}
```"""
        
        # 9) Chuẩn bị kết quả
        json_result = {
            "text": combined_text,
            "clean": clean_text,
            "page_count": len(ocr_result.pages),
            "results": texts,
            "processing_time_seconds": round(time.time() - start_time, 2),
            "filename": filename,
            "file_size_bytes": file_size,
            "timestamp": utils.get_timestamp(),
            "content_type": content_type
        }
        
        return schemas.OCRResponse(
            text=clean_text,
            markdown=markdown,
            raw_json=json_result
        )
        
    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        raise HTTPException(status_code=502, detail=f"OCR processing error: {str(e)}")

@app.post("/validate_api_key")
async def validate_api_key(data: Dict[str, str] = Body(...)):
    """
    Validate an API key with Mistral API.
    Returns 200 if the key is valid, 401 if it's invalid.
    """
    api_key = data.get("api_key")
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    
    try:
        # Create temporary client with the provided API key
        test_client = Mistral(api_key=api_key)
        
        # Try a lightweight request to verify the key
        # We'll just get models list as a simple verification
        response = test_client.models.list()
        
        # If we get here, the API key is valid
        return {"status": "valid", "message": "API key is valid"}
    except Exception as e:
        # Any exception means the key is invalid
        logger.error(f"Invalid API key: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid API key: {str(e)}")

@app.get("/health")
def health_check():
    """Check service health"""
    return {
        "status": "ok",
        "timestamp": utils.get_timestamp(),
        "mode": OCR_MODE
    }
