import os
import tempfile
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

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
    view = (
        supabase.table("segments")
        .select("*")
        .eq("session_id", payload.session_id)
        .order("start_ms")
        .execute()
    )
    text = " ".join(
        [f"[{row['language_code']}] {row.get('asr_text') or ''}" for row in (view.data or [])]
    )
    return {"session_id": payload.session_id, "transcript": text}


# ---------- Chunk upload & ASR ----------
@app.post("/api/upload-chunk", response_model=SegmentResponse)
async def upload_chunk(
    metadata_json: str = Form(...),
    file: UploadFile = File(...),
):
    # Parse metadata
    try:
        meta = ChunkMetadata.model_validate_json(metadata_json)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Bad metadata: {e}")

    if not meta.session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")

    blob = await file.read()
    print("upload_chunk:", "bytes=", len(blob), "content_type=", file.content_type, "filename=", file.filename)
    if not blob:
        raise HTTPException(status_code=400, detail="Empty audio blob")

    # Choose extension
    ext = ".webm"
    if file.filename and "." in file.filename:
        ext = "." + file.filename.rsplit(".", 1)[-1].lower()

    # 1) Store raw chunk in Supabase Storage
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    storage_path = f"sessions/{meta.session_id}/{ts}-{meta.start_ms}-{meta.end_ms}{ext}"

    try:
        supabase.storage.from_("segments").upload(
            path=storage_path,
            file=blob,
            file_options={"content-type": file.content_type or "application/octet-stream"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {e}")

    # 2) Transcribe via OpenAI Whisper
    # On Windows, reopen the temp file to avoid file handle issues.
    tmp_path = None
    text = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(blob)
            tmp.flush()
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_f:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_f,
                language=meta.language_code,
            )
            text = getattr(transcription, "text", None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

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

    return SegmentResponse(
        segment_id=ins.data[0]["id"],
        text=text,
        audio_path=storage_path,
    )


@app.get("/api/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
