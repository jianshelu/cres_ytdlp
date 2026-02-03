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
        if (activeRef.current && containerRef.current) {
            // Calculate position to center the active element
            const container = containerRef.current;
            const active = activeRef.current;

            const containerHeight = container.clientHeight;
            const activeTop = active.offsetTop;
            const activeHeight = active.clientHeight;

            // Scroll so the active element is in the middle
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
            className="h-full overflow-y-auto px-8 py-12 text-center scroll-smooth no-scrollbar"
            style={{
                maskImage: 'linear-gradient(to bottom, transparent, black 10%, black 90%, transparent)',
                WebkitMaskImage: 'linear-gradient(to bottom, transparent, black 10%, black 90%, transparent)'
            }}
        >
            <div className="space-y-6">
                {segments.map((segment) => {
                    const isActive = currentTime >= segment.start && currentTime < segment.end;
                    const isPast = currentTime > segment.end;

                    return (
                        <div
                            key={segment.id}
                            ref={isActive ? activeRef : null}
                            className={`transition-all duration-300 transform cursor-pointer ${isActive
                                    ? 'scale-110 opacity-100'
                                    : isPast
                                        ? 'scale-100 opacity-40 blur-[1px]'
                                        : 'scale-95 opacity-30 blur-[1px]'
                                }`}
                            onClick={() => {
                                const video = document.getElementById('main-video') as HTMLVideoElement;
                                if (video) {
                                    video.currentTime = segment.start;
                                    video.play();
                                }
                            }}
                        >
                            <p className={`text-2xl md:text-3xl font-bold leading-relaxed ${isActive ? 'text-indigo-400' : 'text-white'
                                }`}>
                                {segment.text}
                            </p>
                        </div>
                    );
                })}
            </div>
            {/* Spacer for bottom scrolling */}
            <div className="h-[50vh]"></div>
        </div>
    );
}
