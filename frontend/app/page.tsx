import Recorder from './components/Recorder';

export default function Page() {
  return (
    <main>
      <Recorder />
      <p style={{ marginTop: 24, color: '#666' }}>
        Tip: start recording, then toggle the language button exactly when the language changes. Each toggle finalizes
        a segment and sends it to the backend with an explicit language label for transcription and dataset storage.
      </p>
    </main>
  );
}
