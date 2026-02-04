'use client';

import { useState, useRef, useEffect } from 'react';

interface Segment {
    start: number;
    end: number;
    text: string;
}

interface Props {
    videoSrc: string;
    poster?: string;
    transcript: {
        segments: Segment[];
    };
}

export default function KaraokeTranscript({ videoSrc, poster, transcript }: Props) {
    const [currentTime, setCurrentTime] = useState(0);
    const videoRef = useRef<HTMLVideoElement>(null);
    const transcriptListRef = useRef<HTMLDivElement>(null);
    const activeRef = useRef<HTMLDivElement>(null);

    const handleTimeUpdate = () => {
        if (videoRef.current) {
            setCurrentTime(videoRef.current.currentTime);
        }
    };

    // Scroll active segment into view within the list
    useEffect(() => {
        if (activeRef.current && transcriptListRef.current) {
            const container = transcriptListRef.current;
            const element = activeRef.current;

            // Calculate relative offset
            const containerCenter = container.offsetHeight / 2;
            const elementOffset = element.offsetTop - container.offsetTop;

            container.scrollTo({
                top: elementOffset - containerCenter + (element.offsetHeight / 2),
                behavior: 'smooth'
            });
        }
    }, [currentTime]);

    const activeIndex = transcript.segments.findIndex(
        (s) => currentTime >= s.start && currentTime <= s.end
    );

    // Force play on mount/src change
    useEffect(() => {
        if (videoRef.current) {
            videoRef.current.play().catch(e => {
                console.log("Autoplay prevented by browser, waiting for user interaction:", e);
            });
        }
    }, [videoSrc]);

    return (
        <div className="transcript-container">
            <div className="video-player-section">
                <video
                    ref={videoRef}
                    controls
                    autoPlay
                    playsInline
                    src={videoSrc}
                    poster={poster}
                    onTimeUpdate={handleTimeUpdate}
                    onError={(e) => {
                        const target = e.target as HTMLVideoElement;
                        target.style.display = 'none';
                        if (target.parentElement) {
                            const errDiv = document.createElement('div');
                            errDiv.className = 'video-error';
                            errDiv.textContent = 'Video file not found or playback error.';
                            errDiv.style.padding = '2rem';
                            errDiv.style.textAlign = 'center';
                            errDiv.style.background = '#000';
                            errDiv.style.color = '#fff';
                            target.parentElement.appendChild(errDiv);
                        }
                    }}
                >
                    Your browser does not support the video tag.
                </video>
            </div>

            <div className="transcript-section">
                <h3>Transcription</h3>
                <div className="transcript-list" ref={transcriptListRef}>
                    {transcript.segments.map((segment, sIdx) => {
                        const isActive = sIdx === activeIndex;
                        return (
                            <div
                                key={sIdx}
                                ref={isActive ? activeRef : null}
                                className={`transcript-item ${isActive ? 'active' : ''}`}
                                onClick={() => {
                                    if (videoRef.current) {
                                        videoRef.current.currentTime = segment.start;
                                        videoRef.current.play();
                                    }
                                }}
                            >
                                <div className="transcript-text">{segment.text}</div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
