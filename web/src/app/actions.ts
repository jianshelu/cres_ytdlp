'use server';

import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export async function processVideos(formData: FormData) {
    const search = formData.get('search') as string;
    const limit = formData.get('limit') as string || "1";

    if (!search) {
        return { success: false, message: 'Search query required' };
    }

    try {
        // Call the starter script
        // We use nohup or just fire and forget, but exec waits for completion.
        // Since starter.py now returns quickly (just submitting workflows), we can await it.
        const command = `python3 src/starter.py --search "${search}" --limit ${limit}`;
        console.log(`Executing: ${command}`);

        const { stdout, stderr } = await execAsync(command, { cwd: '/workspace' });
        console.log("Stdout:", stdout);

        if (stderr) console.error("Stderr:", stderr);

        return { success: true, message: 'Workflows submitted successfully' };
    } catch (error: any) {
        console.error("Error executing starter script:", error);
        return { success: false, message: `Error: ${error.message}` };
    }
}
