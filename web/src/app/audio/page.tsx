import fs from 'fs';
import path from 'path';
import Link from 'next/link';
import { headers } from 'next/headers';
import AudioClient, { type AudioRecord } from './AudioClient';

export const dynamic = 'force-dynamic';

interface RawVideoData {
  title?: unknown;
  video_path?: unknown;
  thumb_path?: unknown;
  summary?: unknown;
  search_query?: unknown;
  query_updated_at?: unknown;
}

function normalizeString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function loadAudioRecords(): AudioRecord[] {
  const candidateDataPaths = [
    path.join(process.cwd(), 'src', 'data.json'),
    path.join(process.cwd(), 'web', 'src', 'data.json'),
  ];

  try {
    const dataPath = candidateDataPaths.find((candidate) => fs.existsSync(candidate));
    if (!dataPath) {
      throw new Error(`data.json not found in: ${candidateDataPaths.join(', ')}`);
    }

    const fileContent = fs.readFileSync(dataPath, 'utf8');
    const parsed = JSON.parse(fileContent);
    if (!Array.isArray(parsed)) {
      throw new Error('data.json root is not an array');
    }

    return parsed
      .map((entry, index) => {
        const row = (entry || {}) as RawVideoData;
        return {
          id: index,
          title: normalizeString(row.title),
          videoPath: normalizeString(row.video_path),
          thumbPath: normalizeString(row.thumb_path),
          summary: normalizeString(row.summary),
          query: normalizeString(row.search_query) || 'Uncategorized',
          updatedAt: normalizeString(row.query_updated_at),
        } satisfies AudioRecord;
      })
      .filter((record) => record.title && record.videoPath);
  } catch (error) {
    console.error('Failed to load audio records:', error);
    return [];
  }
}

export default async function AudioPage() {
  const hdrs = await headers();
  const forwardedProto = (hdrs.get('x-forwarded-proto') || 'http').split(',')[0].trim();
  const hostHeader = (hdrs.get('x-forwarded-host') || hdrs.get('host') || '').split(',')[0].trim();

  let requestMinioBase = '';
  if (hostHeader) {
    try {
      const parsedHost = new URL(`http://${hostHeader}`);
      requestMinioBase = `${forwardedProto || 'http'}://${parsedHost.hostname}:9000`;
    } catch {
      requestMinioBase = '';
    }
  }

  const records = loadAudioRecords();

  return (
    <main className="container audio-page">
      <div style={{ marginBottom: '2rem' }}>
        <Link href="/" className="audio-back-link">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          Back to Home
        </Link>
      </div>

      <header className="audio-header">
        <h1>Audio Review</h1>
        <p>Filter downloaded items by query and listen in a compact audio-first layout.</p>
      </header>

      <AudioClient records={records} requestMinioBase={requestMinioBase} />
    </main>
  );
}
