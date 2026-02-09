'use client';

import { useMemo, useState } from 'react';

interface Keyword {
  term: string;
  score: number;
  count: number;
}

interface VideoTranscription {
  videoId: string;
  title: string;
  transcription: string;
}

interface CombinedKeySentence {
  id?: number;
  sentence: string;
  keyword?: string;
  source_index?: number;
  source_title?: string;
}

interface TranscriptionsResponse {
  query: string;
  videos: VideoTranscription[];
  combined: {
    keywords: Keyword[];
    sentence: string;
    key_sentences?: CombinedKeySentence[];
  };
}

interface Props {
  data: TranscriptionsResponse;
}

function splitCombinedSentences(text: string): string[] {
  return (text || '')
    .split(/(?<=[.!?\u3002\uff01\uff1f])\s+|[\u3002\uff01\uff1f]+/g)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

export default function SentenceClient({ data }: Props) {
  const [activeSource, setActiveSource] = useState<number>(0);

  const sentenceItems = useMemo(() => {
    const structured = (data.combined.key_sentences || [])
      .filter((x) => x && (x.sentence || '').trim())
      .slice(0, 5)
      .map((x, idx) => ({
        id: typeof x.id === 'number' ? x.id : idx,
        sentence: (x.sentence || '').trim(),
        keyword: (x.keyword || '').trim(),
        sourceIndex: typeof x.source_index === 'number' ? x.source_index : -1,
        sourceTitle: (x.source_title || '').trim(),
      }));

    if (structured.length > 0) return structured;

    return splitCombinedSentences(data.combined.sentence || '')
      .slice(0, 5)
      .map((sentence, idx) => ({
        id: idx,
        sentence,
        keyword: '',
        sourceIndex: -1,
        sourceTitle: '',
      }));
  }, [data.combined.key_sentences, data.combined.sentence]);

  const sourceTitle = data.videos[activeSource]?.title || '';
  const sourceText = data.videos[activeSource]?.transcription || '';

  return (
    <>
      <div className="transcription-page-header">
        <h1>Sentence View</h1>
        <p>
          Search Query: <span className="keyword-badge" style={{ fontSize: '1.2rem', padding: '0.5rem 1rem' }}>{data.query}</span>
        </p>
      </div>

      <section className="combined-section">
        <h2>Combined Keywords</h2>
        <div className="combined-keywords">
          {data.combined.keywords.map((kw, i) => (
            <span key={i} className={`combined-tag tag-${kw.score >= 0.8 ? '5' : kw.score >= 0.6 ? '4' : kw.score >= 0.4 ? '3' : kw.score >= 0.2 ? '2' : '1'}`}>
              {kw.term} <span className="tag-count">({kw.count})</span>
            </span>
          ))}
        </div>
      </section>

      <section className="combined-section">
        <h2>Key Sentences</h2>
        <div className="combined-sentences" style={{ marginTop: '1rem' }}>
          {sentenceItems.map((item) => {
            const canJump = item.sourceIndex >= 0 && item.sourceIndex < data.videos.length;
            return (
              <button
                key={item.id}
                type="button"
                className="sentence-line-btn"
                onClick={() => {
                  if (canJump) setActiveSource(item.sourceIndex);
                }}
                title={canJump ? `Show source transcription V${item.sourceIndex + 1}` : 'No source transcript mapping'}
              >
                <span className="sentence-line-title">
                  {canJump
                    ? `V${item.sourceIndex + 1}. ${item.sourceTitle || data.videos[item.sourceIndex].title}`
                    : item.sourceTitle || 'Unknown source'}
                </span>
                <span className="sentence-line-text">{item.sentence}</span>
              </button>
            );
          })}
        </div>
      </section>

      {sourceText && (
        <section className="combined-section">
          <h2>Source Transcription</h2>
          <div style={{ color: 'var(--foreground)', fontWeight: 700, marginBottom: '0.75rem' }}>
            V{activeSource + 1}. {sourceTitle}
          </div>
          <div className="carousel-transcript" style={{ maxHeight: '50vh' }}>
            {sourceText}
          </div>
        </section>
      )}
    </>
  );
}

