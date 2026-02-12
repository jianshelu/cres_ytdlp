'use client';

import { useState } from 'react';

export default function SearchForm() {
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [message, setMessage] = useState('');
    const [isError, setIsError] = useState(false);

    async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
        e.preventDefault();
        const formData = new FormData(e.currentTarget);
        const search = (formData.get('search') as string || '').trim();
        const limit = Number(formData.get('limit') || 5);
        const maxDurationMinutes = Number(formData.get('maxDurationMinutes') || 10);

        if (!search) {
            setIsError(true);
            setMessage('Search query required');
            return;
        }

        setIsSubmitting(true);
        setMessage('');
        setIsError(false);

        try {
            const response = await fetch('/api/batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: search,
                    limit,
                    max_duration_minutes: maxDurationMinutes,
                }),
            });

            if (!response.ok) {
                const text = await response.text();
                throw new Error(`API ${response.status}: ${text}`);
            }

            const data = await response.json();
            setIsError(false);
            setMessage(`Batch started: ${data.workflow_id || 'N/A'}`);
        } catch (err) {
            setIsError(true);
            setMessage(err instanceof Error ? err.message : 'Failed to start batch process');
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <div>
            <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'nowrap' }}>
                <div style={{ flex: 1, minWidth: '200px' }}>
                    <input
                        type="text"
                        name="search"
                        id="search"
                        placeholder="Search keywords..."
                        style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #444', background: '#222', color: '#fff' }}
                        required
                    />
                </div>
                <div style={{ flex: '0 0 auto' }}>
                    <input
                        type="number"
                        name="limit"
                        id="limit"
                        min="1"
                        max="50"
                        defaultValue="5"
                        placeholder="Limit"
                        style={{ width: '80px', padding: '8px', borderRadius: '4px', border: '1px solid #444', background: '#222', color: '#fff' }}
                    />
                </div>
                <div style={{ flex: '0 0 auto' }}>
                    <input
                        type="number"
                        name="maxDurationMinutes"
                        id="maxDurationMinutes"
                        min="1"
                        max="180"
                        defaultValue="10"
                        placeholder="最大时长(分钟)"
                        title="最大视频时长（分钟）"
                        style={{ width: '110px', padding: '8px', borderRadius: '4px', border: '1px solid #444', background: '#222', color: '#fff' }}
                    />
                </div>
                <button
                    type="submit"
                    disabled={isSubmitting}
                    style={{ padding: '8px 16px', borderRadius: '4px', border: 'none', background: isSubmitting ? '#4b5563' : '#0070f3', color: '#fff', cursor: isSubmitting ? 'not-allowed' : 'pointer' }}
                >
                    {isSubmitting ? 'Starting...' : 'Start Processing'}
                </button>
            </form>
            {message && (
                <p style={{ marginTop: '0.75rem', color: isError ? '#ef4444' : '#22c55e', fontSize: '0.9rem' }}>
                    {message}
                </p>
            )}
        </div>
    );
}
