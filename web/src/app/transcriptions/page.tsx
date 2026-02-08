import Link from 'next/link';
import fs from 'fs';
import path from 'path';
import TranscriptionCard from '../components/TranscriptionCard';

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
}

interface TranscriptData {
    text: string;
    segments: { start: number; text: string }[];
}

interface Props {
    searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function TranscriptionsPage({ searchParams }: Props) {
    const resolvedParams = await searchParams;
    const keyword = resolvedParams?.keyword as string || '';

    // Read data
    const dataPath = path.join(process.cwd(), 'src', 'data.json');
    let data: VideoData[] = [];
    try {
        const fileContent = fs.readFileSync(dataPath, 'utf8');
        data = JSON.parse(fileContent);
    } catch (e) {
        console.error("Failed to load video data:", e);
    }

    // Filter videos that contain this keyword
    const matchingVideos = data.filter(video =>
        (video.keywords || []).some(kw =>
            kw.word.toLowerCase() === keyword.toLowerCase()
        )
    );

    // Fetch transcripts for matching videos
    const videosWithTranscripts: Array<{
        video: VideoData;
        transcript: TranscriptData | null;
        keywordSentence: string;
    }> = [];

    for (const video of matchingVideos) {
        let transcript: TranscriptData | null = null;
        let keywordSentence = '';

        if (video.json_path) {
            try {
                if (video.json_path.startsWith('http')) {
                    const res = await fetch(video.json_path, { cache: 'no-store' });
                    if (res.ok) {
                        transcript = await res.json();
                    }
                } else {
                    const relativePath = video.json_path.replace('test_downloads/', 'downloads/');
                    const fullPath = path.join(process.cwd(), 'public', relativePath);
                    const jsonContent = fs.readFileSync(fullPath, 'utf8');
                    transcript = JSON.parse(jsonContent);
                }

                // Find sentence containing keyword
                if (transcript?.segments) {
                    for (const seg of transcript.segments) {
                        if (seg.text.toLowerCase().includes(keyword.toLowerCase())) {
                            keywordSentence = seg.text;
                            break;
                        }
                    }
                }
                // Fallback: search in full text
                if (!keywordSentence && transcript?.text) {
                    const sentences = transcript.text.split(/[.!?。！？]+/);
                    for (const sentence of sentences) {
                        if (sentence.toLowerCase().includes(keyword.toLowerCase())) {
                            keywordSentence = sentence.trim();
                            break;
                        }
                    }
                }
            } catch (e) {
                console.error(`Failed to load transcript for ${video.title}:`, e);
            }
        }

        videosWithTranscripts.push({ video, transcript, keywordSentence });
    }

    return (
        <main className="container">
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
                {keyword && (
                    <p>
                        Videos containing: <span className="keyword-badge">{keyword}</span>
                    </p>
                )}
                <p style={{ color: 'var(--muted)', marginTop: '0.5rem' }}>
                    Found {videosWithTranscripts.length} video{videosWithTranscripts.length !== 1 ? 's' : ''}
                </p>
            </div>

            {videosWithTranscripts.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--muted)' }}>
                    <p>No videos found with keyword "{keyword}"</p>
                    <Link href="/" style={{ color: 'var(--accent)', marginTop: '1rem', display: 'inline-block' }}>
                        ← Return to home
                    </Link>
                </div>
            ) : (
                <div className="transcription-grid">
                    {videosWithTranscripts.map((item, index) => (
                        <TranscriptionCard
                            key={index}
                            title={item.video.title}
                            keyword={keyword}
                            keywordSentence={item.keywordSentence}
                            fullText={item.transcript?.text || 'Transcript not available'}
                            videoIndex={data.indexOf(item.video)}
                        />
                    ))}
                </div>
            )}
        </main>
    );
}
