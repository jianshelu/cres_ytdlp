import Link from 'next/link';
import fs from 'fs';
import path from 'path';
import VideoCard from './components/VideoCard';

export const dynamic = 'force-dynamic';

interface Keyword {
  word: string;
  count: number;
  score: number;
  start_time?: number;
}

interface VideoData {
  title: string;
  video_path: string;
  thumb_path: string | null;
  keywords: Keyword[];
  summary: string;
}

export default async function Home() {
  // Read data at runtime
  const dataPath = path.join(process.cwd(), 'src', 'data.json');
  let data: VideoData[] = [];
  try {
    const fileContent = fs.readFileSync(dataPath, 'utf8');
    data = JSON.parse(fileContent);
  } catch (e) {
    console.error("Failed to load video data:", e);
  }

  // Aggregate unique keywords with total counts
  const keywordMap = new Map<string, { count: number; score: number }>();
  data.forEach(video => {
    (video.keywords || []).forEach(kw => {
      const existing = keywordMap.get(kw.word);
      if (existing) {
        existing.count += kw.count;
        existing.score = Math.max(existing.score, kw.score);
      } else {
        keywordMap.set(kw.word, { count: kw.count, score: kw.score });
      }
    });
  });

  // Sort by total count descending
  const allKeywords = Array.from(keywordMap.entries())
    .map(([word, { count, score }]) => ({ word, count, score }))
    .sort((a, b) => b.count - a.count);

  return (
    <main className="container">
      <header className="header">
        <h1>Video Review</h1>
        <p>Browse and review your downloaded videos and transcriptions.</p>
      </header>

      <section className="search-section" style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #333', borderRadius: '8px' }}>
        <form action={async (formData) => {
          'use server';
          const { processVideos } = await import('./actions');
          await processVideos(formData);
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

      <div className="main-layout">
        {/* Video Grid - Left Side */}
        <div className="grid">
          {data.map((video: VideoData, index: number) => (
            <VideoCard key={index} video={video} index={index} />
          ))}
        </div>

        {/* Keyword Sidebar - Right Side */}
        <aside className="keyword-sidebar">
          <h3>🔍 Keywords</h3>
          <p className="sidebar-subtitle">Click to view all videos with this keyword</p>
          <div className="keyword-list">
            {allKeywords.map((kw, i) => {
              let colorClass = 'tag-1';
              if (kw.score >= 5) colorClass = 'tag-5';
              else if (kw.score === 4) colorClass = 'tag-4';
              else if (kw.score === 3) colorClass = 'tag-3';
              else if (kw.score === 2) colorClass = 'tag-2';

              return (
                <Link
                  key={i}
                  href={`/transcriptions?keyword=${encodeURIComponent(kw.word)}`}
                  className={`sidebar-tag ${colorClass}`}
                >
                  {kw.word} <span className="tag-count">({kw.count})</span>
                </Link>
              );
            })}
            {allKeywords.length === 0 && (
              <p style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>No keywords extracted yet.</p>
            )}
          </div>
        </aside>
      </div>
    </main>
  );
}
