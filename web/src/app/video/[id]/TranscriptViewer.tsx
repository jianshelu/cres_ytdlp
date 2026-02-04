'use client';

import { useEffect, useState, useRef } from 'react';

interface Segment {
    id: number;
    start: number;
    end: number;
    text: string;
}

export default function TranscriptViewer({ segments }: { segments: Segment[] }) {
    const [currentTime, setCurrentTime] = useState(0);
    const activeRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const video = document.getElementById('main-video') as HTMLVideoElement;
        if (!video) return;

        const handleTimeUpdate = () => {
            setCurrentTime(video.currentTime);
        };

        video.addEventListener('timeupdate', handleTimeUpdate);
        return () => video.removeEventListener('timeupdate', handleTimeUpdate);
    }, []);

    // Auto-scroll to active segment
    useEffect(() => {
        if (activeRef.current) {
            activeRef.current.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
            });
        }
    }, [currentTime]);

    return (
        <div className="flex flex-col">
            {segments.map((segment) => {
                const isActive = currentTime >= segment.start && currentTime < segment.end;
                return (
                    <div
                        key={segment.id}
                        ref={isActive ? activeRef : null}
                        className={`p-3 text-sm cursor-pointer transition-colors duration-200 border-b border-gray-700/50 ${isActive
                                ? 'bg-indigo-900/40 text-white border-indigo-500/30'
                                : 'text-gray-400 hover:bg-gray-700/50 hover:text-gray-200'
                            }`}
                        onClick={() => {
                            const video = document.getElementById('main-video') as HTMLVideoElement;
                            if (video) {
                                video.currentTime = segment.start;
                                video.play();
                            }
                        }}
                    >
                        <span className="text-xs font-mono text-gray-500 mr-2 opacity-50 block mb-1">
                            {new Date(segment.start * 1000).toISOString().substr(14, 5)}
                        </span>
                        <p>{segment.text}</p>
                    </div>
                );
            })}
        </div>
    );
}
