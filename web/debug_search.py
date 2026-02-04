import yt_dlp
import json

def debug_search(query):
    print(f"Debug Search: {query}")
    ydl_opts = {
        'extract_flat': True, 
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'quiet': False # Enable logs
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
            print("Keys:", info.keys())
            if 'entries' in info:
                print(f"Entries count: {len(info['entries'])}")
                for entry in info['entries']:
                    print(entry)
            else:
                print("No entries found.")
                print(json.dumps(info, indent=2))
        except Exception as e:
            print(f"Error: {e}")

debug_search("Google DeepMind")
