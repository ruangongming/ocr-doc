import re

def correct(text: str) -> str:
    """
    Hàm hậu xử lý, làm sạch và cải thiện chất lượng văn bản OCR.
    Giữ nguyên định dạng từ văn bản gốc càng nhiều càng tốt.
    """
    if not text:
        return ""
        
    # Loại bỏ khoảng trắng thừa trong một dòng nhưng giữ nguyên ngắt dòng
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Loại bỏ khoảng trắng thừa trong mỗi dòng
        cleaned_line = re.sub(r'\s+', ' ', line.strip())
        cleaned_lines.append(cleaned_line)
    
    # Giữ nguyên cấu trúc đoạn văn của văn bản gốc
    result = ""
    current_paragraph = []
    
    for line in cleaned_lines:
        if line.strip():
            current_paragraph.append(line)
        else:
            if current_paragraph:
                result += "\n".join(current_paragraph) + "\n\n"
                current_paragraph = []
            else:
                result += "\n"
    
    if current_paragraph:
        result += "\n".join(current_paragraph)
    
    # Sửa lỗi chung trong OCR
    corrections = [
        (r'l\s?([^\w\s])\s?l', '1\\1'),  # l.l → 1.1
        (r'([0-9])\s*\.\s*([0-9])', '\\1.\\2'),  # Fix số thập phân
        (r'([a-z])\s*\-\s*([a-z])', '\\1-\\2'),  # Fix từ ghép
    ]
    
    for pattern, replacement in corrections:
        result = re.sub(pattern, replacement, result)
    
    # Thêm định dạng cho các tiêu đề dễ nhận biết
    result = re.sub(r'^(CHÍNH PHỦ|CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM|NGHỊ ĐỊNH)$', r'\n\1\n', result, flags=re.MULTILINE)
    
    # Định dạng đặc biệt cho tiêu đề Điều, Khoản, Mục
    result = re.sub(r'^(Điều \d+\.)', r'\n\1', result, flags=re.MULTILINE)
    
    return result.strip()
