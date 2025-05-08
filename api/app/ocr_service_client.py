import os
import requests
from fastapi import HTTPException
from ocr_doc_utils import utils

logger = utils.setup_logging()

# URL đến OCR-service (có thể override qua ENV)
OCR_URL = utils.get_env("OCR_SERVICE_URL", "http://ocr-service:9000/process")

def call_ocr(raw_bytes: bytes) -> dict:
    """
    Gửi raw bytes lên OCR-service, trả về dict JSON đầy đủ:
      {
        "text": ...,
        "clean": ...,
        "page_count": ...,
        "confidence": ...,
        ...
      }
    Raise HTTPException nếu service lỗi.
    """
    try:
        resp = requests.post(
            OCR_URL,
            files={"file": ("upload", raw_bytes)},
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error("OCR-service HTTP error: %s", e)
        raise HTTPException(status_code=502, detail="Không gọi được OCR engine")
    except ValueError as e:
        logger.error("OCR-service returned invalid JSON: %s", e)
        raise HTTPException(status_code=502, detail="OCR engine trả về dữ liệu không hợp lệ")
