import { NextRequest, NextResponse } from 'next/server';

function getUpstreams() {
  const envBase = (process.env.API_URL || '').trim();
  if (!envBase) return ['http://127.0.0.1:8000', 'http://localhost:8000'];
  return [envBase, 'http://127.0.0.1:8000', 'http://localhost:8000'];
}

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get('query') || '';
  const limit = request.nextUrl.searchParams.get('limit') || '50';

  if (!query) {
    return NextResponse.json({ detail: 'query is required' }, { status: 400 });
  }

  const controller = new AbortController();
  // Upstream combined-keyword extraction can exceed 20s on larger query sets.
  const timer = setTimeout(() => controller.abort(), 90000);
  const upstreams = getUpstreams();

  try {
    let lastErr: unknown = null;
    for (const base of upstreams) {
      try {
        const url = `${base}/api/transcriptions?query=${encodeURIComponent(query)}&limit=${encodeURIComponent(limit)}`;
        const res = await fetch(url, {
          method: 'GET',
          cache: 'no-store',
          signal: controller.signal,
        });
        const text = await res.text();
        return new NextResponse(text, {
          status: res.status,
          headers: { 'Content-Type': res.headers.get('Content-Type') || 'application/json' },
        });
      } catch (err) {
        lastErr = err;
      }
    }
    return NextResponse.json(
      { detail: lastErr instanceof Error ? lastErr.message : 'upstream request failed' },
      { status: 502 }
    );
  } finally {
    clearTimeout(timer);
  }
}
