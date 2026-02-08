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
  search_query?: string;
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

  // Extract unique search queries with video counts
  const searchQueryMap = new Map<string, number>();
  data.forEach(video => {
    const query = video.search_query || 'Uncategorized';
    searchQueryMap.set(query, (searchQueryMap.get(query) || 0) + 1);
  });

  // Sort by count descending
  const searchQueries = Array.from(searchQueryMap.entries())
    .map(([query, count]) => ({ query, count }))
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
        {/* Video Grid - Left Side (3 columns) */}
        <div className="grid">
          {data.map((video: VideoData, index: number) => (
            <VideoCard key={index} video={video} index={index} />
          ))}
        </div>

        {/* Search Words Sidebar - Right Side */}
        <aside className="keyword-sidebar">
          <h3>🔍 Search Words</h3>
          <p className="sidebar-subtitle">Click to view transcriptions for this search</p>
          <div className="keyword-list">
            {searchQueries.map((sq, i) => {
              // Color based on count
              let colorClass = 'tag-1';
              if (sq.count >= 20) colorClass = 'tag-5';
              else if (sq.count >= 10) colorClass = 'tag-4';
              else if (sq.count >= 5) colorClass = 'tag-3';
              else if (sq.count >= 2) colorClass = 'tag-2';

              return (
                <Link
                  key={i}
                  href={`/transcriptions?query=${encodeURIComponent(sq.query)}`}
                  className={`sidebar-tag ${colorClass}`}
                >
                  {sq.query} <span className="tag-count">({sq.count})</span>
                </Link>
              );
            })}
            {searchQueries.length === 0 && (
              <p style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>No search queries yet. Start a batch process above.</p>
            )}
          </div>
        </aside>
      </div>
    </main>
  );
}
