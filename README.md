# User‑Assisted Bilingual ASR (Next.js + FastAPI + Supabase)

This app records microphone audio in short chunks, lets users **toggle language** live (e.g., English/Chinese), sends chunks
with the chosen language to a FastAPI backend that uses **OpenAI Whisper** for transcription, then stores **labeled audio + text**
in **Supabase** (Postgres + Storage). Perfect for collecting bilingual code‑switching datasets.

## Stack
- Frontend: Next.js 14 (App Router), MediaRecorder API
- Backend: FastAPI (Python), OpenAI Whisper API
- Database/Storage: Supabase (free tier)
- Hosting: Vercel (frontend), Render (backend)

## Quickstart
See the `sql/`, `backend/`, and `frontend/` folders for exact files and env vars.

### Local Dev
1. Create a Supabase project, run `sql/schema.sql`, create a private `segments` bucket.
2. Backend: set `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, then `uvicorn main:app --reload`.
3. Frontend: set `NEXT_PUBLIC_BACKEND_URL`, run `npm run dev`.

### Deploy
- Backend → Render. Frontend → Vercel. Configure CORS.

## Roadmap
- WebSocket live partials; VAD to skip silence; diarization; auto LID; per‑segment confidence.

## License
MIT