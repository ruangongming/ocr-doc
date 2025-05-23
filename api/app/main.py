# api/app/main.py

import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from ocr_doc_utils import utils, postprocess, schemas
from .ocr_service_client import call_ocr, validate_api_key
import requests
from typing import Dict

logger = utils.setup_logging()
app = FastAPI()

# Thêm CORS middleware để frontend có thể gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/ocr", response_model=schemas.OCRResponse)
async def ocr_endpoint(
    file: UploadFile = File(None),
    url: str = Form(None),
    api_key: str = Form(None),
    x_api_key: str = Header(None)
):
    """
    1) Nhận file upload (bytes) hoặc URL
    2) Gọi OCR-service qua call_ocr
    3) Lấy text đã clean (hoặc tự clean nếu chưa có)
    4) Lấy markdown (hoặc tự tạo nếu chưa có)
    5) Trả về OCRResponse(text, markdown, raw_json)
    """
    if not file and not url:
        raise HTTPException(
            status_code=400,
            detail="Vui lòng cung cấp file upload hoặc URL"
        )
    
    # Prefer form data API key over header
    effective_api_key = api_key or x_api_key
    
    # Trường hợp URL
    if url:
        try:
            logger.info(f"Fetching file from URL: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            raw = response.content
            filename = url.split("/")[-1]
            content_type = response.headers.get("Content-Type", "application/octet-stream")
        except Exception as e:
            logger.error(f"Failed to fetch URL {url}: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Không thể tải file từ URL: {str(e)}"
            )
    # Trường hợp file upload
    else:
        filename = file.filename
        content_type = file.content_type
        raw = await file.read()

    # --- gọi service ---
    try:
        data = call_ocr(raw, filename=filename, content_type=content_type, api_key=effective_api_key)
    except HTTPException:
        # service trả HTTPException rồi, chỉ re-raise
        raise
    except Exception as e:
        logger.error("Call to OCR-service failed: %s", e)
        raise HTTPException(status_code=502, detail="OCR engine error")

    # --- xử lý text & markdown ---
    # nếu call_ocr đã trả về trường 'clean', ưu tiên dùng
    clean = data.get("clean") or postprocess.correct(data.get("text", ""))
    # nếu call_ocr đã trả 'markdown', ưu tiên dùng
    md = data.get("markdown") or f"```txt\n{clean}\n```"

    # --- chuẩn bị raw_json trả về ---
    # nếu service trả 'raw_json', dùng, nếu không thì toàn bộ dict
    raw_json = data.get("raw_json", data)
    
    # Thêm thông tin file vào raw_json
    if isinstance(raw_json, dict):
        raw_json.update({
            "filename": filename,
            "content_type": content_type,
            "source_type": "url" if url else "upload",
            "timestamp": utils.get_timestamp(),
            "file_size_bytes": len(raw)
        })

    return schemas.OCRResponse(
        text=clean,
        markdown=md,
        raw_json=raw_json
    )

@app.post("/ocr/validate")
async def validate_api_key_endpoint(data: Dict[str, str] = Body(...)):
    """
    Validate an API key by making a lightweight call to the OCR service
    
    Body:
    {
        "api_key": "your-api-key"
    }
    
    Returns:
    {
        "valid": true/false,
        "message": "Success or error message"
    }
    """
    api_key = data.get("api_key")
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    
    try:
        is_valid = validate_api_key(api_key)
        if is_valid:
            return {"valid": True, "message": "API key is valid"}
        else:
            return {"valid": False, "message": "API key is invalid"}
    except Exception as e:
        logger.error(f"API key validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error validating API key: {str(e)}")

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok"}
