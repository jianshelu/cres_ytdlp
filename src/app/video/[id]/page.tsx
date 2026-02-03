import fs from 'fs';
import path from 'path';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import KaraokeTranscript from './KaraokeTranscript';

export const dynamic = 'force-dynamic';

interface PageProps {
    params: {
        id: string;
    };
}

export default async function VideoPage({ params }: PageProps) {
    const { id } = await Promise.resolve(params); // Nextjs 15+ await params
    const videoName = decodeURIComponent(id);
    const downloadsDir = path.join(process.cwd(), 'public/downloads');

    // Find files
    let videoFile: string | null = null;
    let jsonFile: string | null = null;

    try {
        const files = fs.readdirSync(downloadsDir);
        videoFile = files.find(f => f.startsWith(videoName) && (f.endsWith('.webm') || f.endsWith('.mp4') || f.endsWith('.mkv'))) || null;
        jsonFile = files.find(f => f === `${videoName}.json`) || null;
    } catch (e) {
        console.error("Error reading directory", e);
        notFound();
    }

    if (!videoFile) {
        return notFound();
    }

    let transcriptData = null;
    if (jsonFile) {
        try {
            const content = fs.readFileSync(path.join(downloadsDir, jsonFile), 'utf-8');
            transcriptData = JSON.parse(content);
        } catch (e) {
            console.error("Error parsing transcript", e);
        }
    }

    return (
        <div className="min-h-screen bg-black text-white font-[family-name:var(--font-geist-sans)] flex flex-col">
            <header className="p-4 border-b border-gray-800 flex items-center bg-gray-900/50 backdrop-blur z-10">
                <Link href="/" className="text-gray-400 hover:text-white mr-4 transition-colors">
                    ← Back
                </Link>
                <h1 className="text-xl font-bold truncate text-gray-200">{videoName}</h1>
            </header>

            <main className="flex-1 flex flex-col lg:flex-row overflow-hidden">
                {/* Video Column */}
                <div className="lg:w-1/2 flex flex-col p-6 items-center justify-center bg-gray-900">
                    <div className="w-full max-w-2xl bg-black rounded-xl overflow-hidden shadow-2xl ring-1 ring-gray-800">
                        <video
                            id="main-video"
                            className="w-full aspect-video object-contain"
                            controls
                            src={`/downloads/${videoFile}`}
                        >
                            Your browser does not support the video tag.
                        </video>
                    </div>

                    <div className="mt-8 max-w-2xl w-full">
                        <h2 className="text-sm font-bold uppercase tracking-wider text-indigo-500 mb-2">AI Summary</h2>
                        <p className="text-gray-400 whitespace-pre-line leading-relaxed text-sm">
                            {transcriptData?.summary || "No summary available."}
                        </p>
                    </div>
                </div>

                {/* Karaoke Transcript Column */}
                <div className="lg:w-1/2 bg-black relative">
                    <div className="absolute inset-0 bg-gradient-to-b from-black via-transparent to-black pointer-events-none z-10"></div>
                    {transcriptData?.segments ? (
                        <KaraokeTranscript segments={transcriptData.segments} />
                    ) : (
                        <div className="flex h-full items-center justify-center text-gray-500">No transcript available.</div>
                    )}
                </div>
            </main>
        </div>
    );
}
