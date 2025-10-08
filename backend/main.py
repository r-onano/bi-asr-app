import io
import os
import tempfile
from datetime import datetime
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from openai import OpenAI

from models import (
    StartSessionRequest,
    StartSessionResponse,
    ChunkMetadata,
    SegmentResponse,
    EndSessionRequest,
)
from supabase_client import supabase

app = FastAPI(title="Bilingual ASR Backend")

# --- CORS ---
origins_env = os.getenv("CORS_ORIGINS", "*")
origins = [o.strip() for o in origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])  # Whisper API

# ---------- Session endpoints ----------
@app.post("/api/start-session", response_model=StartSessionResponse)
def start_session(payload: StartSessionRequest):
    data = {
        "client_label": payload.client_label,
        "user_agent": payload.user_agent,
        "note": payload.note,
    }
    res = supabase.table("sessions").insert(data).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to create session")
    return StartSessionResponse(session_id=res.data[0]["id"])

@app.post("/api/end-session")
def end_session(payload: EndSessionRequest):
    # No-op for now; hook for summaries or post-processing if needed
    # Could aggregate and return the full transcript
    view = supabase.table("segments").select("*").eq("session_id", payload.session_id).order("start_ms").execute()
    text = " ".join([f"[{row['language_code']}] {row.get('asr_text') or ''}" for row in view.data])
    return {"session_id": payload.session_id, "transcript": text}

# ---------- Chunk upload & ASR ----------
@app.post("/api/upload-chunk", response_model=SegmentResponse)
async def upload_chunk(
    metadata_json: str = Form(...),    # JSON string for metadata (safer with multipart)
    file: UploadFile = File(...),       # audio/webm or audio/ogg
):
    # Parse metadata
    try:
        meta = ChunkMetadata.model_validate_json(metadata_json)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Bad metadata: {e}")

    # Basic checks
    if not meta.session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")

    # Read file into memory
    blob = await file.read()
    if not blob:
        raise HTTPException(status_code=400, detail="Empty audio blob")

    # 1) Store raw audio chunk in Supabase Storage
    # path: sessions/<session_id>/<ts>-<start_ms>-<end_ms>.webm
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    ext = ".webm"
    if file.filename and "." in file.filename:
        ext = "." + file.filename.rsplit(".", 1)[-1]
    storage_path = f"sessions/{meta.session_id}/{ts}-{meta.start_ms}-{meta.end_ms}{ext}"

    upload_res = supabase.storage.from_("segments").upload(
        path=storage_path,
        file=blob,
        file_options={"content-type": file.content_type or "application/octet-stream"}
    )
    if hasattr(upload_res, "error") and upload_res.error:
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {upload_res.error}")

    # 2) Transcribe via OpenAI Whisper
    # Save to temp file because transcription API expects a file-like
    with tempfile.NamedTemporaryFile(suffix=ext) as tmp:
        tmp.write(blob)
        tmp.flush()
        tmp.seek(0)
        # Model options: 'whisper-1' (legacy) or modern 'gpt-4o-transcribe'/'whisper-1' depending on availability.
        # We'll call with language hint for better accuracy.
        try:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=tmp,
                language=meta.language_code,
                response_format="verbose_json"
            )
            text = transcription.text or None
        except Exception as e:
            text = None

    # 3) Insert DB row
    seg_row = {
        "session_id": meta.session_id,
        "language_code": meta.language_code,
        "start_ms": meta.start_ms,
        "end_ms": meta.end_ms,
        "asr_text": text,
        "audio_path": storage_path,
        "confidence": None,
    }
    ins = supabase.table("segments").insert(seg_row).execute()
    if not ins.data:
        raise HTTPException(status_code=500, detail="Failed to record segment")

    return SegmentResponse(segment_id=ins.data[0]["id"], text=text, audio_path=storage_path)

@app.get("/api/health")
def health():
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))