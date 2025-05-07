from pathlib import Path
from datetime import datetime, timezone
import uuid, logging, os

DATA_DIR = Path(os.getenv("OUTPUT_DIR", "/data")).resolve()

def new_session_dir() -> Path:
    """Tạo thư mục phiên định dạng: 20240505T135412Z_f452a3"""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dirname = f"{stamp}_{uuid.uuid4().hex[:6]}"
    path = DATA_DIR / dirname
    path.mkdir(parents=True, exist_ok=True)
    return path

def setup_logging() -> None:
    log_dir = DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "api.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler()
        ],
    )

setup_logging()
