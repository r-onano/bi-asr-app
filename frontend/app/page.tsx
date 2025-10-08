import Recorder from './components/Recorder';

export default function Page() {
  return (
    <main>
      <Recorder />
      <p style={{ marginTop: 24, color: '#666' }}>
        Tip: speak, then click the language button when you switch languages. The app sends ~2s chunks to the
        backend, transcribes with a language hint, and stores audio + text for research.
      </p>
    </main>
  );
}