import Link from 'next/link';
import data from '../data.json';

export default function Home() {
  return (
    <main className="container">
      <header className="header">
        <h1>Video Review</h1>
        <p>Browse and review your downloaded "Antigravity" videos and transcriptions.</p>
      </header>

      <div className="grid">
        {data.map((video, index) => (
          <Link key={index} href={`/video/${index}`} className="video-card">
            <div className="thumbnail-wrapper">
              {video.thumb_path ? (
                <img
                  src={`/${video.thumb_path.replace('test_downloads/', 'downloads/')}`}
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
              <div className="keyword-tags">
                {(video.keywords || []).map((kw, i) => {
                  let colorClass = 'tag-1';
                  if (kw.count === 2) colorClass = 'tag-2';
                  else if (kw.count === 3) colorClass = 'tag-3';
                  else if (kw.count === 4) colorClass = 'tag-4';
                  else if (kw.count >= 5) colorClass = 'tag-5plus';

                  return (
                    <span key={i} className={`tag ${colorClass}`}>
                      {kw.word} ({kw.count})
                    </span>
                  );
                })}
              </div>
              <div className="video-card-footer" style={{ marginTop: '1rem' }}>
                Click to view transcript
              </div>
            </div>
          </Link>
        ))}
      </div>
    </main>
  );
}
