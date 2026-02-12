'use server';

import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export async function processVideos(formData: FormData) {
    const search = formData.get('search') as string;
    const limit = parseInt((formData.get('limit') as string) || "1", 10);

    if (!search) {
        return { success: false, message: 'Search query required' };
    }

    try {
        console.log(`Submitting batch request: Query='${search}', Limit=${limit}`);

        // Call FastAPI
        // Assuming FastAPI is on localhost:8000 (accessible from Next.js server side if on same network/host)
        // In Docker, if they are in same container, localhost works.
        const response = await fetch("http://localhost:8000/batch", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                query: search,
                limit: limit
            }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error("FastAPI Error:", errorText);
            return { success: false, message: `API Error: ${response.status} ${response.statusText}` };
        }

        const data = await response.json();
        console.log("FastAPI Response:", data);

        return { success: true, message: `Batch process started! Workflow ID: ${data.workflow_id}` };
    } catch (error: any) {
        console.error("Error calling backend API:", error);
        return { success: false, message: `Connection Error: ${error.message}` };
    }
}
