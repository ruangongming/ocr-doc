#api/app/ocr_service_client.py
import os
import requests
from fastapi import HTTPException
from ocr_doc_utils import utils

logger = utils.setup_logging()

# Must point at the `/ocr` endpoint on the OCR‐service
OCR_URL = utils.get_env("OCR_SERVICE_URL", "http://ocr-service:9000/ocr")

def call_ocr(raw_bytes: bytes, filename: str = "upload.pdf", content_type: str = None) -> dict:
    """
    Send raw bytes to OCR‐service and return its full JSON:
      {
        "text": ...,
        "clean": ...,
        "markdown": ...,
        "raw_json": {...}
      }
    Raises HTTPException if anything goes wrong.
    """
    try:
        # Determine content type if not provided
        if not content_type:
            if filename.lower().endswith('.pdf'):
                content_type = 'application/pdf'
            elif filename.lower().endswith(('.jpg', '.jpeg')):
                content_type = 'image/jpeg'
            elif filename.lower().endswith('.png'):
                content_type = 'image/png'
            else:
                content_type = 'application/octet-stream'
                
        # Include content type in the request
        files = {
            "file": (filename, raw_bytes, content_type)
        }
        
        # Add file hash to logging
        file_hash = utils.compute_file_hash(raw_bytes)
        file_info = utils.extract_file_info(filename)
        logger.info(f"Processing file: {filename}, size: {len(raw_bytes)} bytes, hash: {file_hash}, type: {content_type}")
        
        resp = requests.post(
            OCR_URL,
            files=files,
            timeout=60  # Increased timeout for larger files
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError as e:
        logger.error("Cannot connect to OCR service: %s", e)
        raise HTTPException(
            status_code=503,
            detail="OCR service không khả dụng. Vui lòng thử lại sau."
        )
    except requests.exceptions.Timeout as e:
        logger.error("OCR service timeout: %s", e)
        raise HTTPException(
            status_code=504,
            detail="OCR service xử lý quá lâu. Vui lòng thử lại sau."
        )
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            # Forward client errors
            detail = e.response.json().get("detail", str(e))
            raise HTTPException(status_code=400, detail=detail)
        else:
            logger.error("OCR-service HTTP error: %s", e)
            raise HTTPException(
                status_code=502,
                detail="Lỗi khi xử lý file. Vui lòng kiểm tra định dạng file."
            )
    except ValueError as e:
        logger.error("OCR-service returned invalid JSON: %s", e)
        raise HTTPException(
            status_code=502,
            detail="OCR service trả về dữ liệu không hợp lệ"
        )
    except Exception as e:
        logger.error("Unexpected error calling OCR service: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Lỗi không xác định. Vui lòng thử lại sau."
        )
