'use client';

import { useState } from 'react';

interface Keyword {
    term: string;
    score: number;
    count: number;
}

interface VideoTranscription {
    videoId: string;
    title: string;
    transcription: string;
    keywords: Keyword[];
}

interface Props {
    videos: VideoTranscription[];
}

export default function TranscriptionCarousel({ videos }: Props) {
    const [currentIndex, setCurrentIndex] = useState(0);

    if (!videos || videos.length === 0) {
        return (
            <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--muted)' }}>
                No transcriptions available
            </div>
        );
    }

    const currentVideo = videos[currentIndex];

    const handlePrev = () => {
        setCurrentIndex((prev) => (prev > 0 ? prev - 1 : videos.length - 1));
    };

    const handleNext = () => {
        setCurrentIndex((prev) => (prev < videos.length - 1 ? prev + 1 : 0));
    };

    // Keyboard navigation
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'ArrowLeft') handlePrev();
        if (e.key === 'ArrowRight') handleNext();
    };

    // Helper to get color class based on keyword score
    const getScoreClass = (score: number) => {
        if (score >= 0.9) return 'tag-5';
        if (score >= 0.75) return 'tag-4';
        if (score >= 0.6) return 'tag-3';
        if (score >= 0.4) return 'tag-2';
        return 'tag-1';
    };

    return (
        <div
            className="carousel-container"
            tabIndex={0}
            onKeyDown={handleKeyDown}
            role="region"
            aria-label="Transcription carousel"
        >
            {/* Navigation controls */}
            <div className="carousel-controls">
                <button
                    onClick={handlePrev}
                    className="carousel-btn carousel-btn-prev"
                    aria-label="Previous transcription"
                >
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M15 18l-6-6 6-6" />
                    </svg>
                </button>

                <div className="carousel-indicator">
                    {currentIndex + 1} / {videos.length}
                </div>

                <button
                    onClick={handleNext}
                    className="carousel-btn carousel-btn-next"
                    aria-label="Next transcription"
                >
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M9 18l6-6-6-6" />
                    </svg>
                </button>
            </div>

            {/* Current slide */}
            <div className="carousel-slide">
                <div className="carousel-slide-header">
                    <h3 className="carousel-slide-title">{currentVideo.title}</h3>

                    {/* Per-video keywords */}
                    {currentVideo.keywords && currentVideo.keywords.length > 0 && (
                        <div className="carousel-slide-keywords">
                            {currentVideo.keywords.map((kw, i) => (
                                <span key={i} className={`tag ${getScoreClass(kw.score)}`}>
                                    {kw.term} <span className="tag-count">({kw.count})</span>
                                </span>
                            ))}
                        </div>
                    )}
                </div>

                {/* Transcript content */}
                <div className="carousel-slide-content">
                    {currentVideo.transcription || 'Transcript not available'}
                </div>
            </div>

            {/* Slide dots indicator */}
            <div className="carousel-dots">
                {videos.map((_, i) => (
                    <button
                        key={i}
                        onClick={() => setCurrentIndex(i)}
                        className={`carousel-dot ${i === currentIndex ? 'active' : ''}`}
                        aria-label={`Go to slide ${i + 1}`}
                    />
                ))}
            </div>
        </div>
    );
}
