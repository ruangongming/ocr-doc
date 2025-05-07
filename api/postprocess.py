"""
Các hàm hậu xử lý kết quả OCR.
Có thể cắm thêm spell‑checker, grammar, regex… sau này.
"""
import unicodedata, re

def correct(text: str) -> str:
    # Chuẩn hoá Unicode & xoá khoảng trắng dư
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[ \t]+\n", "\n", text)   # space trước \n
    text = re.sub(r"\n{3,}", "\n\n", text)   # quá 2 dòng trống
    return text
