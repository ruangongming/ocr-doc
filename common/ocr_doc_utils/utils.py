import os
import uuid
import logging
import datetime
import hashlib

def new_session_dir(base: str = "/data"):
    """
    Tạo thư mục phiên mới có UUID làm tên.
    """
    uid = str(uuid.uuid4())
    path = os.path.join(base, uid)
    os.makedirs(path, exist_ok=True)
    return path

def setup_logging(level=logging.INFO):
    """
    Cấu hình logging đơn giản.
    """
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
        level=level,
        datefmt="%Y-%m-%d %H:%M:%S,%03d",
    )
    return logging.getLogger()

def get_env(key: str, default=None):
    """
    Lấy biến môi trường với giá trị default nếu không tồn tại.
    """
    return os.getenv(key, default)

def get_timestamp():
    """
    Trả về timestamp hiện tại dạng ISO 8601 để dùng trong API responses.
    """
    return datetime.datetime.now().isoformat()

def compute_file_hash(file_bytes: bytes) -> str:
    """
    Tính hash MD5 cho nội dung file.
    """
    return hashlib.md5(file_bytes).hexdigest()

def extract_file_info(filename: str) -> dict:
    """
    Trích xuất thông tin từ tên file.
    """
    if not filename:
        return {"name": "unknown", "extension": "", "basename": "unknown"}
        
    basename = os.path.basename(filename)
    name, ext = os.path.splitext(basename)
    if ext.startswith('.'):
        ext = ext[1:]
    
    return {
        "name": name,
        "extension": ext.lower(),
        "basename": basename
    }
