# api/main.py
# ------------------------------------------------------------
# FastAPI entrypoint for OCR‑API
# ------------------------------------------------------------
from pathlib import Path
import json
import logging

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .ocr_service import run_ocr, convert_to_markdown
from .schemas import OCRResponse
from .utils import new_session_dir

# ──────────────────── Logging ────────────────────────────────
logger = logging.getLogger(__name__)

# ──────────────────── FastAPI app ────────────────────────────
app = FastAPI(title="OCR‑API", version="0.1.0")

# ‑‑ (optional) cho phép FE Streamlit gọi từ http://localhost:8501
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # đổi thành ["http://localhost:8501"] khi cần hạn chế
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ──────────────────── Endpoints ──────────────────────────────
@app.post("/ocr", response_model=OCRResponse, summary="Nhận file & trả kết quả OCR")
async def ocr_endpoint(file: UploadFile = File(...)):
    """
    Nhận file (ảnh/PDF), chạy OCR, sinh 3 file (.txt/.md/.json)
    lưu vào volume `/data/<timestamp_uuid>/`, sau đó trả JSON
    chứa đường dẫn & preview (500 ký tự đầu).
    """
    try:
        raw = await file.read()
        text = run_ocr(raw, mode="mock")       # TODO: đổi mode 'local' | 'api'
        md   = convert_to_markdown(text)
    except Exception as e:
        logger.exception("OCR failed")
        raise HTTPException(status_code=500, detail=str(e))

    # ghi file ra volume /data
    outdir: Path = new_session_dir()
    txt_path  = outdir / "output.txt"
    md_path   = outdir / "output.md"
    json_path = outdir / "output.json"

    txt_path.write_text(text, encoding="utf-8")
    md_path.write_text(md,   encoding="utf-8")
    json_path.write_text(
        json.dumps({"text": text, "markdown": md}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    response = OCRResponse(
        session=outdir.name,
        preview=text[:500],
        paths={
            "txt":  str(txt_path),
            "md":   str(md_path),
            "json": str(json_path),
        },
    )

    return JSONResponse(content=response.model_dump())
