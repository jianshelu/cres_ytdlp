'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';

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

interface Props {
    video: VideoData;
    index: number;
}

// Helper to encode parts of the URI while keeping the structure
function safelyEncodeURI(uri: string) {
    return uri.split('/').map(part => encodeURIComponent(part)).join('/');
}

export default function VideoCard({ video, index }: Props) {
    const router = useRouter();

    const handleCardClick = () => {
        router.push(`/video/${index}`);
    };

    const thumbSrc = video.thumb_path
        ? (video.thumb_path.startsWith('http')
            ? video.thumb_path
            : safelyEncodeURI(`/${video.thumb_path.replace('test_downloads/', 'downloads/')}`))
        : null;

    return (
        <div className="video-card" onClick={handleCardClick} style={{ cursor: 'pointer' }}>
            <div className="thumbnail-wrapper">
                {thumbSrc ? (
                    <img src={thumbSrc} alt={video.title} />
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
                    {(video.keywords || []).map((kw, i) => {
                        let colorClass = 'tag-1';
                        if (kw.score >= 5) colorClass = 'tag-5';
                        else if (kw.score === 4) colorClass = 'tag-4';
                        else if (kw.score === 3) colorClass = 'tag-3';
                        else if (kw.score === 2) colorClass = 'tag-2';

                        const startTime = kw.start_time || 0;
                        const seekTime = Math.max(0, Math.floor(startTime) - 1);

                        return (
                            <Link
                                key={i}
                                href={`/video/${index}?t=${seekTime}`}
                                className={`tag ${colorClass}`}
                                title={`Jump to ${seekTime}s`}
                                onClick={(e) => {
                                    e.stopPropagation();
                                }}
                            >
                                {kw.word} <span className="tag-count">({kw.count})</span>
                            </Link>
                        );
                    })}
                </div>

                <div className="video-card-footer">
                    Click to view transcript
                </div>
            </div>
        </div>
    );
}
