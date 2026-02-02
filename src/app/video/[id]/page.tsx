import Link from 'next/link';
import fs from 'fs';
import path from 'path';
import data from '../../../data.json';
import KaraokeTranscript from './KaraokeTranscript';

interface Props {
    params: Promise<{ id: string }>;
}

export default async function VideoPage({ params }: Props) {
    const resolvedParams = await params;
    const index = parseInt(resolvedParams.id);
    const videoData = data[index];

    if (!videoData) {
        return <div className="container">Video not found.</div>;
    }

    let transcript = null;
    if (videoData.json_path) {
        try {
            const fullPath = path.join(process.cwd(), '..', videoData.json_path);
            const jsonContent = fs.readFileSync(fullPath, 'utf8');
            transcript = JSON.parse(jsonContent);
        } catch (e) {
            console.error("Failed to read transcript:", e);
        }
    }

    const videoSrc = `/${videoData.video_path.replace('test_downloads/', 'downloads/')}`;

    return (
        <main className="container">
            <div style={{ marginBottom: '2rem' }}>
                <Link href="/" style={{ color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M19 12H5M12 19l-7-7 7-7" />
                    </svg>
                    Back to list
                </Link>
            </div>

            <h1 style={{ marginBottom: '2rem' }}>{videoData.title}</h1>

            {transcript ? (
                <KaraokeTranscript videoSrc={videoSrc} transcript={transcript} />
            ) : (
                <div className="container">No transcription available.</div>
            )}
        </main>
    );
}
