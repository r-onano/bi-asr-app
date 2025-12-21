# User-Assisted Bilingual ASR for English–Mandarin Code Switching

This repository contains the code for a user-assisted bilingual automatic speech recognition (ASR) web application designed to study English–Mandarin code switching in realistic conversational speech.

Instead of relying on automatic language detection, the system allows the user to explicitly indicate the active language during recording. Speech is captured as segments, each labeled with a single intended language, transcribed independently, and stored for later analysis. This design prioritizes transparency, controllability, and clean data collection over full automation.

The project was developed as part of a graduate-level deep learning course and focuses on system design, evaluation methodology, and understanding architectural tradeoffs in bilingual ASR.

---

## Motivation

Code switching between English and Mandarin is common in casual speech, especially in voice messages and informal coordination. However, most ASR systems assume a single dominant language per utterance or rely on automatic language identification, which can fail when switches are brief or occur mid-sentence.

This project explores a different approach: shifting part of the language identification problem to the user interface. By allowing the user to explicitly signal language changes, we aim to:
- Improve transcription stability in bilingual settings
- Produce clean, well-labeled bilingual speech data
- Expose the practical limits of manual segmentation as switching becomes more fine-grained

---

## System Overview

The system is a lightweight web application with a clear interaction model:

1. The user starts a recording session.
2. The user speaks naturally and presses a toggle button to switch between English and Mandarin.
3. Each continuous span of speech with a single intended language is treated as a segment.
4. Each segment is uploaded with:
   - Audio data
   - Session ID
   - Language label
   - Timing metadata
5. The backend transcribes each segment independently and stores the results.

This design makes the pipeline easy to reason about and makes failure modes (ASR errors vs. segmentation errors vs. labeling errors) easier to diagnose.

---

## Architecture

- **Frontend**
  - Built with Next.js and React
  - Uses `getUserMedia` and `MediaRecorder` for audio capture
  - Maintains explicit language state (`en` or `zh`)
  - Finalizes and uploads segments on toggle events

- **Backend**
  - Provides endpoints for session management and segment uploads
  - Transcribes each segment independently using OpenAI Whisper
  - Uses the user-provided language label to constrain decoding
  - Stores transcripts and metadata in Supabase

- **Storage**
  - Session-level and segment-level metadata stored in Supabase
  - Designed to support both real-time feedback and offline evaluation

---

## Evaluation Design

We evaluate the system across five trials grouped into three tiers:

- **Tier 1: Monolingual**
  - English-only speech
  - Mandarin-only speech (characters, not pinyin)

- **Tier 2: Sentence-Level Switching**
  - Alternating English and Mandarin sentences

- **Tier 3: Phrase- and Word-Level Switching**
  - Mandarin phrases embedded in English sentences
  - Mandarin word insertions inside English
  - Mandarin-dominant speech with English insertions

Evaluation combines:
- **BLEU** for overlap-based accuracy
- **WER** for speech recognition error patterns
- **chrF** for character-level Mandarin evaluation
- **Label purity**, measuring how well language tags align with actual content

Both numeric metrics and qualitative transcript inspection are used.

---

## Key Findings

- The system performs strongly in monolingual and sentence-level switching scenarios.
- Manual segmentation aligns well with sentence boundaries and produces clean labeled data.
- Performance degrades sharply for phrase- and word-level switching due to:
  - Toggle latency
  - Boundary clipping
  - Single-language labels per segment
- Failures at fine-grained switching are architectural, not just model limitations.

---

## Limitations

- Manual toggling introduces reaction time and segmentation gaps.
- Each segment can only have one language label.
- Browser audio recording requires finalizing containers, which introduces small gaps.
- Standard ASR metrics are imperfect for evaluating code-switched speech.

---

## Future Work

Potential extensions include:
- Continuous streaming transcription with chunk-level language identification
- Automatic language diarization within segments
- Voice activity detection for cleaner segmentation
- Hybrid user-assisted and automatic language detection modes

---

## Repository Structure

frontend/ # Next.js frontend for recording and language toggling
backend/ # API and transcription logic
scripts/ # Evaluation and scoring scripts
data/ # Trial scripts and evaluation outputs

---

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/r-onano/bi-asr-app.git
2. Install frontend dependencies and run the app.

3. Start the backend server.

4. Record sessions and analyze transcripts using the provided scripts.

(Setup details may vary depending on local configuration and API credentials.)


## Authors

Cepher Onano
Cathy Gao
Jake Kim
Paul Mitchell

William & Mary, Department of Computer Science
