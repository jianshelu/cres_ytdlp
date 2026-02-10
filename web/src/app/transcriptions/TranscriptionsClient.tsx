'use client';

import { SyntheticEvent, useEffect, useMemo, useRef, useState } from 'react';

interface Keyword {
    term: string;
    score: number;
    count: number;
}

interface Segment {
    start: number;
    end: number;
    text: string;
}

interface VideoTranscription {
    videoId: string;
    title: string;
    transcription: string;
    keywords: Keyword[];
    videoPath?: string;
    segments?: Segment[];
}

interface CombinedData {
    keywords: Keyword[];
    sentence: string;
    key_sentences?: CombinedKeySentence[];
    combined_video_url?: string;
    recombined_sentence?: boolean;
    sentence_version?: string;
}

interface MetaData {
    llm: string;
    replaceCount: number;
    coverage: boolean[];
}

interface TranscriptionsResponse {
    query: string;
    videos: VideoTranscription[];
    combined: CombinedData;
    meta: MetaData;
}

interface Props {
    data: TranscriptionsResponse;
    query: string;
}

interface KeySentenceItem {
    id: number;
    sentence: string;
    sourceIndex: number;
    sourceTitle: string;
}

interface CombinedKeySentence {
    id?: number;
    sentence: string;
    keyword?: string;
    source_index?: number;
    source_title?: string;
}

interface CombinedClip {
    keySentenceId: number;
    sourceIndex: number;
    sentence: string;
    title: string;
    videoPath: string;
    start: number;
    end: number;
}

