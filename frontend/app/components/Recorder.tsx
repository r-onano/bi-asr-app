'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';

type Lang = 'en' | 'zh';

type Segment = {
  id?: string;
  language: Lang;
  start_ms: number;
  end_ms: number;
  text: string | null;
  audio_path?: string;
};

function pickMimeType() {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/ogg'];
  for (const t of candidates) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(t)) return t;
  }
  return '';
}

function extFromMime(mimeType: string) {
  if (mimeType.includes('ogg')) return 'ogg';
  return 'webm';
}

function createRecorder(stream: MediaStream) {
  const mimeType = pickMimeType();
  return mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
}

export default function Recorder() {
  const backendBase = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [language, setLanguage] = useState<Lang>('en');
  const [status, setStatus] = useState<string>('');
  const [segments, setSegments] = useState<Segment[]>([]);
  const [error, setError] = useState<string>('');

  const mediaStreamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);

  const sessionStartPerfRef = useRef<number>(0);
  const segmentStartMsRef = useRef<number>(0);

  const segmentChunksRef = useRef<BlobPart[]>([]);
  const hasAnyAudioRef = useRef<boolean>(false);

  const canToggle = isRecording && !!sessionId;

  useEffect(() => {
    return () => {
      tryStopRecorder();
      tryStopTracks();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function tryStopTracks() {
    const stream = mediaStreamRef.current;
    if (!stream) return;
    for (const track of stream.getTracks()) track.stop();
    mediaStreamRef.current = null;
  }

  function tryStopRecorder() {
    const rec = recorderRef.current;
    if (!rec) return;
    if (rec.state !== 'inactive') rec.stop();
    recorderRef.current = null;
  }

  function currentRelativeMs() {
    return Math.max(0, Math.floor(performance.now() - sessionStartPerfRef.current));
  }

  async function safeText(res: Response) {
    try {
      return await res.text();
    } catch {
      return '';
    }
  }

  async function startSession() {
    const res = await fetch(`${backendBase}/api/start-session`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        client_label: 'web',
        user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : null,
        note: 'user-assisted bilingual ASR session',
      }),
    });
    if (!res.ok) throw new Error(`start-session failed: ${res.status}`);
    const data = await res.json();
    if (!data?.session_id) throw new Error('start-session missing session_id');
    return data.session_id as string;
  }

  async function endSession(sid: string) {
    const res = await fetch(`${backendBase}/api/end-session`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ session_id: sid }),
    });
    if (!res.ok) throw new Error(`end-session failed: ${res.status}`);
    return await res.json();
  }

  async function stopRecorderAndWait(rec: MediaRecorder) {
    if (rec.state === 'inactive') return;

    await new Promise<void>((resolve) => {
      const onStop = () => {
        rec.removeEventListener('stop', onStop);
        resolve();
      };
      rec.addEventListener('stop', onStop);

      try {
        rec.requestData();
      } catch {
        // ignore
      }

      try {
        rec.stop();
      } catch {
        rec.removeEventListener('stop', onStop);
        resolve();
      }
    });
  }

  async function flushCurrentSegment(langForSegment: Lang, restartAfter: boolean) {
    const sid = sessionId;
    const rec = recorderRef.current;
    const stream = mediaStreamRef.current;

    if (!sid || !rec) return;

    const start_ms = segmentStartMsRef.current;
    const end_ms = currentRelativeMs();

    setStatus('uploading segment...');
    setError('');

    // Stop recorder to force a clean segment file boundary (fixes invalid/0s segments on toggles)
    await stopRecorderAndWait(rec);

    // Build blob AFTER stop so it includes the final chunk
    const parts = segmentChunksRef.current;
    segmentChunksRef.current = [];

    const hasAudio = hasAnyAudioRef.current;
    hasAnyAudioRef.current = false;

    const duration = end_ms - start_ms;

    if (!hasAudio || parts.length === 0 || duration < 200) {
      segmentStartMsRef.current = end_ms;

      if (restartAfter && stream) {
        const newRec = createRecorder(stream);
        recorderRef.current = newRec;

        newRec.ondataavailable = (evt) => {
          if (!evt.data || evt.data.size === 0) return;
          hasAnyAudioRef.current = true;
          segmentChunksRef.current.push(evt.data);
        };

        newRec.onerror = () => setError('recorder error');
        newRec.start(250);
      } else {
        recorderRef.current = null;
      }

      setStatus('');
      return;
    }

    const blobType = rec.mimeType || pickMimeType() || 'audio/webm';
    const blob = new Blob(parts, { type: blobType });

    const meta = {
      session_id: sid,
      language_code: langForSegment,
      start_ms,
      end_ms,
    };

    try {
      const form = new FormData();
      form.append('metadata_json', JSON.stringify(meta));

      const ext = extFromMime(blobType);
      form.append('file', blob, `segment-${start_ms}-${end_ms}.${ext}`);

      const res = await fetch(`${backendBase}/api/upload-chunk`, {
        method: 'POST',
        body: form,
      });

      if (!res.ok) {
        const msg = await safeText(res);
        throw new Error(`upload-chunk failed: ${res.status} ${msg}`);
      }

      const data = await res.json();

      setSegments((prev) => [
        ...prev,
        {
          id: data.segment_id,
          language: langForSegment,
          start_ms,
          end_ms,
          text: data.text ?? null,
          audio_path: data.audio_path,
        },
      ]);
    } catch (e: any) {
      setError(e?.message || 'segment upload failed');
      setSegments((prev) => [
        ...prev,
        {
          language: langForSegment,
          start_ms,
          end_ms,
          text: null,
        },
      ]);
    } finally {
      segmentStartMsRef.current = end_ms;
      setStatus('');
    }

    if (restartAfter && stream) {
      const newRec = createRecorder(stream);
      recorderRef.current = newRec;

      newRec.ondataavailable = (evt) => {
        if (!evt.data || evt.data.size === 0) return;
        hasAnyAudioRef.current = true;
        segmentChunksRef.current.push(evt.data);
      };

      newRec.onerror = () => setError('recorder error');
      newRec.start(250);
    } else {
      recorderRef.current = null;
    }
  }

  async function onStart() {
    setError('');
    setStatus('starting...');
    setSegments([]);
    setLanguage('en');

    try {
      const sid = await startSession();
      setSessionId(sid);

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const rec = createRecorder(stream);
      recorderRef.current = rec;

      segmentChunksRef.current = [];
      hasAnyAudioRef.current = false;

      sessionStartPerfRef.current = performance.now();
      segmentStartMsRef.current = 0;

      rec.ondataavailable = (evt) => {
        if (!evt.data || evt.data.size === 0) return;
        hasAnyAudioRef.current = true;
        segmentChunksRef.current.push(evt.data);
      };

      rec.onerror = () => {
        setError('recorder error');
      };

      rec.start(250);
      setIsRecording(true);
      setStatus('');
    } catch (e: any) {
      setStatus('');
      setError(e?.message || 'failed to start');
      setIsRecording(false);
      setSessionId(null);
      tryStopRecorder();
      tryStopTracks();
    }
  }

  async function onToggleLanguage() {
    if (!canToggle) return;

    const currentLang = language;
    const nextLang: Lang = currentLang === 'en' ? 'zh' : 'en';

    setStatus('finalizing segment...');
    await flushCurrentSegment(currentLang, true);

    setLanguage(nextLang);
    setStatus('');
  }

  async function onStop() {
    const sid = sessionId;
    if (!sid) {
      setIsRecording(false);
      tryStopRecorder();
      tryStopTracks();
      return;
    }

    setStatus('stopping...');
    setError('');

    try {
      await flushCurrentSegment(language, false);
    } finally {
      tryStopRecorder();
      tryStopTracks();
      setIsRecording(false);
    }

    try {
      setStatus('ending session...');
      await endSession(sid);
    } catch {
      // no-op
    } finally {
      setStatus('');
      setSessionId(null);
    }
  }

  const transcriptText = useMemo(() => {
    return segments
      .map((s) => {
        const tag = s.language === 'en' ? '[EN]' : '[ZH]';
        const t = s.text ?? '';
        return `${tag} ${t}`.trim();
      })
      .filter(Boolean)
      .join('\n');
  }, [segments]);

  const langLabel = language === 'en' ? 'English' : 'Mandarin';
  const toggleLabel = language === 'en' ? 'Switch to Mandarin' : 'Switch to English';

  return (
    <section style={{ padding: 16, border: '1px solid #ddd', borderRadius: 12 }}>
      <h2 style={{ marginTop: 0 }}>User-Assisted Bilingual ASR</h2>

      <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        {!isRecording ? (
          <button onClick={onStart} style={btn()}>
            Start
          </button>
        ) : (
          <button onClick={onStop} style={btn({ borderColor: '#c33' })}>
            Stop
          </button>
        )}

        <button onClick={onToggleLanguage} disabled={!canToggle} style={btn({ opacity: canToggle ? 1 : 0.5 })}>
          {toggleLabel}
        </button>

        <span style={{ color: '#444' }}>
          Current language: <b>{langLabel}</b>
        </span>

        {sessionId ? (
          <span style={{ color: '#666' }}>
            Session: <code>{sessionId}</code>
          </span>
        ) : null}
      </div>

      {status ? <p style={{ marginTop: 12, color: '#444' }}>{status}</p> : null}
      {error ? <p style={{ marginTop: 12, color: '#b00' }}>{error}</p> : null}

      <div style={{ marginTop: 16 }}>
        <h3 style={{ marginBottom: 8 }}>Transcript</h3>
        <textarea
          value={transcriptText}
          readOnly
          rows={10}
          style={{
            width: '100%',
            borderRadius: 10,
            border: '1px solid #ddd',
            padding: 12,
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
            fontSize: 13,
            lineHeight: 1.4,
          }}
        />
      </div>

      <div style={{ marginTop: 16 }}>
        <h3 style={{ marginBottom: 8 }}>Segments</h3>
        <div style={{ display: 'grid', gap: 8 }}>
          {segments.map((s, idx) => (
            <div
              key={`${idx}-${s.start_ms}-${s.end_ms}`}
              style={{
                border: '1px solid #eee',
                borderRadius: 10,
                padding: 10,
                background: '#fafafa',
              }}
            >
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                <b>{s.language === 'en' ? 'EN' : 'ZH'}</b>
                <span style={{ color: '#666' }}>
                  {s.start_ms}ms to {s.end_ms}ms
                </span>
                {s.audio_path ? <code style={{ color: '#666' }}>{s.audio_path}</code> : null}
              </div>
              <div style={{ marginTop: 6, whiteSpace: 'pre-wrap' }}>{s.text ?? '(no transcript returned)'}</div>
            </div>
          ))}
          {segments.length === 0 ? <div style={{ color: '#666' }}>No segments yet.</div> : null}
        </div>
      </div>

      <p style={{ marginTop: 16, color: '#666' }}>
        Recording is segmented only when I toggle languages or stop. Each segment is uploaded with an explicit language
        label and stored for future bilingual dataset growth.
      </p>
    </section>
  );
}

function btn(opts?: { borderColor?: string; opacity?: number }) {
  return {
    padding: '10px 14px',
    borderRadius: 10,
    border: `1px solid ${opts?.borderColor || '#333'}`,
    background: '#fff',
    cursor: 'pointer',
    opacity: opts?.opacity ?? 1,
  } as React.CSSProperties;
}
