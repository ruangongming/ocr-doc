import os
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from ocr_doc_utils import utils, postprocess, schemas

from pdf2image import convert_from_bytes

logger = utils.setup_logging()
app = FastAPI()

@app.post("/process", response_model=schemas.OCRResponse)
async def process_image(file: UploadFile = File(...)):
    # 1) Đọc raw bytes
    raw = await file.read()

    # 2) Lưu tạm file gốc (nếu cần)
    session_dir = utils.new_session_dir("/data")
    in_path = os.path.join(session_dir, file.filename)
    with open(in_path, "wb") as f:
        f.write(raw)

    # 3) Nếu PDF, convert trang đầu
    ext = file.filename.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        try:
            pages = convert_from_bytes(raw)
            buf = io.BytesIO()
            pages[0].save(buf, format="PNG")
            payload = buf.getvalue()
        except Exception as e:
            logger.error("PDF→image conversion failed: %s", e)
            raise HTTPException(500, "PDF conversion error")
    else:
        payload = raw

    # 4) MOCK OCR (thay bằng gọi Mistral thật khi có client)
    try:
        # <<< STUB: bạn sẽ đổi sang gọi ocr_client khi sẵn sàng >>>
        text_raw = "Đây là kết quả OCR thô (mock)"
    except Exception as e:
        logger.error("OCR engine error: %s", e)
        raise HTTPException(502, "OCR engine error")

    # 5) Post‐process
    text_clean = postprocess.correct(text_raw)
    md = f"```txt\n{text_clean}\n```"

    # 6) Metadata trả về
    json_result = {
        "text": text_raw,
        "clean": text_clean,
        "page_count": 1,
    }

    return schemas.OCRResponse(
        text=text_clean,
        markdown=md,
        raw_json=json_result
    )
