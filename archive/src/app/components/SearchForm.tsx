'use client';

import { processVideos } from '../actions';
import { useActionState } from 'react';

// Use a simple wrapper form or useActionState if available in React Canary/19 
// Since we are on Next.js 15+, let's try standard form action.

export default function SearchForm() {
    async function handleSubmit(formData: FormData) {
        const result = await processVideos(formData);
        if (result.success) {
            alert("Videos are being processed! Refresh the page in a few minutes.");
        } else {
            alert(result.message);
        }
    }

    return (
        <div className="bg-white p-6 rounded-lg shadow-md mb-8">
            <h2 className="text-xl font-semibold mb-4 text-gray-800">Process New Videos</h2>
            <form action={handleSubmit} className="flex flex-col md:flex-row gap-4">
                <div className="flex-grow">
                    <label htmlFor="search" className="sr-only">Search Keyword</label>
                    <input
                        type="text"
                        name="search"
                        id="search"
                        placeholder="Enter search keyword (e.g. 'AI News')"
                        className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900"
                        required
                    />
                </div>
                <div className="w-full md:w-32">
                    <label htmlFor="limit" className="sr-only">Limit</label>
                    <input
                        type="number"
                        name="limit"
                        id="limit"
                        min="1"
                        max="5"
                        defaultValue="1"
                        className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 text-gray-900"
                        title="Number of videos to download"
                    />
                </div>
                <button
                    type="submit"
                    className="px-6 py-2 bg-indigo-600 text-white font-medium rounded-md hover:bg-indigo-700 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                    Process
                </button>
            </form>
        </div>
    );
}
