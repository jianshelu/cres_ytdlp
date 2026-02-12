import argparse
import asyncio
import json
import logging
import os
import sys

# Mock activity context if needed, or import functions directly.
# Since activities are decorated, we might need to handle calling them directly.
# In temporalio, calling decorated activity functions directly works fine (they act like normal functions).

# Add project root to path
sys.path.append(os.getcwd())

from src.backend.activities import download_video, transcribe_video, summarize_content, search_videos

# Configure logging to see output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    parser = argparse.ArgumentParser(description="Test separate activities manually.")
    subparsers = parser.add_subparsers(dest="command", help="Activity to run")

    # Download Command
    dl_parser = subparsers.add_parser("download", help="Download a video")
    dl_parser.add_argument("--id", required=True, help="YouTube Video ID (suffix after v=)")

    # Transcribe Command
    tr_parser = subparsers.add_parser("transcribe", help="Transcribe a downloaded object")
    tr_parser.add_argument("--object", required=True, help="MinIO object name (e.g. 'Title.webm')")

    # Summarize Command
    sum_parser = subparsers.add_parser("summarize", help="Summarize a transcript")
    # Summarize Command
    sum_parser = subparsers.add_parser("summarize", help="Summarize a transcript")
    group = sum_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--id", help="Video ID or partial filename to find transcript")
    group.add_argument("--file", help="Exact filename of the transcript (e.g., 'VideoTitle.json')")

    args = parser.parse_args()

    if args.command == "download":
        url = f"https://www.youtube.com/watch?v={args.id}"
        print(f"Testing download_video for URL: {url}")
        try:
             result = download_video(url)
             print(f"Download Result (Object Name): {result}")
        except Exception as e:
            print(f"Error: {e}")

    elif args.command == "transcribe":
        print(f"Testing transcribe_video for object: {args.object}")
        try:
            result = transcribe_video(args.object)
            print(f"Transcription Length: {len(result)} chars")
            print("Preview:", result[:200])
        except Exception as e:
             print(f"Error: {e}")

    elif args.command == "summarize":
        download_dir = "web/public/downloads"
        if not os.path.exists(download_dir):
            print(f"Directory {download_dir} not found.")
            return

        target_file = None
        
        if args.file:
            print(f"Testing summarize_content for File: {args.file}")
            possible_path = os.path.join(download_dir, args.file)
            if os.path.exists(possible_path):
                target_file = possible_path
            else:
                 # Try current dir
                 if os.path.exists(args.file):
                     target_file = args.file
        
        elif args.id:
            print(f"Testing summarize_content for ID/Pattern: {args.id}")
            # Naive search: check if any file contains the ID/string
            import glob
            matches = glob.glob(os.path.join(download_dir, f"*{args.id}*.json"))
            if matches:
                target_file = matches[0]
            else:
                 print(f"No transcript found matching *{args.id}*.json in {download_dir}")
        
        if not target_file:
            print("Could not locate transcript file.")
            print("Available .json files:")
            for f in os.listdir(download_dir):
                if f.endswith(".json"):
                    print(f" - {f}")
            return

        print(f"Using transcript file: {target_file}")

        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            text = data.get('text', '')
            if not text:
                print("No 'text' field found in JSON.")
                return

            object_name = os.path.basename(target_file).replace('.json', '.webm') 
            
            result = await summarize_content((text, object_name))
            print("\n--- Summary Result ---")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
        except Exception as e:
            print(f"Error: {e}")

    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
