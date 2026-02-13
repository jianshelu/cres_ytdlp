'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';

export interface AudioRecord {
  id: number;
  title: string;
  videoPath: string;
  thumbPath: string;
  summary: string;
  query: string;
  updatedAt: string;
}

interface Props {
  records: AudioRecord[];
  requestMinioBase?: string;
}

interface AudioSourcePlayerProps {
  title: string;
  videoUrl: string;
  sources: string[];
}

function safelyEncodeURI(uri: string) {
  return uri.split('/').map((part) => encodeURIComponent(part)).join('/');
}

function parseUpdatedAt(input: string): number {
  const ts = Date.parse(input || '');
  return Number.isNaN(ts) ? 0 : ts;
}

function minioBaseUrl(requestMinioBase: string): string {
  const trimmed = (requestMinioBase || '').trim();
  if (trimmed) {
    return trimmed.replace(/\/+$/, '');
  }
  return 'http://127.0.0.1:9000';
}

function normalizeMediaUrl(rawUrl: string, requestMinioBase: string): string {
  let raw = (rawUrl || '').trim();
  if (!raw) return '';

  if (raw.startsWith('http:/') && !raw.startsWith('http://')) {
    raw = raw.replace('http:/', 'http://');
  } else if (raw.startsWith('https:/') && !raw.startsWith('https://')) {
    raw = raw.replace('https:/', 'https://');
  }

  if (!raw.startsWith('http://') && !raw.startsWith('https://')) {
    const normalizedPath = raw.replace('test_downloads/', 'downloads/');
    const prefixedPath = normalizedPath.startsWith('/') ? normalizedPath : `/${normalizedPath}`;
    return safelyEncodeURI(prefixedPath);
  }

  try {
    const url = new URL(raw);
    const host = (url.hostname || '').toLowerCase();
    if (host === 'cres' || host === 'minio' || host === 'minio-ci') {
      const base = minioBaseUrl(requestMinioBase);
      let mappedPath = url.pathname || '';
      if (host === 'cres' && !mappedPath.startsWith('/cres/')) {
        mappedPath = `/cres${mappedPath.startsWith('/') ? '' : '/'}${mappedPath}`;
      }
      raw = `${base}${mappedPath}`;
    }
  } catch {
    // Keep best-effort URL and continue.
  }

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

function buildAudioCandidates(videoPath: string, requestMinioBase: string): string[] {
  const normalizedVideo = normalizeMediaUrl(videoPath, requestMinioBase);
  if (!normalizedVideo) return [];

  const candidates: string[] = [];
  const audioRoute = normalizedVideo.replace('/videos/', '/audios/');
  const extensionPattern = /(\.(mp4|webm|mkv|mov|avi))([?#].*)?$/i;

  if (audioRoute !== normalizedVideo) {
    candidates.push(audioRoute);
    if (extensionPattern.test(audioRoute)) {
      candidates.push(audioRoute.replace(extensionPattern, '.m4a$3'));
      candidates.push(audioRoute.replace(extensionPattern, '.mp3$3'));
      candidates.push(audioRoute.replace(extensionPattern, '.wav$3'));
      candidates.push(audioRoute.replace(extensionPattern, '.ogg$3'));
      candidates.push(audioRoute.replace(extensionPattern, '.opus$3'));
    }
  }

  candidates.push(normalizedVideo);
  return Array.from(new Set(candidates.filter(Boolean)));
}

function AudioSourcePlayer({ title, videoUrl, sources }: AudioSourcePlayerProps) {
  const [sourceIndex, setSourceIndex] = useState(0);
  const [failed, setFailed] = useState(sources.length === 0);

  const source = sources[sourceIndex] || '';

  const handleMediaError = () => {
    if (sourceIndex + 1 < sources.length) {
      setSourceIndex((current) => current + 1);
      return;
    }
    setFailed(true);
  };

  if (!source || failed) {
    return (
      <div className="audio-fallback">
        <p>Audio preview is unavailable for this item.</p>
        {videoUrl && (
          <a href={videoUrl} target="_blank" rel="noreferrer">
            Open source media
          </a>
        )}
      </div>
    );
  }

  return (
    <div className="audio-player-wrap">
      <audio
        key={source}
        controls
        preload="none"
        src={source}
        aria-label={`Audio player for ${title}`}
        onError={handleMediaError}
        onCanPlay={() => setFailed(false)}
      />
      {sourceIndex > 0 && (
        <p className="audio-source-note">
          Using fallback source {sourceIndex + 1} of {sources.length}
        </p>
      )}
    </div>
  );
}

export default function AudioClient({ records, requestMinioBase = '' }: Props) {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeQuery, setActiveQuery] = useState('all');

  const queryStats = useMemo(() => {
    const counts = new Map<string, number>();
    for (const record of records) {
      const key = record.query || 'Uncategorized';
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    return Array.from(counts.entries())
      .map(([query, count]) => ({ query, count }))
      .sort((a, b) => b.count - a.count || a.query.localeCompare(b.query));
  }, [records]);

  const filteredRecords = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();

    return records
      .filter((record) => {
        if (activeQuery !== 'all' && record.query !== activeQuery) {
          return false;
        }
        if (!normalizedSearch) {
          return true;
        }
        const haystack = `${record.title} ${record.summary} ${record.query}`.toLowerCase();
        return haystack.includes(normalizedSearch);
      })
      .sort((a, b) => {
        const tsDiff = parseUpdatedAt(b.updatedAt) - parseUpdatedAt(a.updatedAt);
        if (tsDiff !== 0) return tsDiff;
        return a.title.localeCompare(b.title);
      });
  }, [records, searchTerm, activeQuery]);

  return (
    <section>
      <div className="audio-controls">
        <input
          type="text"
          className="audio-search-input"
          placeholder="Filter by title, summary, or query"
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
        />
        <select
          className="audio-query-select"
          value={activeQuery}
          onChange={(event) => setActiveQuery(event.target.value)}
        >
          <option value="all">All Queries ({records.length})</option>
          {queryStats.map((row) => (
            <option key={row.query} value={row.query}>
              {row.query} ({row.count})
            </option>
          ))}
        </select>
      </div>

      <div className="audio-query-chips">
        <button
          type="button"
          className={`audio-query-chip ${activeQuery === 'all' ? 'active' : ''}`}
          onClick={() => setActiveQuery('all')}
        >
          All
        </button>
        {queryStats.slice(0, 18).map((row) => (
          <button
            key={row.query}
            type="button"
            className={`audio-query-chip ${activeQuery === row.query ? 'active' : ''}`}
            onClick={() => setActiveQuery(row.query)}
          >
            {row.query} ({row.count})
          </button>
        ))}
      </div>

      {filteredRecords.length === 0 ? (
        <div className="audio-empty-state">
          <p>No matching items were found.</p>
        </div>
      ) : (
        <div className="audio-grid">
          {filteredRecords.map((record) => {
            const thumbSrc = record.thumbPath ? normalizeMediaUrl(record.thumbPath, requestMinioBase) : '';
            const videoUrl = normalizeMediaUrl(record.videoPath, requestMinioBase);
            const audioSources = buildAudioCandidates(record.videoPath, requestMinioBase);
            const shortSummary = record.summary || 'No summary available.';
            const updatedAtTs = parseUpdatedAt(record.updatedAt);

            return (
              <article key={`${record.id}-${record.title}`} className="audio-card">
                <div className="audio-thumb-wrap">
                  {thumbSrc ? <img src={thumbSrc} alt={record.title} className="audio-thumb" loading="lazy" /> : <div className="audio-thumb audio-thumb-fallback">No Thumbnail</div>}
                </div>

                <div className="audio-meta">
                  <h2>{record.title}</h2>
                  <p className="audio-meta-line">
                    <span className="audio-query-pill">{record.query || 'Uncategorized'}</span>
                    {updatedAtTs > 0 && <span>Updated {new Date(updatedAtTs).toLocaleString()}</span>}
                  </p>
                  <p className="audio-summary">{shortSummary}</p>
                  <AudioSourcePlayer title={record.title} videoUrl={videoUrl} sources={audioSources} />
                  <div className="audio-links">
                    <Link href={`/video/${record.id}`}>Open Video Detail</Link>
                    {videoUrl && (
                      <a href={videoUrl} target="_blank" rel="noreferrer">
                        Open Media URL
                      </a>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
