# api/app/main.py

import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from ocr_doc_utils import utils, postprocess, schemas
from .ocr_service_client import call_ocr

logger = utils.setup_logging()
app = FastAPI()

@app.post("/ocr", response_model=schemas.OCRResponse)
async def ocr_endpoint(file: UploadFile = File(...)):
    """
    1) Nhận file upload (bytes)
    2) Gọi OCR-service qua call_ocr
    3) Lấy text đã clean (hoặc tự clean nếu chưa có)
    4) Lấy markdown (hoặc tự tạo nếu chưa có)
    5) Trả về OCRResponse(text, markdown, raw_json)
    """
    raw = await file.read()

    # --- gọi service ---
    try:
        data = call_ocr(raw)
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

    return schemas.OCRResponse(
        text=clean,
        markdown=md,
        raw_json=raw_json
    )
