import re

def correct(text: str) -> str:
    """
    Loại bỏ ký tự lạ, sửa lỗi typo đơn giản.
    """
    text = re.sub(r"ﬁ", "fi", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()
