from pydantic import BaseModel, Field
from typing import Optional

class StartSessionRequest(BaseModel):
    client_label: Optional[str] = None
    user_agent: Optional[str] = None
    note: Optional[str] = None

class StartSessionResponse(BaseModel):
    session_id: str

class ChunkMetadata(BaseModel):
    session_id: str
    language_code: str = Field(..., pattern=r"^[a-z]{2}(-[A-Za-z0-9]+)?$")  # e.g. 'en', 'zh', 'en-US'
    start_ms: int
    end_ms: int

class SegmentResponse(BaseModel):
    segment_id: str
    text: Optional[str] = None
    audio_path: str

class EndSessionRequest(BaseModel):
    session_id: str