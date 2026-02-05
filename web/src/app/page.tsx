import Link from 'next/link';
import fs from 'fs';
import path from 'path';

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
          <Link key={index} href={`/video/${index}`} className="video-card">
            <div className="thumbnail-wrapper">
              {video.thumb_path ? (
                <img
                  src={safelyEncodeURI(`/${video.thumb_path.replace('test_downloads/', 'downloads/')}`)}
                  alt={video.title}
                />
              ) : (
                <div style={{ padding: '20px', textAlign: 'center' }}>No Thumbnail</div>
              )}
              <div className="play-overlay">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="white">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
            </div>
            <div className="video-card-content">
              <h2>{video.title}</h2>

              <div className="tags">
                {(video.keywords || []).map((kw: any, i: number) => {
                  let colorClass = 'tag-1';
                  // Use score directly (1-5)
                  if (kw.score >= 5) colorClass = 'tag-5';
                  else if (kw.score === 4) colorClass = 'tag-4';
                  else if (kw.score === 3) colorClass = 'tag-3';
                  else if (kw.score === 2) colorClass = 'tag-2';

                  return (
                    <span key={i} className={`tag ${colorClass}`}>
                      {kw.word} <span className="tag-count">({kw.count})</span>
                    </span>
                  );
                })}
              </div>

              <div className="video-card-footer">
                Click to view transcript
              </div>
            </div>
          </Link>
        ))}
      </div>
    </main>
  );
}
