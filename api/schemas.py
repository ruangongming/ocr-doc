from pydantic import BaseModel

class OCRResponse(BaseModel):
    session: str         # tên thư mục phiên
    preview: str         # 500 ký tự đầu để FE hiển thị
    paths: dict[str, str]  # {"txt": "...", "md": "...", "json": "..."}
