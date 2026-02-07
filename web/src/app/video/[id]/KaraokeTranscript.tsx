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
    initialTime?: number;
}

export default function KaraokeTranscript({ videoSrc, poster, transcript, initialTime }: Props) {
    const [currentTime, setCurrentTime] = useState(0);
    const videoRef = useRef<HTMLVideoElement>(null);

    const handleTimeUpdate = () => {
        if (videoRef.current) {
            setCurrentTime(videoRef.current.currentTime);
        }
    };

    // Auto-scroll logic removed as it's less standard for paragraph views, 
    // but the user can scroll naturally since the video is sticky.

    // Initial Seek and Play
    useEffect(() => {
        if (videoRef.current) {
            if (initialTime && initialTime > 0) {
                videoRef.current.currentTime = initialTime;
            }
            videoRef.current.play().catch(e => {
                console.log("Autoplay prevented by browser, waiting for user interaction:", e);
            });
        }
    }, [videoSrc, initialTime]);

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
                <div className="transcript-list">
                    {transcript.segments.map((segment, idx) => {
                        const isActive = currentTime >= segment.start && currentTime <= segment.end;

                        return (
                            <div
                                key={idx}
                                className={`transcript-segment ${isActive ? 'active-segment' : ''}`}
                                onClick={() => {
                                    if (videoRef.current) {
                                        videoRef.current.currentTime = segment.start;
                                        videoRef.current.play();
                                    }
                                }}
                            >
                                {segment.text}
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
