import os
from minio import Minio
from minio.commonconfig import CopySource

# Config
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS = "minioadmin"
MINIO_SECRET = "minioadmin"
SECURE = False

def get_minio_client():
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS,
        secret_key=MINIO_SECRET,
        secure=SECURE
    )

def migrate_data():
    client = get_minio_client()
    target_bucket = "cres"
    
    # Ensure target bucket exists
    if not client.bucket_exists(target_bucket):
        client.make_bucket(target_bucket)
        print(f"Created bucket: {target_bucket}")

    # Define source to target mapping (Bucket -> Prefix)
    # Note: Initially we had 'videos' and 'transcripts' buckets
    # thumbnails were mixed in 'videos'
    
    mapping = {
        "videos": "videos",
        "transcripts": "transcripts"
    }
    
    video_extensions = ('.mp4', '.webm', '.mkv', '.avi', '.mov', '.info.json') # Metadata in videos
    image_extensions = ('.jpg', '.webp', '.png', '.jpeg') # Thumbnails to thumbnails folder

    for source_bucket, default_prefix in mapping.items():
        if not client.bucket_exists(source_bucket):
            print(f"Source bucket {source_bucket} does not exist, skipping.")
            continue
            
        print(f"Migrating objects from bucket: {source_bucket}...")
        objects = client.list_objects(source_bucket, recursive=True)
        
        for obj in objects:
            try:
                source_key = obj.object_name
                filename = os.path.basename(source_key)
                
                # Determine target prefix
                target_prefix = default_prefix
                
                # Special routing for thumbnails out of the 'videos' bucket
                if source_bucket == "videos":
                    if filename.lower().endswith(image_extensions):
                        target_prefix = "thumbnails"
                
                target_key = f"{target_prefix}/{source_key}"
                
                print(f"  Copying {source_bucket}/{source_key} -> {target_bucket}/{target_key}")
                
                # Copy object
                client.copy_object(
                    target_bucket,
                    target_key,
                    CopySource(source_bucket, source_key)
                )
                
                # Delete original
                client.remove_object(source_bucket, source_key)
                
            except Exception as e:
                print(f"  Failed to migrate {obj.object_name}: {e}")

    print("Consolidation migration complete.")

if __name__ == "__main__":
    migrate_data()
