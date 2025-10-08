'use client';

import React, { useEffect, useRef, useState } from 'react';

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL as string;

type Segment = {
  id: string;
  lang: string;
  startMs: number;
  endMs: number;
  text?: string;
};

export default function Recorder() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [language, setLanguage] = useState<'en' | 'zh'>('en');
  const [segments, setSegments] = useState<Segment[]>([]);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const startTimeRef = useRef<number>(0);
  const elapsedRef = useRef<number>(0);
  const chunkIntervalMs = 2000; // 2s chunks

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
    }
  }, []);

  async function ensureSession() {
    if (sessionId) return sessionId;
    const res = await fetch(`${BACKEND}/api/start-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_label: 'web-demo', user_agent: navigator.userAgent })
    });
    const data = await res.json();
    setSessionId(data.session_id);
    return data.session_id as string;
  }

  async function startRec() {
    const sid = await ensureSession();
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    mediaRecorderRef.current = mr;
    startTimeRef.current = performance.now();

    mr.ondataavailable = async (ev: BlobEvent) => {
      if (ev.data && ev.data.size > 0) {
        const now = performance.now();
        const startMs = Math.floor(elapsedRef.current);
        const endMs = Math.floor(startMs + chunkIntervalMs);
        elapsedRef.current = endMs;

        const metadata = {
          session_id: sid,
          language_code: language,
          start_ms: startMs,
          end_ms: endMs,
        };

        const fd = new FormData();
        fd.append('metadata_json', JSON.stringify(metadata));
        fd.append('file', ev.data, `chunk-${startMs}-${endMs}.webm`);

        try {
          const resp = await fetch(`${BACKEND}/api/upload-chunk`, { method: 'POST', body: fd });
          const json = await resp.json();
          setSegments(prev => [...prev, { id: json.segment_id, lang: language, startMs, endMs, text: json.text }]);
        } catch (e) {
          console.error('upload failed', e);
        }
      }
    };

    mr.start(chunkIntervalMs);
    setRecording(true);
  }

  function stopRec() {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
    setRecording(false);
  }

  async function endSession() {
    if (!sessionId) return;
    const res = await fetch(`${BACKEND}/api/end-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    });
    const data = await res.json();
    alert(`Final transcript for session\n\n${data.transcript || ''}`);
  }

  function toggleLanguage() {
    setLanguage(prev => (prev === 'en' ? 'zh' : 'en'));
  }

  const transcript = segments
    .sort((a, b) => a.startMs - b.startMs)
    .map(s => `[${s.lang}] ${s.text || ''}`)
    .join(' ');

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <h1>User‑Assisted Bilingual ASR</h1>
      <div style={{ display: 'flex', gap: 8 }}>
        {!recording ? (
          <button onClick={startRec} style={{ padding: '8px 12px' }}>Start Recording</button>
        ) : (
          <button onClick={stopRec} style={{ padding: '8px 12px' }}>Stop</button>
        )}
        <button onClick={toggleLanguage} disabled={!recording} style={{ padding: '8px 12px' }}>
          Language: {language.toUpperCase()} (click to switch)
        </button>
        <button onClick={endSession} disabled={!sessionId} style={{ padding: '8px 12px' }}>
          End Session & Aggregate
        </button>
      </div>

      <div>
        <h3>Live Transcript</h3>
        <div style={{ whiteSpace: 'pre-wrap', border: '1px solid #ddd', padding: 12, borderRadius: 8, minHeight: 120 }}>
          {transcript || '—'}
        </div>
      </div>

      <div>
        <h3>Segments</h3>
        <ol>
          {segments.map(s => (
            <li key={s.id}>
              <code>[{s.lang}] {s.startMs}–{s.endMs} ms</code> → {s.text || '…'}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}