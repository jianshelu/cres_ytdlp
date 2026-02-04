import sys
import os
import argparse
import asyncio
import yt_dlp
from temporalio.client import Client

# Add src to path so we can import workflows/activities as if we were inside src
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from workflows import VideoProcessingWorkflow

# Filter Logic
def filter_video_info(info):
    """
    Filter video based on duration and license.
    Returns: True if accepted, False otherwise.
    """
    duration = info.get('duration', 0)
    
    # Duration Filter: 3 mins (180s) to 30 mins (1800s)
    if duration < 180 or duration > 1800:
        print(f"Skipping {info.get('title', 'Unknown')}: Duration {duration}s out of range.")
        return False

    # License Filter: Check for Creative Commons
    license_field = info.get('license', '').lower()
    # Note: yt-dlp metadata for license can be tricky. 
    # Often 'creative commons' is in the license field.
    if 'creative commons' not in license_field:
         print(f"Skipping {info.get('title', 'Unknown')}: License '{license_field}' is not Creative Commons.")
         return False

    return True

async def main():
    parser = argparse.ArgumentParser(description="Video Pipeline Orchestrator")
    parser.add_argument("--url", help="YouTube URL to process (Single video mode)")
    parser.add_argument("--search", help="Search query to find videos")
    parser.add_argument("--limit", type=int, default=1, help="Max videos to process")
    args = parser.parse_args()

    if not args.url and not args.search:
        print("Error: Must provide --url or --search")
        sys.exit(1)

    # Connect to Temporal Client
    # Assuming running locally with default ports
    try:
        client = await Client.connect("localhost:7233")
    except Exception as e:
        print(f"Failed to connect to Temporal server: {e}")
        print("Make sure Temporal is running.")
        sys.exit(1)

    urls_to_process = []

    if args.url:
        # Single URL mode - we might want to minimally validate it or just let the workflow handle it.
        # But original script applied filters even to search results? 
        # Original script: download_single_video -> NO filters. 
        # So we keep that behavior: Direct URL = No checks.
        urls_to_process.append(args.url)

    if args.search:
        print(f"Searching for: {args.search}")
        ydl_opts = {
            'quiet': True,
            'extract_flat': True, # Don't download, just get metadata
            'dump_single_json': True,
        }
        
        # We search for more than limit because we filter some out
        search_limit = args.limit * 5 
        current_count = 0
        
        # Note: 'extract_flat' is fast but might not have full metadata like 'license' or precise 'duration'
        # depending on the extractor. 
        # To get full metadata for filtering, we might need to process entries.
        
        # 1. Broad Search
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                query = f"ytsearch{search_limit}:{args.search}"
                search_results = ydl.extract_info(query, download=False)
            except Exception as e:
                print(f"Search failed: {e}")
                sys.exit(1)

        # 2. Filter Candidates
        if 'entries' in search_results:
            candidates = search_results['entries']
            print(f"Found {len(candidates)} potential candidates. Filtering...")
            
            for entry in candidates:
                if current_count >= args.limit:
                    break
                    
                url = entry.get('url')
                if not url:
                    continue
                
                # We need to fetch full details for this video to check License/Duration reliably
                # extract_flat often misses License.
                
                print(f"Checking metadata for: {entry.get('title', 'Unknown')}")
                # Fetch detailed info for single video (no download)
                try:
                    with yt_dlp.YoutubeDL({'quiet': True}) as ydl_detail:
                         info = ydl_detail.extract_info(url, download=False)
                         
                         if filter_video_info(info):
                             urls_to_process.append(info['webpage_url'])
                             current_count += 1
                             print(f"ACCEPTED: {info['title']}")
                except Exception as e:
                    print(f"Error checking video {url}: {e}")

    print(f"\nDispatching {len(urls_to_process)} workflows...")

    import uuid
    for url in urls_to_process:
        # Deduplication ID
        vid_id = url.split("v=")[-1] if "v=" in url else url[-10:]
        # Use UUID to force new execution for testing/dev
        workflow_id = f"video-process-{vid_id}-{uuid.uuid4().hex[:8]}"
        
        try:
            handle = await client.start_workflow(
                VideoProcessingWorkflow.run,
                url,
                id=workflow_id,
                task_queue="video-processing-queue",
            )
            print(f"Started Workflow: {workflow_id} (RunID: {handle.run_id})")
        except Exception as e:
            print(f"Failed to start workflow {workflow_id}: {e}")

    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
