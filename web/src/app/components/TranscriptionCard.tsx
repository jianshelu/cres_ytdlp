'use client';

import Link from 'next/link';

interface Props {
    title: string;
    keyword: string;
    keywordSentence: string;
    fullText: string;
    videoIndex: number;
}

export default function TranscriptionCard({
    title,
    keyword,
    keywordSentence,
    fullText,
    videoIndex
}: Props) {
    // Highlight keyword in sentence
    const highlightKeyword = (text: string, kw: string) => {
        if (!kw || !text) return text;

        const regex = new RegExp(`(${kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        const parts = text.split(regex);

        return parts.map((part, i) =>
            regex.test(part) ? (
                <span key={i} className="highlight">{part}</span>
            ) : (
                part
            )
        );
    };

    return (
        <div className="transcription-card">
            <Link href={`/video/${videoIndex}`}>
                <h3>{title}</h3>
            </Link>

            {keywordSentence ? (
                <div className="keyword-sentence">
                    {highlightKeyword(keywordSentence, keyword)}
                </div>
            ) : (
                <div className="keyword-sentence" style={{ opacity: 0.6 }}>
                    Keyword not found in transcript segments
                </div>
            )}

            <div className="full-transcript">
                {fullText}
            </div>
        </div>
    );
}