export default function TranscriptionsClient({ data, query }: Props) {
    const [activeIndex, setActiveIndex] = useState(0);
    const carouselVideos = useMemo(() => data.videos.slice(0, 5), [data.videos]);
    const transcriptRef = useRef<HTMLDivElement | null>(null);
    const combinedVideoRefA = useRef<HTMLVideoElement | null>(null);
    const combinedVideoRefB = useRef<HTMLVideoElement | null>(null);

    const [pendingJumpTerm, setPendingJumpTerm] = useState<string | null>(null);
    const [pendingJumpSentence, setPendingJumpSentence] = useState<string | null>(null);
    const [activeSentenceIdx, setActiveSentenceIdx] = useState<number>(-1);
    const [combinedClipIndex, setCombinedClipIndex] = useState(0);
    const [activePlayer, setActivePlayer] = useState<0 | 1>(0);
    const [stickyVideo, setStickyVideo] = useState(true);
    const didMountRef = useRef(false);
    const userJumpEnabledRef = useRef(false);
    const playbackCacheRef = useRef<{ time: number; src: string; paused: boolean }>({
        time: 0,
        src: '',
        paused: false,
    });

    const normalizeForMatch = (value: string) => value.toLowerCase().trim();
    const normalizeCompact = (value: string) => normalizeForMatch(value).replace(/[^\u4e00-\u9fff\w]/g, '');
    const scrollWithinContainer = (container: HTMLElement, target: HTMLElement) => {
        const containerRect = container.getBoundingClientRect();
        const targetRect = target.getBoundingClientRect();
        const top = container.scrollTop + (targetRect.top - containerRect.top) - (container.clientHeight / 2) + (target.clientHeight / 2);
        container.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    };

    const resolveVideoSrc = (videoPath: string) => {
        const raw = (videoPath || '').trim();
        if (!raw) return '';
        if (raw.startsWith('http://') || raw.startsWith('https://')) {
            try {
                const url = new URL(raw);
                const encodedPath = url.pathname
                    .split('/')
                    .map((part) => {
                        if (!part) return part;
                        try {
                            return encodeURIComponent(decodeURIComponent(part));
                        } catch {
                            return encodeURIComponent(part);
                        }
                    })
                    .join('/');
                url.pathname = encodedPath;
                return url.toString();
            } catch {
                return encodeURI(raw);
            }
        }
        return `/${raw.replace(/^\/+/, '')}`;
    };

    const scoreToTagClass = (score: number) => {
        if (score >= 0.8) return 'tag-5';
        if (score >= 0.6) return 'tag-4';
        if (score >= 0.4) return 'tag-3';
        if (score >= 0.2) return 'tag-2';
        return 'tag-1';
    };

    const splitCombinedSentences = (text: string): string[] => {
        return (text || '')
            .split(/(?<=[.!?\u3002\uff01\uff1f])\s+|[\u3002\uff01\uff1f]+/g)
            .map((s) => s.trim())
            .filter((s) => s.length > 0);
    };

    const splitTranscriptSentences = (text: string): string[] => {
        const chunks = (text || '')
            .split(/(?<=[.!?\u3002\uff01\uff1f])\s+|\n+/g)
            .map((s) => s.trim())
            .filter((s) => s.length > 0);
        return chunks.length > 0 ? chunks : (text ? [text] : []);
    };

    const highlightKeywords = (text: string, keywords: string[]) => {
        if (!keywords.length) return text;
        const sortedKws = [...keywords]
            .filter((k) => k.length > 0)
            .sort((a, b) => b.length - a.length)
            .map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));

        if (!sortedKws.length) return text;
        const regex = new RegExp(`(${sortedKws.join('|')})`, 'gi');
        const exactRegex = new RegExp(`^(${sortedKws.join('|')})$`, 'i');
        const parts = text.split(regex);

        return parts.map((part, i) => {
            if (!part) return part;
            return exactRegex.test(part) ? <span key={i} className="highlight">{part}</span> : part;
        });
    };

    const deriveTranscriptKeywords = (text: string, combinedKeywords: string[], topN: number = 5) => {
        const stop = new Set([
            'the', 'and', 'for', 'that', 'this', 'with', 'you', 'your', 'are', 'was', 'have', 'has', 'had',
            'from', 'they', 'their', 'about', 'there', 'what', 'when', 'where', 'which', 'will', 'would',
            'could', 'should', 'into', 'just', 'like', 'more', 'than', 'then', 'over', 'very', 'some', 'such',
            'been', 'being', 'also', 'but', 'not', 'its', 'our', 'out', 'all', 'can', 'get', 'got', 'one',
            'two', 'three', 'how', 'why', 'who', 'whom', 'whose', 'video', 'today', 'people', 'thing', 'things',
            'make', 'made', 'using',
        ]);
        const combinedSet = new Set(combinedKeywords.map((k) => k.toLowerCase().trim()));
        const tokens = (text.match(/[A-Za-z][A-Za-z0-9'-]{2,}/g) || []).map((t) => t.toLowerCase());
        const counts: Record<string, number> = {};
        for (const t of tokens) {
            if (stop.has(t) || combinedSet.has(t)) continue;
            counts[t] = (counts[t] || 0) + 1;
        }
        return Object.entries(counts)
            .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
            .slice(0, topN)
            .map(([term]) => term);
    };

    const highlightTranscriptByKeywordType = (
        text: string,
        transcriptionKeywords: string[],
        combinedKeywords: Keyword[]
    ) => {
        const own = Array.from(new Set(transcriptionKeywords.map((k) => k.trim().toLowerCase()).filter((k) => k.length > 0)));
        const combinedMeta = new Map<string, string>();
        for (const kw of combinedKeywords) {
            const term = (kw.term || '').trim().toLowerCase();
            if (!term) continue;
            combinedMeta.set(term, scoreToTagClass(kw.score));
        }
        const combined = Array.from(new Set(combinedKeywords.map((k) => k.term).map((k) => k.trim().toLowerCase()).filter((k) => k.length > 0)));
        const merged = Array.from(new Set([...own, ...combined])).sort((a, b) => b.length - a.length);
        if (!merged.length) return text;

        const escaped = merged.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
        const regex = new RegExp(`(${escaped.join('|')})`, 'gi');
        const parts = text.split(regex);

        return parts.map((part, i) => {
            const normalized = part.trim().toLowerCase();
            if (!normalized) return part;
            const inOwn = own.includes(normalized);
            const inCombined = combined.includes(normalized);
            const combinedTagClass = combinedMeta.get(normalized) || 'tag-2';

            if (inOwn && inCombined) return <span key={i} data-term={normalized} className={`hl-both ${combinedTagClass}`}>{part}</span>;
            if (inOwn) return <span key={i} data-term={normalized} className="hl-transcript">{part}</span>;
            if (inCombined) return <span key={i} data-term={normalized} className={`hl-combined ${combinedTagClass}`}>{part}</span>;
            return part;
        });
    };

    const keywordSourceMap = useMemo(() => {
        const map = new Map<string, number>();
        for (const kw of data.combined.keywords) {
            const norm = normalizeForMatch(kw.term || '');
            if (!norm || map.has(norm)) continue;
            const idx = carouselVideos.findIndex((v) => normalizeForMatch(v.transcription || '').includes(norm));
            if (idx >= 0) map.set(norm, idx);
        }
        return map;
    }, [data.combined.keywords, carouselVideos]);

    const findSentenceSourceIndex = (sentence: string): number => {
        const normalizedSentence = normalizeForMatch(sentence);
        if (!normalizedSentence) return -1;

        const directIndex = carouselVideos.findIndex((v) => normalizeForMatch(v.transcription || '').includes(normalizedSentence));
        if (directIndex >= 0) return directIndex;

        const compactSentence = normalizeCompact(normalizedSentence);
        const probe = compactSentence.slice(0, 22);
        if (probe.length >= 6) {
            const probeIndex = carouselVideos.findIndex((v) => normalizeCompact(v.transcription || '').includes(probe));
            if (probeIndex >= 0) return probeIndex;
        }

        return -1;
    };

    const keySentenceItems = useMemo<KeySentenceItem[]>(() => {
        const structured = (data.combined.key_sentences || []).filter((item) => !!item?.sentence);
        if (structured.length > 0) {
            return structured.slice(0, 5).map((item, idx) => {
                const sentence = (item.sentence || '').trim();
                const sourceIndex = typeof item.source_index === 'number' ? item.source_index : findSentenceSourceIndex(sentence);
                const sourceTitle = (item.source_title || '').trim()
                    || (sourceIndex >= 0 ? carouselVideos[sourceIndex]?.title || `V${sourceIndex + 1}` : 'Unknown transcription');
                return {
                    id: typeof item.id === 'number' ? item.id : idx,
                    sentence,
                    sourceIndex,
                    sourceTitle,
                };
            });
        }

        const sentences = splitCombinedSentences(data.combined.sentence || '');
        return sentences.map((sentence, idx) => {
            const sourceIndex = findSentenceSourceIndex(sentence);
            return {
                id: idx,
                sentence,
                sourceIndex,
                sourceTitle: sourceIndex >= 0 ? carouselVideos[sourceIndex]?.title || `V${sourceIndex + 1}` : 'Unknown transcription',
            };
        });
    }, [carouselVideos, data.combined.key_sentences, data.combined.sentence]);

    const findBestSegmentForSentence = (sentence: string, segments: Segment[]): Segment | null => {
        if (!segments.length) return null;
        const target = normalizeCompact(sentence);
        if (!target) return null;

        let best: Segment | null = null;
        let bestScore = 0;

        for (const seg of segments) {
            const sText = normalizeCompact(seg.text || '');
            if (!sText) continue;
            if (sText.includes(target) || target.includes(sText)) {
                return seg;
            }
            const prefix = target.slice(0, Math.min(18, target.length));
            if (prefix && sText.includes(prefix)) {
                const score = prefix.length / Math.max(sText.length, 1);
                if (score > bestScore) {
                    bestScore = score;
                    best = seg;
                }
            }
        }

        return best;
    };

    const combinedClips = useMemo<CombinedClip[]>(() => {
        const clips: CombinedClip[] = [];
        for (const item of keySentenceItems) {
            if (item.sourceIndex < 0) continue;
            const sourceVideo = carouselVideos[item.sourceIndex];
            if (!sourceVideo) continue;
            const videoPath = sourceVideo.videoPath || '';
            if (!videoPath) continue;

            const segments = (sourceVideo.segments || []).filter((s) => Number.isFinite(s.start) && Number.isFinite(s.end));
            const matched = findBestSegmentForSentence(item.sentence, segments);

            let start = 0;
            let end = 12;
            if (matched) {
                const rawStart = Math.max(0, Number(matched.start) || 0);
                const rawEnd = Math.max(rawStart + 0.5, Number(matched.end) || rawStart + 0.5);
                // Keep clip long enough to feel like a sentence segment (not a flash cut).
                start = Math.max(0, rawStart - 1.5);
                end = Math.max(start + 8, rawEnd + 3.5);
                end = Math.min(end, start + 14);
            }

            clips.push({
                keySentenceId: item.id,
                sourceIndex: item.sourceIndex,
                sentence: item.sentence,
                title: sourceVideo.title,
                videoPath,
                start,
                end,
            });
        }
        return clips;
    }, [carouselVideos, keySentenceItems]);

    const clipIndexBySentenceId = useMemo(() => {
        const map = new Map<number, number>();
        combinedClips.forEach((clip, idx) => map.set(clip.keySentenceId, idx));
        return map;
    }, [combinedClips]);

    const activeClip = combinedClips[combinedClipIndex] || null;
    const activeKeySentenceId = activeClip?.keySentenceId ?? -1;
    const hasServerCombinedVideo = !!(data.combined.combined_video_url || '').trim();
    const getVideoRef = (slot: 0 | 1) => (slot === 0 ? combinedVideoRefA : combinedVideoRefB);
    const getActiveVideo = () => getVideoRef(activePlayer).current;
    const getStandbyVideo = () => getVideoRef(activePlayer === 0 ? 1 : 0).current;

    const activeTranscript = carouselVideos[activeIndex]?.transcription || '';
    const transcriptSentences = useMemo(() => splitTranscriptSentences(activeTranscript), [activeTranscript]);

    const highlightList = [
        ...data.combined.keywords.map((k) => k.term),
        query,
    ];

    const jumpToKeyword = (term: string) => {
        const normalizedTerm = normalizeForMatch(term);
        if (!normalizedTerm) return;
        const idx = keywordSourceMap.get(normalizedTerm);
        if (idx === undefined) return;
        setActiveIndex(idx);
        setPendingJumpTerm(normalizedTerm);
    };

    const jumpToSentenceSource = () => {
        if (!activeClip) return;
        setActiveIndex(activeClip.sourceIndex);
        setPendingJumpSentence(activeClip.sentence);
    };

    const findBestSentenceIndex = (targetSentence: string, sentences: string[]): number => {
        if (!targetSentence || !sentences.length) return -1;
        const normTarget = normalizeCompact(targetSentence);
        if (!normTarget) return -1;

        let bestIdx = -1;
        let bestScore = 0;
        for (let i = 0; i < sentences.length; i++) {
            const normSentence = normalizeCompact(sentences[i]);
            if (!normSentence) continue;
            if (normSentence.includes(normTarget) || normTarget.includes(normSentence)) return i;
            const prefix = normTarget.slice(0, Math.min(18, normTarget.length));
            if (prefix && normSentence.includes(prefix)) {
                const score = prefix.length / Math.max(normSentence.length, 1);
                if (score > bestScore) {
                    bestScore = score;
                    bestIdx = i;
                }
            }
        }
        return bestIdx;
    };

    useEffect(() => {
        if (!combinedClips.length) return;
        if (combinedClipIndex >= combinedClips.length) {
            setCombinedClipIndex(0);
        }
    }, [combinedClipIndex, combinedClips]);

    useEffect(() => {
        // Avoid browser scroll restoration jumping into lower sections on route changes.
        window.scrollTo(0, 0);
    }, [query]);

    useEffect(() => {
        if (!didMountRef.current) {
            didMountRef.current = true;
            return;
        }
        // New query should not auto-jump transcript sentence until user interacts.
        userJumpEnabledRef.current = false;
    }, [query]);

    useEffect(() => {
        const onScroll = () => {
            const nextSticky = window.scrollY < 260;
            setStickyVideo((prev) => (prev === nextSticky ? prev : nextSticky));
        };
        onScroll();
        window.addEventListener('scroll', onScroll, { passive: true });
        return () => window.removeEventListener('scroll', onScroll);
    }, []);

    useEffect(() => {
        const activeVideo = getActiveVideo();
        if (!activeVideo) return;
        if (!playbackCacheRef.current.src) return;
        // Preserve progress when sticky/non-sticky layout toggles on page scroll.
        if (activeVideo.src === playbackCacheRef.current.src) {
            const delta = Math.abs((activeVideo.currentTime || 0) - playbackCacheRef.current.time);
            if (delta > 0.5) {
                try {
                    activeVideo.currentTime = playbackCacheRef.current.time;
                } catch {
                    // noop
                }
            }
            if (!playbackCacheRef.current.paused) {
                activeVideo.play().catch(() => {
                    // autoplay may be blocked
                });
            }
        }
    }, [stickyVideo, activePlayer]);

    useEffect(() => {
        if (!activeClip) return;
        setActiveIndex(activeClip.sourceIndex);
        if (userJumpEnabledRef.current) {
            setPendingJumpSentence(activeClip.sentence);
        }
    }, [activeClip?.keySentenceId]);

    useEffect(() => {
        if (!pendingJumpTerm) return;
        const container = transcriptRef.current;
        if (!container) return;

        const safeTerm = pendingJumpTerm.replace(/(["\\])/g, '\\$1');
        const target = container.querySelector(`[data-term="${safeTerm}"]`) as HTMLElement | null;

        if (target) scrollWithinContainer(container, target);
        else container.scrollTo({ top: 0, behavior: 'smooth' });
        setPendingJumpTerm(null);
    }, [activeIndex, pendingJumpTerm]);

    useEffect(() => {
        if (!pendingJumpSentence) return;
        const container = transcriptRef.current;
        if (!container) return;

        const idx = findBestSentenceIndex(pendingJumpSentence, transcriptSentences);
        if (idx >= 0) {
            const target = container.querySelector(`[data-sentence-idx="${idx}"]`) as HTMLElement | null;
            if (target) {
                setActiveSentenceIdx(idx);
                scrollWithinContainer(container, target);
            }
        } else {
            setActiveSentenceIdx(-1);
        }
        setPendingJumpSentence(null);
    }, [activeIndex, pendingJumpSentence, transcriptSentences]);

    const loadClipToVideo = (video: HTMLVideoElement, clip: CombinedClip, autoplay: boolean, markIdx: number) => {
        const src = resolveVideoSrc(clip.videoPath);
        if (!src) return;

        const seekAndMaybePlay = () => {
            try {
                video.currentTime = Math.max(0, clip.start + 0.02);
            } catch {
                // noop
            }
            video.dataset.clipIdx = String(markIdx);
            video.muted = false;
            video.volume = 1;
            if (autoplay) {
                video.play().catch(() => {
                    // autoplay may be blocked by browser policy
                });
            } else {
                video.pause();
            }
        };

        if (!video.src || video.src !== src) {
            video.src = src;
            video.load();
            video.addEventListener('loadedmetadata', seekAndMaybePlay, { once: true });
            return;
        }

        if (video.readyState >= 1) {
            seekAndMaybePlay();
        } else {
            video.addEventListener('loadedmetadata', seekAndMaybePlay, { once: true });
        }
    };

    const lastLoadedClipKeyRef = useRef<string>('');

    useEffect(() => {
        if (!activeClip || !combinedClips.length) return;
        const clipKey = `${activePlayer}:${combinedClipIndex}:${activeClip.keySentenceId}:${activeClip.videoPath}:${activeClip.start}:${activeClip.end}`;
        if (lastLoadedClipKeyRef.current === clipKey) return;
        lastLoadedClipKeyRef.current = clipKey;

        const activeVideo = getActiveVideo();
        const standbyVideo = getStandbyVideo();
        if (!activeVideo) return;

        loadClipToVideo(activeVideo, activeClip, true, combinedClipIndex);

        if (standbyVideo) {
            const nextIdx = (combinedClipIndex + 1) % combinedClips.length;
            const nextClip = combinedClips[nextIdx];
            if (nextClip) loadClipToVideo(standbyVideo, nextClip, false, nextIdx);
        }
    }, [activeClip?.keySentenceId, activePlayer, combinedClipIndex, combinedClips.length]);

    const advanceClip = () => {
        if (!combinedClips.length) return;
        const currentIdx = combinedClipIndex;
        const nextIdx = (currentIdx + 1) % combinedClips.length;
        const currentClip = combinedClips[currentIdx];
        const nextClip = combinedClips[nextIdx];
        const activeVideo = getActiveVideo();
        const standbyVideo = getStandbyVideo();

        if (activeVideo && currentClip && nextClip) {
            const currentSrc = resolveVideoSrc(currentClip.videoPath);
            const nextSrc = resolveVideoSrc(nextClip.videoPath);
            if (currentSrc && currentSrc === nextSrc) {
                setCombinedClipIndex(nextIdx);
                try {
                    activeVideo.currentTime = Math.max(0, nextClip.start + 0.02);
                    activeVideo.play().catch(() => {
                        // ignore
                    });
                } catch {
                    // ignore
                }
                return;
            }

            if (standbyVideo && standbyVideo.dataset.clipIdx === String(nextIdx) && standbyVideo.readyState >= 2) {
                setCombinedClipIndex(nextIdx);
                setActivePlayer((p) => (p === 0 ? 1 : 0));
                standbyVideo.play().catch(() => {
                    // ignore
                });
                return;
            }
        }

        setCombinedClipIndex(nextIdx);
    };

    const handleCombinedTimeUpdate = (event: SyntheticEvent<HTMLVideoElement>) => {
        if (!activeClip) return;
        const activeVideo = getActiveVideo();
        if (!activeVideo) return;
        if (event.currentTarget !== activeVideo) return;
        playbackCacheRef.current = {
            time: activeVideo.currentTime || 0,
            src: activeVideo.src || '',
            paused: activeVideo.paused,
        };
        if (activeVideo.currentTime >= activeClip.end - 0.05) {
            advanceClip();
        }
    };

    const handleDownload = (content: string, filename: string) => {
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    const handleDownloadAll = () => {
        const allContent = data.videos
            .map((v) => `=== ${v.title} ===\n\n${v.transcription}`)
            .join('\n\n---\n\n');
        handleDownload(allContent, `transcriptions-${query}.txt`);
    };

    const goPrev = () => {
        setActiveIndex((prev) => (prev === 0 ? carouselVideos.length - 1 : prev - 1));
    };

    const goNext = () => {
        setActiveIndex((prev) => (prev === carouselVideos.length - 1 ? 0 : prev + 1));
    };

    return (
        <>
            <div className="transcription-page-header">
                <h1>Transcriptions</h1>
                <p>
                    Search Query: <span className="keyword-badge" style={{ fontSize: '1.2rem', padding: '0.5rem 1rem' }}>{query}</span>
                </p>
                <p style={{ color: 'var(--muted)', marginTop: '0.5rem' }}>
                    Showing {data.videos.length} video{data.videos.length !== 1 ? 's' : ''} (max 5)
                </p>
            </div>

            {(hasServerCombinedVideo || combinedClips.length > 0) && (
                <section className={`combined-section combined-video-section ${stickyVideo ? 'floating' : ''}`}>
                    <h2>Combined Video</h2>
                    {hasServerCombinedVideo ? (
                        <div className="combined-video-stack">
                            <video
                                className="combined-video-player is-active"
                                src={resolveVideoSrc(data.combined.combined_video_url || '')}
                                controls
                                autoPlay
                                loop
                                muted={false}
                                playsInline
                                preload="auto"
                            />
                        </div>
                    ) : (
                        <div className="combined-video-stack">
                            <video
                                ref={combinedVideoRefA}
                                className={`combined-video-player ${activePlayer === 0 ? 'is-active' : 'is-standby'}`}
                                controls={activePlayer === 0}
                                autoPlay
                                muted={false}
                                playsInline
                                preload="auto"
                                onTimeUpdate={handleCombinedTimeUpdate}
                                onEnded={advanceClip}
                            />
                            <video
                                ref={combinedVideoRefB}
                                className={`combined-video-player ${activePlayer === 1 ? 'is-active' : 'is-standby'}`}
                                controls={activePlayer === 1}
                                autoPlay
                                muted={false}
                                playsInline
                                preload="auto"
                                onTimeUpdate={handleCombinedTimeUpdate}
                                onEnded={advanceClip}
                            />
                        </div>
                    )}
                    <div className="combined-video-meta">
                        {hasServerCombinedVideo ? (
                            <>
                                <span>Prebuilt Combined Video</span>
                                {data.combined.recombined_sentence && <span>Recombined Sentence</span>}
                                {!!(data.combined.sentence_version || '').trim() && <span>{data.combined.sentence_version}</span>}
                            </>
                        ) : (
                            <>
                                <span>Clip {combinedClipIndex + 1}/{combinedClips.length}</span>
                                <span>Source: V{activeClip?.sourceIndex !== undefined ? activeClip.sourceIndex + 1 : '-'} - {activeClip?.title || '-'}</span>
                                <span>{activeClip ? `${activeClip.start.toFixed(1)}s - ${activeClip.end.toFixed(1)}s` : ''}</span>
                            </>
                        )}
                    </div>
                </section>
            )}

            {data.combined.keywords.length > 0 && (
                <section className="combined-section">
                    <h2>Combined Keywords</h2>
                    <div className="combined-keywords">
                        {data.combined.keywords.map((kw, i) => {
                            const sourceIdx = keywordSourceMap.get(normalizeForMatch(kw.term));
                            return (
                                <button
                                    key={i}
                                    type="button"
                                    className={`combined-tag jump-chip tag-${kw.score >= 0.8 ? '5' : kw.score >= 0.6 ? '4' : kw.score >= 0.4 ? '3' : kw.score >= 0.2 ? '2' : '1'}`}
                                    onClick={() => jumpToKeyword(kw.term)}
                                    title={sourceIdx !== undefined ? `Jump to transcription V${sourceIdx + 1}` : 'No source transcription in top 5'}
                                >
                                    {kw.term} <span className="tag-count">({kw.count})</span>
                                    {sourceIdx !== undefined && <span className="source-pill">V{sourceIdx + 1}</span>}
                                </button>
                            );
                        })}
                    </div>
                    <div style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                        <span>{data.meta.llm}</span>
                        <span>Replacements: {data.meta.replaceCount}/{data.meta.coverage.length}</span>
                        <span>Coverage: {data.meta.coverage.filter(Boolean).length}/{data.meta.coverage.length}</span>
                    </div>
                </section>
            )}

            {data.combined.sentence && (
                <section className="combined-section">
                    <h2 style={{ margin: 0 }}>Key Sentences</h2>
                    <div className="combined-sentences" style={{ marginTop: '1rem' }}>
                        {keySentenceItems.map((item) => {
                            const clipIdx = clipIndexBySentenceId.get(item.id);
                            const isActive = item.id === activeKeySentenceId;
                            return (
                                <button
                                    key={item.id}
                                    type="button"
                                    className={`sentence-line-btn ${isActive ? 'active' : ''}`}
                                    onClick={() => {
                                        userJumpEnabledRef.current = true;
                                        if (!hasServerCombinedVideo && clipIdx !== undefined) {
                                            setCombinedClipIndex(clipIdx);
                                            return;
                                        }
                                        if (item.sourceIndex >= 0) {
                                            setActiveIndex(item.sourceIndex);
                                            setPendingJumpSentence(item.sentence);
                                        } else {
                                            jumpToSentenceSource();
                                        }
                                    }}
                                    title={item.sourceIndex >= 0 ? `Jump to transcription V${item.sourceIndex + 1}` : 'Source not found'}
                                >
                                    <span className="sentence-line-title">
                                        {item.sourceIndex >= 0 ? `V${item.sourceIndex + 1}. ${item.sourceTitle}` : item.sourceTitle}
                                    </span>
                                    <span className="sentence-line-text">
                                        {highlightKeywords(item.sentence, [...data.combined.keywords.map((k) => k.term), query])}
                                    </span>
                                </button>
                            );
                        })}
                    </div>
                </section>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1rem' }}>
                <button
                    onClick={handleDownloadAll}
                    className="download-btn"
                    style={{
                        padding: '0.5rem 1rem',
                        borderRadius: '8px',
                        border: 'none',
                        background: 'var(--accent)',
                        color: '#fff',
                        cursor: 'pointer',
                        fontSize: '0.9rem',
                        fontWeight: 600,
                        transition: 'transform 0.2s, background 0.2s',
                    }}
                >
                    Download All Transcripts
                </button>
            </div>

            {carouselVideos.length > 0 && (
                <section className="combined-section">
                    <div className="carousel-header">
                        <h2 style={{ margin: 0 }}>Full Transcriptions</h2>
                        <div className="carousel-controls">
                            <button type="button" className="carousel-btn" onClick={goPrev} aria-label="Previous transcription">Previous</button>
                            <span className="carousel-index">{activeIndex + 1} / {carouselVideos.length}</span>
                            <button type="button" className="carousel-btn" onClick={goNext} aria-label="Next transcription">Next</button>
                        </div>
                    </div>

                    <div className="carousel-slide">
                        <h3 className="column-title">V{activeIndex + 1}. {carouselVideos[activeIndex].title}</h3>

                        <div className="column-keywords">
                            {(carouselVideos[activeIndex].keywords.length > 0
                                ? carouselVideos[activeIndex].keywords.slice(0, 5).map((kw) => kw.term)
                                : deriveTranscriptKeywords(
                                    carouselVideos[activeIndex].transcription || '',
                                    data.combined.keywords.map((k) => k.term),
                                    5
                                )
                            ).map((term, ki) => (
                                <span key={ki} className="column-tag tag-2">{term}</span>
                            ))}
                        </div>

                        <div ref={transcriptRef} className="carousel-transcript karaoke-transcript">
                            {carouselVideos[activeIndex].transcription
                                ? splitTranscriptSentences(carouselVideos[activeIndex].transcription).map((sentence, idx) => (
                                    <span
                                        key={`sentence-${idx}`}
                                        data-sentence-idx={idx}
                                        className={`karaoke-sentence ${idx === activeSentenceIdx ? 'active' : ''}`}
                                    >
                                        {highlightTranscriptByKeywordType(
                                            sentence,
                                            (carouselVideos[activeIndex].keywords.length > 0
                                                ? carouselVideos[activeIndex].keywords.map((k) => k.term)
                                                : deriveTranscriptKeywords(
                                                    carouselVideos[activeIndex].transcription || '',
                                                    data.combined.keywords.map((k) => k.term),
                                                    5
                                                )
                                            ),
                                            data.combined.keywords
                                        )}
                                    </span>
                                ))
                                : 'Transcript not available'}
                        </div>

                        <button
                            onClick={() => handleDownload(carouselVideos[activeIndex].transcription, `transcript-${carouselVideos[activeIndex].videoId}.txt`)}
                            className="download-btn-small"
                            style={{
                                marginTop: '0.75rem',
                                padding: '0.4rem 0.8rem',
                                borderRadius: '6px',
                                border: '1px solid var(--border)',
                                background: 'var(--card-bg)',
                                color: 'var(--foreground)',
                                cursor: 'pointer',
                                fontSize: '0.8rem',
                                fontWeight: 600,
                                width: 'fit-content',
                            }}
                        >
                            Download current transcript
                        </button>
                    </div>

                    <div className="carousel-dots">
                        {carouselVideos.map((_, i) => (
                            <button
                                key={i}
                                type="button"
                                className={`carousel-dot ${i === activeIndex ? 'active' : ''}`}
                                onClick={() => setActiveIndex(i)}
                                aria-label={`Go to transcription ${i + 1}`}
                            />
                        ))}
                    </div>
                </section>
            )}
        </>
    );
}
