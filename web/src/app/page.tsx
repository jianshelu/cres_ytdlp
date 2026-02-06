import Link from 'next/link';
import fs from 'fs';
import path from 'path';
import VideoCard from './components/VideoCard';

export const dynamic = 'force-dynamic';

// Helper to encode parts of the URI while keeping the structure
function safelyEncodeURI(uri: string) {
  return uri.split('/').map(part => encodeURIComponent(part)).join('/');
}

export default async function Home() {
  // Read data at runtime
  const dataPath = path.join(process.cwd(), 'src', 'data.json');
  let data = [];
  try {
    const fileContent = fs.readFileSync(dataPath, 'utf8');
    data = JSON.parse(fileContent);
  } catch (e) {
    console.error("Failed to load video data:", e);
  }

  return (
    <main className="container">
      <header className="header">
        <h1>Video Review</h1>
        <p>Browse and review your downloaded "Antigravity" videos and transcriptions.</p>
        <p>Browse and review your downloaded "Antigravity" videos and transcriptions.</p>
      </header>

      <section className="search-section" style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #333', borderRadius: '8px' }}>
        <form action={async (formData) => {
          'use server';
          const { processVideos } = await import('./actions'); // Dynamic import to avoid cycles/issues if any
          await processVideos(formData);
          // In a real app we'd use useFormState or client components for feedback.
          // For now, this is a basic form submission that reloads.
        }} style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <input
            type="text"
            name="search"
            placeholder="Search keywords..."
            required
            style={{ flex: 1, padding: '8px', borderRadius: '4px', border: '1px solid #444', background: '#222', color: '#fff' }}
          />
          <input
            type="number"
            name="limit"
            placeholder="Limit"
            defaultValue="5"
            min="1"
            max="50"
            style={{ width: '80px', padding: '8px', borderRadius: '4px', border: '1px solid #444', background: '#222', color: '#fff' }}
          />
          <button
            type="submit"
            style={{ padding: '8px 16px', borderRadius: '4px', border: 'none', background: '#0070f3', color: '#fff', cursor: 'pointer' }}
          >
            Start Processing
          </button>
        </form>
      </section>

      <div className="grid">
        {data.map((video: any, index: number) => (
          <VideoCard key={index} video={video} index={index} />
        ))}
      </div>
    </main>
  );
}
