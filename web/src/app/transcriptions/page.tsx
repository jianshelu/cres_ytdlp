import Link from 'next/link';
import fs from 'fs';
import path from 'path';

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
    json_path: string | null;
    keywords: Keyword[];
    summary: string;
    search_query?: string;
}

interface TranscriptData {
    text: string;
    segments: { start: number; text: string }[];
    keywords?: Keyword[];
}

interface Props {
    searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function TranscriptionsPage({ searchParams }: Props) {
    const resolvedParams = await searchParams;
    const query = resolvedParams?.query as string || '';

    // Read data
    const dataPath = path.join(process.cwd(), 'src', 'data.json');
    let data: VideoData[] = [];
    try {
        const fileContent = fs.readFileSync(dataPath, 'utf8');
        data = JSON.parse(fileContent);
    } catch (e) {
        console.error("Failed to load video data:", e);
    }

    // Filter videos that match this search query
    const matchingVideos = query
        ? data.filter(video => video.search_query === query)
        : data;

    // Limit to 5 columns max
    const displayVideos = matchingVideos.slice(0, 5);

    // Fetch transcripts for matching videos
    const videosWithTranscripts: Array<{
        video: VideoData;
        transcript: TranscriptData | null;
        keywords: Keyword[];
    }> = [];

    for (const video of displayVideos) {
        let transcript: TranscriptData | null = null;
        let keywords: Keyword[] = video.keywords || [];

        if (video.json_path) {
            try {
                if (video.json_path.startsWith('http')) {
                    const res = await fetch(video.json_path, { cache: 'no-store' });
                    if (res.ok) {
                        transcript = await res.json();
                        if (transcript?.keywords) {
                            keywords = transcript.keywords;
                        }
                    }
                } else {
                    const relativePath = video.json_path.replace('test_downloads/', 'downloads/');
                    const fullPath = path.join(process.cwd(), 'public', relativePath);
                    const jsonContent = fs.readFileSync(fullPath, 'utf8');
                    transcript = JSON.parse(jsonContent);
                    if (transcript?.keywords) {
                        keywords = transcript.keywords;
                    }
                }
            } catch (e) {
                console.error(`Failed to load transcript for ${video.title}:`, e);
            }
        }

        videosWithTranscripts.push({ video, transcript, keywords });
    }

    // Calculate combined keywords (aggregate from all videos)
    const combinedKeywordMap = new Map<string, { count: number; score: number }>();
    videosWithTranscripts.forEach(item => {
        item.keywords.forEach(kw => {
            const existing = combinedKeywordMap.get(kw.word);
            if (existing) {
                existing.count += kw.count;
                existing.score = Math.max(existing.score, kw.score);
            } else {
                combinedKeywordMap.set(kw.word, { count: kw.count, score: kw.score });
            }
        });
    });

    const combinedKeywords = Array.from(combinedKeywordMap.entries())
        .map(([word, { count, score }]) => ({ word, count, score }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 20);

    // Calculate combined sentence (first sentence from each video that matches query)
    const combinedSentences: string[] = [];
    videosWithTranscripts.forEach(item => {
        if (item.transcript?.text) {
            const sentences = item.transcript.text.split(/[.!?。！？]+/).filter(s => s.trim());
            if (sentences.length > 0) {
                // Get first meaningful sentence (at least 20 chars)
                const meaningful = sentences.find(s => s.trim().length > 20);
                if (meaningful) {
                    combinedSentences.push(meaningful.trim());
                }
            }
        }
    });

    // Calculate column width based on number of videos
    const columnCount = Math.min(videosWithTranscripts.length, 5);

    return (
        <main className="container transcriptions-page">
            <div style={{ marginBottom: '2rem' }}>
                <Link href="/" style={{ color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M19 12H5M12 19l-7-7 7-7" />
                    </svg>
                    Back to Home
                </Link>
            </div>

            <div className="transcription-page-header">
                <h1>Transcriptions</h1>
                {query && (
                    <p>
                        Search Query: <span className="keyword-badge" style={{ fontSize: '1.2rem', padding: '0.5rem 1rem' }}>{query}</span>
                    </p>
                )}
                <p style={{ color: 'var(--muted)', marginTop: '0.5rem' }}>
                    Showing {videosWithTranscripts.length} video{videosWithTranscripts.length !== 1 ? 's' : ''} (max 5 columns)
                </p>
            </div>

            {/* Combined Keywords Section */}
            {combinedKeywords.length > 0 && (
                <section className="combined-section">
                    <h2>🏷️ Combined Keywords</h2>
                    <div className="combined-keywords">
                        {combinedKeywords.map((kw, i) => {
                            let colorClass = 'tag-1';
                            if (kw.score >= 5) colorClass = 'tag-5';
                            else if (kw.score === 4) colorClass = 'tag-4';
                            else if (kw.score === 3) colorClass = 'tag-3';
                            else if (kw.score === 2) colorClass = 'tag-2';

                            return (
                                <span key={i} className={`combined-tag ${colorClass}`}>
                                    {kw.word} <span className="tag-count">({kw.count})</span>
                                </span>
                            );
                        })}
                    </div>
                </section>
            )}

            {/* Combined Sentences Section */}
            {combinedSentences.length > 0 && (
                <section className="combined-section">
                    <h2>💬 Key Sentences</h2>
                    <div className="combined-sentences">
                        {combinedSentences.map((sentence, i) => (
                            <blockquote key={i} className="sentence-quote">
                                "{sentence}"
                            </blockquote>
                        ))}
                    </div>
                </section>
            )}

            {/* Transcription Columns */}
            {videosWithTranscripts.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--muted)' }}>
                    <p>No videos found for query "{query}"</p>
                    <Link href="/" style={{ color: 'var(--accent)', marginTop: '1rem', display: 'inline-block' }}>
                        ← Return to home
                    </Link>
                </div>
            ) : (
                <div
                    className="transcription-columns"
                    style={{
                        display: 'grid',
                        gridTemplateColumns: `repeat(${columnCount}, 1fr)`,
                        gap: '1rem',
                        marginTop: '2rem'
                    }}
                >
                    {videosWithTranscripts.map((item, index) => (
                        <div key={index} className="transcription-column">
                            {/* Video Title */}
                            <h3 className="column-title">{item.video.title}</h3>

                            {/* Keywords on top */}
                            <div className="column-keywords">
                                {item.keywords.slice(0, 8).map((kw, ki) => {
                                    let colorClass = 'tag-1';
                                    if (kw.score >= 5) colorClass = 'tag-5';
                                    else if (kw.score === 4) colorClass = 'tag-4';
                                    else if (kw.score === 3) colorClass = 'tag-3';
                                    else if (kw.score === 2) colorClass = 'tag-2';

                                    return (
                                        <span key={ki} className={`column-tag ${colorClass}`}>
                                            {kw.word}
                                        </span>
                                    );
                                })}
                                {item.keywords.length === 0 && (
                                    <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>No keywords</span>
                                )}
                            </div>

                            {/* Transcription Text */}
                            <div className="column-transcript">
                                {item.transcript?.text || 'Transcript not available'}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </main>
    );
}
