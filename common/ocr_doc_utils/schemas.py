from typing import Dict, Any
from pydantic import BaseModel

class OCRResponse(BaseModel):
    """
    Cấu trúc response trả về từ OCR service, phù hợp với cách stand.py trả về kết quả.
    """
    text: str  # Văn bản tinh chỉnh
    markdown: str  # Format markdown
    raw_json: Dict[str, Any]  # Dữ liệu gốc bao gồm metadata phong phú: page_count, results, processing_time_seconds, v.v.
