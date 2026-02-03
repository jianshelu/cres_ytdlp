import yt_dlp
import json

def debug_search(query):
    print(f"Debug Search: {query}")
    ydl_opts = {
        'extract_flat': True, 
        'noplaylist': True,
        'quiet': False
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Explicitly use ytsearch prefix
            # Note: ytsearchN:query
            term = f"ytsearch1:{query}"
            print(f"Extracting: {term}")
            info = ydl.extract_info(term, download=False)
            
            if 'entries' in info:
                print(f"Entries count: {len(list(info['entries']))}")
                for entry in info['entries']:
                    print(f"Entry: {entry.get('title')} - {entry.get('url')}")
            else:
                print("No entries found.")
        except Exception as e:
            print(f"Error: {e}")

debug_search("Google DeepMind")
