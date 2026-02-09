import Link from 'next/link';
import fs from 'fs';
import path from 'path';
import SearchForm from './components/SearchForm';

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
  query_updated_at?: string | null;
}

function safelyEncodeURI(uri: string) {
  return uri.split('/').map((part) => encodeURIComponent(part)).join('/');
}

export default async function Home() {
  const candidateDataPaths = [
    path.join(process.cwd(), 'src', 'data.json'),
    path.join(process.cwd(), 'web', 'src', 'data.json'),
  ];

  let data: VideoData[] = [];
  try {
    const dataPath = candidateDataPaths.find((p) => fs.existsSync(p));
    if (!dataPath) {
      throw new Error(`data.json not found in: ${candidateDataPaths.join(', ')}`);
    }
    const fileContent = fs.readFileSync(dataPath, 'utf8');
    data = JSON.parse(fileContent);
  } catch (e) {
    console.error('Failed to load video data:', e);
  }

  const grouped = new Map<string, VideoData[]>();
  data.forEach((video) => {
    const query = (video.search_query || 'Uncategorized').trim() || 'Uncategorized';
    if (!grouped.has(query)) grouped.set(query, []);
    grouped.get(query)!.push(video);
  });

  const queryRows = Array.from(grouped.entries())
    .map(([query, videos]) => {
      const latestTs = videos.reduce<number>((maxTs, v) => {
        const raw = v.query_updated_at || '';
        const ts = raw ? Date.parse(raw) : NaN;
        if (!Number.isNaN(ts)) return Math.max(maxTs, ts);
        return maxTs;
      }, 0);
      return { query, videos, count: videos.length, latestTs };
    })
    .sort((a, b) => b.latestTs - a.latestTs || b.count - a.count || a.query.localeCompare(b.query));

  return (
    <main className="container">
      <header className="header">
        <h1>Video Review</h1>
        <p>Browse and review your downloaded videos and transcriptions.</p>
      </header>

      <section
        className="search-section"
        style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #333', borderRadius: '8px' }}
      >
        <SearchForm />
      </section>

      <section className="waterfall-marquee">
        {queryRows.length === 0 && (
          <p style={{ color: 'var(--muted)', fontSize: '0.95rem' }}>
            No search queries yet. Start a batch process above.
          </p>
        )}

        {queryRows.map((row, rowIndex) => {
          const repeated = row.videos.length > 1 ? [...row.videos, ...row.videos] : row.videos;
          const visibleCards = repeated.slice(0, 24);
          const hiddenCount = Math.max(0, repeated.length - visibleCards.length);
          const directionClass = rowIndex % 2 === 0 ? 'left' : 'right';
          // Idle: much slower when not hovered.
          // 8s per result, minimum 120s per full loop.
          const idleDurationSeconds = Math.max(120, row.videos.length * 8);
          // Hover: unified quick speed for all rows.
          const hoverDurationSeconds = 14;

          return (
            <article key={row.query} className="waterfall-row">
              <div className="waterfall-row-header">
                <Link href={`/transcriptions?query=${encodeURIComponent(row.query)}`} className="waterfall-query-chip">
                  {row.query} ({row.count})
                </Link>
                {rowIndex === 0 && <span className="latest-chip">Latest</span>}
                <span className="speed-chip">Idle {idleDurationSeconds}s • Hover {hoverDurationSeconds}s</span>
                {hiddenCount > 0 && <span className="speed-chip">+{hiddenCount} more</span>}
              </div>

              <div className="marquee-shell">
                <div
                  className={`marquee-track ${directionClass}`}
                  style={{
                    ['--marquee-idle-duration' as string]: `${idleDurationSeconds}s`,
                    ['--marquee-hover-duration' as string]: `${hoverDurationSeconds}s`,
                  }}
                >
                  {visibleCards.map((video, idx) => {
                    const thumbSrc = video.thumb_path
                      ? video.thumb_path.startsWith('http')
                        ? video.thumb_path
                        : safelyEncodeURI(`/${video.thumb_path.replace('test_downloads/', 'downloads/')}`)
                      : null;
                    return (
                      <Link
                        key={`${row.query}-${idx}-${video.title}`}
                        href={`/transcriptions?query=${encodeURIComponent(row.query)}`}
                        className="marquee-card"
                        title={video.title}
                      >
                        <div className="marquee-thumb">
                          {thumbSrc ? (
                            <img src={thumbSrc} alt={video.title} loading="lazy" />
                          ) : (
                            <div className="marquee-thumb-fallback">No Thumbnail</div>
                          )}
                        </div>
                        <div className="marquee-title">{video.title}</div>
                      </Link>
                    );
                  })}
                </div>
              </div>
            </article>
          );
        })}
      </section>
    </main>
  );
}
