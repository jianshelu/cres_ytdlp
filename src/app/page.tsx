import fs from 'fs';
import path from 'path';
import Link from 'next/link';
import SearchForm from './components/SearchForm';

export const dynamic = 'force-dynamic';

export default function Home() {
    const downloadsDir = path.join(process.cwd(), 'public/downloads');
    let videoFiles: { name: string; file: string; summary: string; keywords: { word: string; count: number }[] }[] = [];

    try {
        if (fs.existsSync(downloadsDir)) {
            const files = fs.readdirSync(downloadsDir);

            // Collect all video files
            const rawVideos = files.filter(f =>
                f.endsWith('.webm') || f.endsWith('.mp4') || f.endsWith('.mkv')
            );

            videoFiles = rawVideos.map(file => {
                const baseName = path.parse(file).name;
                const jsonFile = files.find(f => f === `${baseName}.json`);
                let summary = "Summary pending...";
                let keywords: string[] = [];

                if (jsonFile) {
                    try {
                        const content = fs.readFileSync(path.join(downloadsDir, jsonFile), 'utf-8');
                        const data = JSON.parse(content);
                        summary = data.summary || "No summary available.";
                        keywords = data.keywords || [];
                    } catch (e) {
                        console.error(`Error reading data for ${baseName}`, e);
                    }
                }

                return {
                    name: baseName,
                    file: file,
                    summary: summary,
                    keywords: keywords
                };
            });
        }
    } catch (error) {
        console.error("Error reading downloads directory:", error);
    }

    return (
        <div className="min-h-screen bg-black text-white font-[family-name:var(--font-geist-sans)]">
            <div className="max-w-7xl mx-auto px-6 py-12">
                <header className="mb-16 flex flex-col md:flex-row md:items-end justify-between gap-8">
                    <div>
                        <h1 className="text-5xl font-black tracking-tighter bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 bg-clip-text text-transparent mb-4">
                            ANTIGRAVITY
                        </h1>
                        <p className="text-gray-400 text-lg font-medium max-w-xl">
                            Next-gen video analysis engine. Instant transcription, AI summarization, and key insight extraction.
                        </p>
                    </div>
                    <div className="w-full md:w-96">
                        <SearchForm />
                    </div>
                </header>

                {videoFiles.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-20 bg-gray-900/30 rounded-3xl border border-gray-800 border-dashed">
                        <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mb-6">
                            <span className="text-2xl">🔍</span>
                        </div>
                        <h2 className="text-xl font-bold mb-2">No videos processed yet</h2>
                        <p className="text-gray-500">Submit a YouTube URL above to start the analysis pipeline.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        {videoFiles.map((video) => (
                            <Link
                                href={`/video/${encodeURIComponent(video.name)}`}
                                key={video.name}
                                className="group relative bg-[#111] border border-gray-800 rounded-3xl overflow-hidden hover:border-indigo-500/50 transition-all duration-500 hover:shadow-[0_0_40px_rgba(79,70,229,0.15)]"
                            >
                                <div className="aspect-video bg-gray-900 relative overflow-hidden">
                                    <div className="absolute inset-0 flex items-center justify-center group-hover:scale-110 transition-transform duration-700">
                                        <div className="w-16 h-16 bg-indigo-600 rounded-full flex items-center justify-center shadow-lg transform group-hover:rotate-12 transition-all">
                                            <span className="text-2xl ml-1">▶</span>
                                        </div>
                                    </div>
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-60"></div>
                                </div>

                                <div className="p-6">
                                    <div className="flex flex-wrap gap-2 mb-4">
                                        {(video.keywords || []).slice(0, 5).map((kw: any, i) => {
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
                                    <h2 className="text-xl font-bold mb-3 line-clamp-2 group-hover:text-indigo-400 transition-colors">
                                        {video.name}
                                    </h2>
                                    <p className="text-gray-500 text-sm line-clamp-3 leading-relaxed mb-6">
                                        {video.summary}
                                    </p>
                                    <div className="pt-4 border-t border-gray-800 flex items-center justify-between">
                                        <span className="text-xs font-bold text-gray-600 uppercase tracking-widest">Analysis Ready</span>
                                        <span className="text-indigo-500 font-bold text-sm flex items-center gap-2">
                                            View Report <span className="group-hover:translate-x-1 transition-transform">→</span>
                                        </span>
                                    </div>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
