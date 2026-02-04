import asyncio
import os
import json
import glob
from temporalio.client import Client

# Config
DOWNLOAD_DIR = "web/public/downloads"
TEMPORAL_HOST = "localhost:7233"

async def main():
    print(f"Connecting to Temporal at {TEMPORAL_HOST}...")
    client = await Client.connect(TEMPORAL_HOST)

    if not os.path.exists(DOWNLOAD_DIR):
        print(f"Directory {DOWNLOAD_DIR} not found.")
        return

    # Find all JSONs that look like transcripts
    json_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.json"))
    
    # Filter if arg provided
    import sys
    if len(sys.argv) > 1:
        target_filter = sys.argv[1]
        print(f"Filtering for files containing: {target_filter}")
        json_files = [f for f in json_files if target_filter in os.path.basename(f)]
    
    tasks = []
    
    for json_file in json_files:
        base_name = os.path.basename(json_file)
        if base_name in ['data.json', 'package.json']:
            continue
            
        with open(json_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except:
                print(f"Skipping broken JSON: {json_file}")
                continue
                
        # Check if it's a transcript file
        if 'text' not in data:
            continue
            
        print(f"Queueing reprocess workflow for {base_name}...")
        
        # Start workflow
        # Logic: 
        # Activity 'summarize_content' takes (text, object_name)
        # We pass this tuple as 'params' to the workflow.
        # But 'object_name' implies the video file name usually, 
        # or the ID used for saving. activities.py uses it to derive json path.
        # activities.py: base_name = os.path.splitext(object_name)[0]
        # So passing the json filename as object_name (or video filename) is fine 
        # as long as splitext works.
        # Let's use the video filename if we can guess it, or just base_name (without ext? no with ext).
        # Use timestamp to ensure unique ID for re-runs
        import time
        timestamp = int(time.time())
        workflow_id = f"reprocess-{base_name.replace('.', '-')}-{timestamp}"
        
        # Dispatch workflow
        handle = await client.start_workflow(
            "ReprocessVideoWorkflow",
            args=[(data['text'], base_name)],
            id=workflow_id,
            task_queue="video-processing-queue"
        )
        tasks.append(handle)
        print(f"  -> Workflow ID: {handle.id}")

    print(f"Dispatched {len(tasks)} workflows.")
    
    # Optional: Wait for results (but user might want fire-and-forget)
    # For a test frame, waiting is nice to see completion.
    if tasks:
        print("Waiting for completion...")
        for handle in tasks:
            try:
                await handle.result()
                print(f"  -> {handle.id} completed.")
            except Exception as e:
                print(f"  -> {handle.id} failed: {e}")
                
        # Trigger index refresh once at the end
        print("Refreshing index...")
        # We can run a quick shell command or another workflow/activity
        import subprocess
        subprocess.run(["python3", "generate_index.py"], check=False)
        print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
