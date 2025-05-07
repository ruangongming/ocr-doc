"""
Đóng gói logic gọi model Mistral (local hoặc qua API).
Hiện tại mock trả 'dummy text' để bạn có thể test end‑to‑end
mà chưa cần model thật.
"""

from .postprocess import correct

def run_ocr(raw_bytes: bytes, mode: str = "mock") -> str:
    """
    mode = 'local' | 'api' | 'mock'
    Trả về chuỗi text đã hậu xử lý.
    """
    if mode == "mock":
        result = "Dummy OCR result for demo purpose."
    else:
        # TODO: gọi model thật ở đây
        result = "REAL OCR output here"

    return correct(result)

def convert_to_markdown(text: str) -> str:
    """Ví dụ chuyển plain text thành markdown (đơn giản)."""
    # Ở đây chỉ bọc ```txt``` cho minh hoạ
    return f"```txt\n{text}\n```"
