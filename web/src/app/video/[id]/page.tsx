import Link from 'next/link';
import fs from 'fs';
import path from 'path';
import KaraokeTranscript from './KaraokeTranscript';

interface Props {
    params: Promise<{ id: string }>;
    searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

// Helper to encode parts of the URI while keeping the structure
function safelyEncodeURI(uri: string) {
    return uri.split('/').map(part => encodeURIComponent(part)).join('/');
}

function normalizeMediaUrl(rawUrl: string) {
    const raw = (rawUrl || '').trim();
    if (!raw) return '';
    if (!raw.startsWith('http://') && !raw.startsWith('https://')) {
        return safelyEncodeURI(raw);
    }

    try {
        const url = new URL(raw);
        const encodedPath = url.pathname
            .split('/')
            .map((part) => {
                if (!part) return part;
                try {
                    return encodeURIComponent(decodeURIComponent(part));
                } catch {
                    return encodeURIComponent(part);
                }
            })
            .join('/');
        url.pathname = encodedPath;
        return url.toString();
    } catch {
        return encodeURI(raw);
    }
}

export default async function VideoPage({ params, searchParams }: Props) {
    const resolvedParams = await params;
    const resolvedSearchParams = await searchParams;
    const index = parseInt(resolvedParams.id);

    const initialTime = resolvedSearchParams?.t ? parseInt(resolvedSearchParams.t as string) : 0;

    // Read data at runtime (support both legacy and current index paths).
    const candidateDataPaths = [
        path.join(process.cwd(), 'src', 'data.json'),
        path.join(process.cwd(), 'web', 'src', 'data.json'),
    ];
    let videoData = null;
    try {
        const dataPath = candidateDataPaths.find((p) => fs.existsSync(p));
        if (!dataPath) {
            throw new Error(`data.json not found in: ${candidateDataPaths.join(', ')}`);
        }
        const fileContent = fs.readFileSync(dataPath, 'utf8');
        const data = JSON.parse(fileContent);
        videoData = data[index];
    } catch (e) {
        console.error("Failed to load video data:", e);
    }

    if (!videoData) {
        return <div className="container">Video not found.</div>;
    }

    let transcript = null;
    if (videoData.json_path) {
        try {
            if (videoData.json_path.startsWith('http')) {
                // Fetch from MinIO (or remote URL)
                const res = await fetch(normalizeMediaUrl(videoData.json_path), { cache: 'no-store' });
                if (res.ok) {
                    transcript = await res.json();
                } else {
                    console.error(`Failed to fetch transcript: ${res.status}`);
                }
            } else {
                // Legacy Local File
                const relativePath = videoData.json_path.replace('test_downloads/', 'downloads/');
                const fullPath = path.join(process.cwd(), 'public', relativePath);
                const jsonContent = fs.readFileSync(fullPath, 'utf8');
                transcript = JSON.parse(jsonContent);
            }
        } catch (e) {
            console.error("Failed to read transcript:", e);
        }
    }

    let videoSrc = '';
    if (videoData.video_path.startsWith('http')) {
        videoSrc = normalizeMediaUrl(videoData.video_path);
    } else {
        const videoPath = videoData.video_path.replace('test_downloads/', 'downloads/');
        videoSrc = safelyEncodeURI(`/${videoPath}`);
    }

    let posterSrc = undefined;
    if (videoData.thumb_path) {
        if (videoData.thumb_path.startsWith('http')) {
            posterSrc = normalizeMediaUrl(videoData.thumb_path);
        } else {
            const thumbPath = videoData.thumb_path.replace('test_downloads/', 'downloads/');
            posterSrc = safelyEncodeURI(`/${thumbPath}`);
        }
    }

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
                <KaraokeTranscript
                    videoSrc={videoSrc}
                    poster={posterSrc}
                    transcript={transcript}
                    initialTime={initialTime}
                />
            ) : (
                <div className="container">No transcription available.</div>
            )}
        </main>
    );
}
