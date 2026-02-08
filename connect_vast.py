import os
import subprocess
import sys

def read_env():
    """Read .env file manually to avoid dependencies."""
    env_vars = {}
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    # Remove potential quotes
                    value = value.strip('\'"')
                    env_vars[key.strip()] = value
    return env_vars

def main():
    env = read_env()
    
    user = env.get("VAST_USER", "root")
    host = env.get("VAST_HOST", "ssh3.vast.ai")
    port = env.get("VAST_PORT", "32069")
    key_path = env.get("VAST_SSH_KEY", "")

    # Fix WSL paths for Windows execution
    if sys.platform == "win32" and key_path.startswith("/mnt/"):
        parts = key_path.split("/")
        if len(parts) > 2 and len(parts[2]) == 1:
            drive = parts[2]
            rest = "/".join(parts[3:])
            key_path = f"{drive}:/{rest}"
            print(f"Converted WSL path to Windows: {key_path}")

    # Ports to tunnel (Local:Remote)
    # Using 127.0.0.1 to avoid IPv6/localhost resolution issues
    tunnels = [
        "3000:127.0.0.1:3000", # Next.js App
        "8000:127.0.0.1:8000", # FastAPI
        "8080:127.0.0.1:8081", # Llama Server
        "8233:127.0.0.1:8233", # Temporal Web UI
        "7233:127.0.0.1:7233", # Temporal Service
        "9001:127.0.0.1:9001", # MinIO Console
        "9000:127.0.0.1:9000", # MinIO API
        "1111:127.0.0.1:1111", # ComfyUI
        "6006:127.0.0.1:6006", # Tensorboard
        "8384:127.0.0.1:8384"  # Syncthing
    ]

    print("========================================")
    print(f"Connecting to {user}@{host}:{port}")
    print("Forwarding Ports:")
    for t in tunnels:
        print(f"  - {t}")
    print("========================================")

    cmd = ["ssh", "-p", port, "-o", "StrictHostKeyChecking=no"]
    
    if key_path:
        cmd.extend(["-i", key_path])
    
    # Add tunnels
    for t in tunnels:
        cmd.extend(["-L", t])
    
    cmd.append(f"{user}@{host}")
    cmd.append("-N") # Do not execute a remote command, just forward ports

    print("\nStarting Tunnel... (Press Ctrl+C to stop)")
    print("Once connected, access your services at:")
    print("  -> Web App:       http://localhost:3000")
    print("  -> Temporal UI:   http://localhost:8233")
    print("  -> MinIO Console: http://localhost:9001")
    print("  -> FastAPI Docs:  http://localhost:8000/docs")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nTunnel stopped.")

if __name__ == "__main__":
    main()
