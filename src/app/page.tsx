import fs from 'fs';
import path from 'path';
import SearchForm from './components/SearchForm';

export const dynamic = 'force-dynamic';

export default function Home() {
    const videosDir = path.join(process.cwd(), 'public/downloads');

    let videos: { name: string; url: string; summary: string }[] = [];

    try {
        const files = fs.readdirSync(videosDir);

        // Group by base name
        const videoFiles = files.filter(f => f.endsWith('.webm') || f.endsWith('.mp4') || f.endsWith('.mkv'));

        videos = videoFiles.map(file => {
            const baseName = path.parse(file).name;
            const jsonFile = files.find(f => f === `${baseName}.json`);
            let summary = "No summary available.";

            if (jsonFile) {
                try {
                    const content = fs.readFileSync(path.join(videosDir, jsonFile), 'utf-8');
                    const data = JSON.parse(content);
                    summary = data.summary || "Summary field missing.";
                } catch (e) {
                    summary = "Error reading summary.";
                }
            }

            return {
                name: baseName,
                url: `/downloads/${file}`,
                summary
            };
        });
    } catch (error) {
        console.error("Error reading video directory:", error);
    }

    return (
        <div className="min-h-screen p-8 bg-gray-50 font-[family-name:var(--font-geist-sans)]">
            <main className="max-w-4xl mx-auto">
                <h1 className="text-3xl font-bold mb-8 text-gray-900">Processed Videos</h1>

                <SearchForm />

                {videos.length === 0 ? (
                    <div className="text-center p-12 bg-white rounded-lg shadow">
                        <p className="text-gray-500">No videos found. Use the search to download videos.</p>
                    </div>
                ) : (
                    <div className="grid gap-8">
                        {videos.map((video) => (
                            <div key={video.name} className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-300">
                                <a href={`/video/${encodeURIComponent(video.name)}`} className="block hover:bg-gray-50 transition-colors">
                                    <div className="md:flex">
                                        <div className="md:shrink-0 bg-black flex items-center justify-center p-4">
                                            {/* Thumbnail placeholder or small video preview */}
                                            <div className="h-48 w-full md:w-64 bg-gray-800 flex items-center justify-center text-white">
                                                <span className="text-4xl">▶</span>
                                            </div>
                                        </div>
                                        <div className="p-8 w-full">
                                            <div className="uppercase tracking-wide text-sm text-indigo-500 font-semibold">Video Analysis</div>
                                            <h2 className="block mt-1 text-lg leading-tight font-medium text-black">{video.name}</h2>
                                            <div className="mt-4 prose prose-indigo text-gray-500 max-h-24 overflow-hidden text-ellipsis">
                                                <h3 className="text-xs font-bold text-gray-400 uppercase mb-1">Click to view details</h3>
                                            </div>
                                        </div>
                                    </div>
                                </a>
                            </div>
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
}
