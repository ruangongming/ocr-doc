import os
import uuid
import logging

def new_session_dir(base: str = "/data"):
    """
    Tạo directory mới cho mỗi phiên xử lý, trả về đường dẫn.
    """
    session_id = uuid.uuid4().hex
    path = os.path.join(base, session_id)
    os.makedirs(path, exist_ok=True)
    return path

def setup_logging(level=logging.INFO):
    """
    Cấu hình logging đơn giản cho toàn ứng dụng.
    """
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
        level=level
    )
    return logging.getLogger()

def get_env(key: str, default=None):
    """
    Lấy biến môi trường với giá trị default nếu không tồn tại.
    """
    return os.getenv(key, default)
