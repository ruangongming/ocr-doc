from pydantic import BaseModel
from typing import Optional, Dict, Any

class OCRResponse(BaseModel):
    text: str
    markdown: Optional[str]
    raw_json: Optional[Dict[str, Any]]
