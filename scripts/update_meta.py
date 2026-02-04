import json
import os
import re
from collections import Counter

STOP_WORDS = set([
    'the', 'and', 'a', 'to', 'of', 'in', 'is', 'it', 'you', 'that', 'this', 'for', 'on', 'with', 'as', 'are', 'was', 'be', 'at', 'or', 'an', 'have', 'from', 'but', 'not', 'by', 'we', 'he', 'she', 'they', 'our', 'their', 'my', 'me', 'us', 'him', 'her', 'them', 'if', 'will', 'can', 'just', 'all', 'so', 'about', 'some', 'no', 'up', 'down', 'out', 'into', 'over', 'now', 'then', 'when', 'where', 'how', 'why', 'what', 'which', 'who', 'get', 'got', 'go', 'going', 'been', 'has', 'had', 'do', 'does', 'did', 'doing', 'one', 'two', 'three', 'like', 'good', 'would', 'could', 'should', 'very', 'really', 'more', 'less', 'than', 'only', 'also', 'too', 'here', 'there'
])

def extract_keywords(text):
    words = re.findall(r'\b\w{3,}\b', text.lower())
    filtered_words = [w for w in words if w not in STOP_WORDS]
    counts = Counter(filtered_words)
    return [{"word": word, "count": count} for word, count in counts.most_common(5)]

def update_metadata(json_path):
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Invalid JSON: {json_path}")
            return

    text = data.get('text', '')
    if not text:
        print(f"No text field found in {json_path}")
        return

    # Basic summary generation (sentences 1-3)
    sentences = re.split(r'(?<=[.!?]) +', text)
    summary = ' '.join(sentences[:3])
    
    data['summary'] = summary
    data['keywords'] = extract_keywords(text)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Updated {json_path}")

if __name__ == "__main__":
    download_dir = "/home/rama/cres_ytdlp/public/downloads"
    json_files = [f for f in os.listdir(download_dir) if f.endswith(".json") and not f.endswith(".info.json")]
    if not json_files:
        print("No transcript JSON files found.")
    else:
        # Sort by modification time to get the latest
        json_files.sort(key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)
        latest_json = os.path.join(download_dir, json_files[0])
        update_metadata(latest_json)
