import Link from 'next/link';
import TranscriptionsClient from './TranscriptionsClient';

export const dynamic = 'force-dynamic';

interface Props {
    searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function TranscriptionsPage({ searchParams }: Props) {
    const resolvedParams = await searchParams;
    const query = (resolvedParams?.query as string) || '';
    const parsedLimit = Number(resolvedParams?.limit || 50);
    const limit = Number.isFinite(parsedLimit) ? Math.max(1, Math.min(50, parsedLimit)) : 50;

    if (!query) {
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
                <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--muted)' }}>
                    <p>No search query provided.</p>
                    <Link href="/" style={{ color: 'var(--accent)', marginTop: '1rem', display: 'inline-block' }}>
                        ← Return to home
                    </Link>
                </div>
            </main>
        );
    }

    let data = null;
    let error = null;

    try {
        const signal = AbortSignal.timeout(25000);
        const response = await fetch(
            `http://127.0.0.1:3000/api/transcriptions?query=${encodeURIComponent(query)}&limit=${limit}`,
            { cache: 'no-store', signal }
        );

        if (!response.ok) {
            throw new Error(`API returned ${response.status}: ${response.statusText}`);
        }

        data = await response.json();
    } catch (e) {
        console.error('Failed to fetch transcriptions from API:', e);
        error = e instanceof Error ? e.message : String(e);
    }

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

            {error ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--muted)' }}>
                    <p style={{ color: '#ef4444', marginBottom: '1rem' }}>⚠️ API Error: {error}</p>
                    <p style={{ fontSize: '0.9rem' }}>Make sure the FastAPI backend is running on port 8000.</p>
                    <Link href="/" style={{ color: 'var(--accent)', marginTop: '1rem', display: 'inline-block' }}>
                        ← Return to home
                    </Link>
                </div>
            ) : !data || data.videos.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--muted)' }}>
                    <p>No videos found for query "{query}"</p>
                    <Link href="/" style={{ color: 'var(--accent)', marginTop: '1rem', display: 'inline-block' }}>
                        ← Return to home
                    </Link>
                </div>
            ) : (
                <TranscriptionsClient data={data} query={query} />
            )}
        </main>
    );
}
