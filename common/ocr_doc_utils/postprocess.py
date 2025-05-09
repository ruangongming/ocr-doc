import re

def correct(text: str) -> str:
    """
    Hàm hậu xử lý, làm sạch và cải thiện chất lượng văn bản OCR.
    """
    if not text:
        return ""
        
    # Loại bỏ khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text)
    
    # Loại bỏ dòng trống quá nhiều
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Sửa lỗi chung trong OCR
    corrections = [
        (r'l\s?([^\w\s])\s?l', '1\\1'),  # l.l → 1.1
        (r'([0-9])\s*\.\s*([0-9])', '\\1.\\2'),  # Fix số thập phân
        (r'([a-z])\s*\-\s*([a-z])', '\\1-\\2'),  # Fix từ ghép
    ]
    
    for pattern, replacement in corrections:
        text = re.sub(pattern, replacement, text)
    
    return text.strip()
