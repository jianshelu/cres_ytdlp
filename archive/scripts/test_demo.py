from main import VideoPipeline

import os

def test_demo():
    print("Running Demo Test...")
    pipeline = VideoPipeline(download_dir="test_downloads")
    
    # Check for existing downloads and transcribe all of them
    if not os.path.exists("test_downloads"):
        print("test_downloads directory not found. Please run the search/download first.")
        return

    video_extensions = ('.mp4', '.mkv', '.webm', '.avi', '.mov')
    files_in_dir = os.listdir("test_downloads")
    video_files = [f for f in files_in_dir if f.lower().endswith(video_extensions)]
    
    if not video_files:
        print("No video files found in test_downloads.")
        return

    print(f"Found {len(video_files)} video(s). Processing transcription...")
    
    for video_file in video_files:
        video_path = os.path.join("test_downloads", video_file)
        base_name = os.path.splitext(video_file)[0]
        json_path = os.path.join("test_downloads", f"{base_name}.json")
        
        if os.path.exists(json_path):
            print(f"Transcription already exists for: {video_file}. Skipping...")
            continue
            
        pipeline.transcribe_file(video_path)
    
    print("All transcriptions complete. Check 'test_downloads' folder.")

if __name__ == "__main__":
    test_demo()
