'use client';

import { useEffect, useState, useRef } from 'react';

interface Segment {
    id: number;
    start: number;
    end: number;
    text: string;
}

export default function KaraokeTranscript({ segments }: { segments: Segment[] }) {
    const [currentTime, setCurrentTime] = useState(0);
    const activeRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Try to find the video element multiple times if needed
        let interval: NodeJS.Timeout;
        let attempts = 0;

        const findVideo = () => {
            const video = document.getElementById('main-video') as HTMLVideoElement;
            if (video) {
                console.log("KaraokeTranscript: Found video element.");
                clearInterval(interval);

                const handleTimeUpdate = () => {
                    setCurrentTime(video.currentTime);
                };

                video.addEventListener('timeupdate', handleTimeUpdate);
                // Trigger once to sync initial state
                setCurrentTime(video.currentTime);

                return () => {
                    video.removeEventListener('timeupdate', handleTimeUpdate);
                };
            }

            attempts++;
            if (attempts > 20) {
                console.error("KaraokeTranscript: Could not find video element after 20 attempts.");
                clearInterval(interval);
            }
        };

        interval = setInterval(findVideo, 500);
        findVideo(); // Try immediately

        return () => {
            clearInterval(interval);
        };
    }, []);

    // Auto-scroll to active segment
    useEffect(() => {
        if (activeRef.current && containerRef.current) {
            const container = containerRef.current;
            const active = activeRef.current;

            const containerHeight = container.clientHeight;
            const activeTop = active.offsetTop;
            const activeHeight = active.clientHeight;

            const scrollValues = activeTop - (containerHeight / 2) + (activeHeight / 2);

            container.scrollTo({
                top: scrollValues,
                behavior: 'smooth'
            });
        }
    }, [currentTime]);

    return (
        <div
            ref={containerRef}
            className="h-full overflow-y-auto px-10 py-20 text-center scroll-smooth scrollbar-hide"
            style={{
                maskImage: 'linear-gradient(to bottom, transparent, black 15%, black 85%, transparent)',
                WebkitMaskImage: 'linear-gradient(to bottom, transparent, black 15%, black 85%, transparent)'
            }}
        >
            <div className="space-y-10 pb-[40vh]">
                {segments.map((segment) => {
                    const isActive = currentTime >= segment.start && currentTime < segment.end;
                    const isPast = currentTime >= segment.end;

                    return (
                        <div
                            key={segment.id}
                            ref={isActive ? activeRef : null}
                            onClick={() => {
                                const video = document.getElementById('main-video') as HTMLVideoElement;
                                if (video) {
                                    video.currentTime = segment.start;
                                    video.play();
                                }
                            }}
                            className={`transition-all duration-500 cursor-pointer ${isActive
                                    ? 'scale-125 opacity-100'
                                    : 'scale-90 opacity-20 blur-[0.5px]'
                                }`}
                        >
                            <p
                                className={`text-3xl md:text-5xl font-black leading-tight tracking-tight transition-colors duration-500 ${isActive
                                        ? 'text-white drop-shadow-[0_0_15px_rgba(99,102,241,0.8)]'
                                        : 'text-gray-500'
                                    }`}
                            >
                                {segment.text}
                            </p>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
