import os
import sys
from minio import Minio

# Config (matching generate_index.py)
DOWNLOAD_DIR = "web/public/downloads"
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS = "minioadmin"
MINIO_SECRET = "minioadmin"
SECURE = False
BUCKET_VIDEOS = "videos"
BUCKET_TRANSCRIPTS = "transcripts"

def get_minio_client():
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS,
        secret_key=MINIO_SECRET,
        secure=SECURE
    )

def migrate():
    if not os.path.exists(DOWNLOAD_DIR):
        print(f"Directory {DOWNLOAD_DIR} does not exist. Nothing to migrate.")
        return

    client = get_minio_client()
    
    # Ensure buckets exist
    for b in [BUCKET_VIDEOS, BUCKET_TRANSCRIPTS]:
        if not client.bucket_exists(b):
            client.make_bucket(b)
            print(f"Created bucket: {b}")

    files = os.listdir(DOWNLOAD_DIR)
    print(f"Found {len(files)} files to check for migration...")
    
    migrated_count = 0
    
    for f in files:
        full_path = os.path.join(DOWNLOAD_DIR, f)
        if os.path.isdir(full_path):
            continue
            
        target_bucket = BUCKET_VIDEOS # Default
        if f.endswith('.json') and not f.endswith('.info.json'):
            target_bucket = BUCKET_TRANSCRIPTS
        
        # Upload
        try:
            # Check if exists (optional, but good for idempotency)
            # Just overwrite to be safe/sure
            client.fput_object(target_bucket, f, full_path)
            print(f"Uploaded {f} -> {target_bucket}")
            
            # Delete local
            os.remove(full_path)
            # print(f"Deleted local {f}")
            migrated_count += 1
            
        except Exception as e:
            print(f"Failed to migrate {f}: {e}")

    print(f"Migration complete. Moved {migrated_count} files.")

if __name__ == "__main__":
    migrate()
