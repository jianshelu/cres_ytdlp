import os
import json
import yt_dlp
import whisper
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

class VideoPipeline:
    def __init__(self, download_dir="downloads", model_size="base"):
        self.download_dir = download_dir
        self.model_size = model_size
        self.model = None
        
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def load_model(self):
        if self.model is None:
            print(f"Loading Whisper model '{self.model_size}'...")
            self.model = whisper.load_model(self.model_size)
            print("Model loaded.")

    def filter_video(self, info):
        """
        Custom filter function for yt-dlp.
        Returns:
            str: Reason for rejection (None if accepted).
        """
        duration = info.get('duration', 0)
        
        # Duration Filter: 3 mins (180s) to 30 mins (1800s)
        if duration < 180 or duration > 1800:
            return f"Duration {duration}s out of range (180-1800s)"

        # License Filter: Check for Creative Commons
        # Note: If passing a direct URL that is already filtered (like User provided),
        # this check relies on metadata presence. 
        license_field = info.get('license', '').lower()
        if 'creative commons' not in license_field:
             # Just in case metadata is missing but it is CC, we might need to be careful.
             # But for now, strict compliance.
            return f"License '{license_field}' is not Creative Commons"

        return None # Accepted

    def download_videos_from_search(self, query, max_results=5):
        """
        Searches and downloads videos matching criteria.
        Now supports direct URLs (including search result URLs).
        """
        if query.startswith("http"):
            search_query = query
        else:
            search_query = f"ytsearch{max_results}:{query}"
        
        ydl_opts = {
            'format': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
            'outtmpl': f'{self.download_dir}/%(title)s.%(ext)s',
            'match_filter': self.filter_video,
            'noplaylist': False, # Allow playlists (search results are playlists)
            'playlistend': max_results,
            'quiet': False, # Set to True to reduce noise, False for debugging
        }

        downloaded_files = []

        print(f"Searching for: {query}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # We need to extract info to get the filename *after* download
                # But search returns a playlist-like object. 
                # We can Iterate matches.
                info = ydl.extract_info(search_query, download=True)
                
                if 'entries' in info:
                    for entry in info['entries']:
                        if entry: # Entry might be None if filtered out
                             filename = ydl.prepare_filename(entry)
                             downloaded_files.append(filename)
                
            except Exception as e:
                print(f"An error occurred during search/download: {e}")

        return downloaded_files

    def download_single_video(self, url):
        """
        Downloads a single video by URL (for testing).
        Note: Filters are NOT applied here to allow testing specific videos.
        """
        ydl_opts = {
            'format': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
            'outtmpl': f'{self.download_dir}/%(title)s.%(ext)s',
            'noplaylist': True,
        }
        
        filepath = None
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                filepath = ydl.prepare_filename(info)
            except Exception as e:
                print(f"Error downloading {url}: {e}")
        
        return filepath

    def transcribe_file(self, filepath):
        """
        Transcribes the video file using Whisper and saves to JSON.
        """
        if not filepath or not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return

        self.load_model()
        
        print(f"Transcribing: {filepath}")
        result = self.model.transcribe(filepath)
        
        # Prepare output filename
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        json_path = os.path.join(self.download_dir, f"{base_name}.json")
        
        with open(json_path, "w", encoding='utf-8') as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
            
        print(f"Transcribed and saved to: {json_path}")


def main():
    pipeline = VideoPipeline()
    
    # Example usage / Test Frame
    print("--- Video Processing Pipeline ---")
    mode = input("Select Mode: [1] Search & Process (Production), [2] Test Single Video: ").strip()
    
    if mode == "1":
        query = "Antigravity"
        print(f"Starting auto-search for '{query}' with CC and duration filters...")
        files = pipeline.download_videos_from_search(query, max_results=10) # Ask for more results as many will be filtered
        
        if not files:
            print("No videos found matching the strict criteria.")
        
        for file in files:
            pipeline.transcribe_file(file)

    elif mode == "2":
        url = input("Enter YouTube URL for testing: ").strip()
        if url:
            print(f"Processing single video: {url}")
            file = pipeline.download_single_video(url)
            if file:
                pipeline.transcribe_file(file)
    else:
        print("Invalid selection.")

if __name__ == "__main__":
    main()
