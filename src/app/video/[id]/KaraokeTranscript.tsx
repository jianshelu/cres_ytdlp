'use client';

import { useState, useRef, useEffect } from 'react';

interface Segment {
    start: number;
    end: number;
    text: string;
}

interface Props {
    videoSrc: string;
    transcript: {
        segments: Segment[];
    };
}

export default function KaraokeTranscript({ videoSrc, transcript }: Props) {
    const [currentTime, setCurrentTime] = useState(0);
    const videoRef = useRef<HTMLVideoElement>(null);
    const activeRef = useRef<HTMLDivElement>(null);

    const handleTimeUpdate = () => {
        if (videoRef.current) {
            setCurrentTime(videoRef.current.currentTime);
        }
    };

    // Scroll active segment into view
    useEffect(() => {
        if (activeRef.current) {
            activeRef.current.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
            });
        }
    }, [currentTime]);

    const activeIndex = transcript.segments.findIndex(
        (s) => currentTime >= s.start && currentTime <= s.end
    );

    return (
        <div className="transcript-container">
            <div className="video-player-section">
                <video
                    ref={videoRef}
                    controls
                    src={videoSrc}
                    onTimeUpdate={handleTimeUpdate}
                >
                    Your browser does not support the video tag.
                </video>
            </div>

            <div className="transcript-section">
                <h3>Transcription</h3>
                <div className="transcript-list">
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
