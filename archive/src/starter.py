import asyncio
import sys
import argparse
from temporalio.client import Client
import yt_dlp
from temporalio.client import Client
from workflows import VideoProcessingWorkflow

async def main():
    parser = argparse.ArgumentParser(description="Trigger Video Processing Workflow")
    parser.add_argument("--url", help="YouTube URL to process")
    parser.add_argument("--search", help="Search query")
    parser.add_argument("--limit", type=int, default=1, help="Number of videos to download (search mode only)")
    args = parser.parse_args()

    if not args.url and not args.search:
        print("Error: Must provide --url or --search")
        sys.exit(1)

    # Connect to client
    client = await Client.connect("localhost:7233")

    urls_to_process = []
    
    if args.url:
        urls_to_process.append(args.url)
    
    if args.search:
        print(f"Searching for '{args.search}' (Limit: {args.limit})...")
        ydl_opts = {
            'quiet': True, 
            'extract_flat': True, 
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Explicitly use ytsearch prefix
                query = f"ytsearch{args.limit}:{args.search}"
                info = ydl.extract_info(query, download=False)
                if 'entries' in info:
                    for entry in info['entries']:
                         # Filter for actual videos (ignore channels/playlists)
                        url = entry.get('url')
                         # Filter for actual videos (ignore channels/playlists)
                        url = entry.get('url')
                        if url and '/watch?v=' in url:
                            urls_to_process.append(url)
                        elif entry.get('id'):
                             urls_to_process.append(f"https://www.youtube.com/watch?v={entry['id']}")
            except Exception as e:
                print(f"Search failed: {e}")

    print(f"Found {len(urls_to_process)} videos to process.")

    # Execute workflow for each URL
    for url in urls_to_process:
        print(f"Starting workflow for: {url}")
        try:
             # Use video ID as workflow ID dedupe
             # Simple ID extraction or hash
            vid_id = url.split("v=")[-1] if "v=" in url else url[-11:]
            
            handle = await client.start_workflow(
                VideoProcessingWorkflow.run,
                url,
                id=f"video-process-{vid_id}", 
                task_queue="video-processing-queue",
            )
            print(f"Workflow started. ID: {handle.id}, RunID: {handle.run_id}")
        except Exception as e:
            print(f"Failed to start workflow for {url}: {e}")

    # Note: We don't wait for results in batch mode to allow async processing
    if len(urls_to_process) == 1 and args.url:
         # Legacy behavior: wait for result if single URL provided explicitly
         # Re-fetch handle if needed but for now let's just exit
         print("Workflows submitted in background.")
    else:
         print("All workflows submitted.")

if __name__ == "__main__":
    asyncio.run(main())
