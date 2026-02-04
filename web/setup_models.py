import whisper
import os

def download_models():
    print("Pre-downloading Whisper models...")
    # This will download the models to ~/.cache/whisper/
    # We can then move them or let them stay there
    whisper.load_model("base")
    print("Whisper base model downloaded.")

if __name__ == "__main__":
    download_models()
