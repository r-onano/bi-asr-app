-- Enable UUIDs
create extension if not exists "uuid-ossp";


-- Sessions table: one per recording session
create table if not exists sessions (
id uuid primary key default uuid_generate_v4(),
created_at timestamptz not null default now(),
client_label text, -- optional: user's label/name for session
user_agent text, -- optional: store UA for debugging
note text -- optional freeform notes
);


-- Segments table: one row per audio chunk
create table if not exists segments (
id uuid primary key default uuid_generate_v4(),
created_at timestamptz not null default now(),
session_id uuid not null references sessions(id) on delete cascade,
language_code text not null, -- e.g., 'en' or 'zh'
start_ms int not null, -- client-side elapsed ms when chunk started
end_ms int not null, -- client-side elapsed ms when chunk ended
asr_text text, -- transcription result
confidence numeric, -- optional if your ASR returns it
audio_path text not null -- Supabase storage path to raw chunk
);


-- Simple view to aggregate transcript per session by time
create or replace view session_transcripts as
select s.id as session_id,
string_agg(
'[' || seg.language_code || '] ' || coalesce(seg.asr_text, ''),
' ',
order by seg.start_ms
) as transcript
from sessions s
left join segments seg on seg.session_id = s.id
group by s.id;