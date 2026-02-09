import os
import subprocess
import sys


DEFAULT_TUNNELS = [
    "3000:127.0.0.1:3000",  # Next.js
    "8000:127.0.0.1:8000",  # FastAPI
    "8080:127.0.0.1:8081",  # llama.cpp
]


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
                    key = key.lstrip("\ufeff")
                    # Remove potential quotes
                    value = value.strip('\'"')
                    env_vars[key.strip()] = value
    return env_vars


def parse_tunnels(env):
    """
    Parse tunnel list from .env.
    Priority:
    1) CONNECT_TUNNELS (comma-separated local:host:port tuples)
    2) defaults suitable for this project.
    """
    raw = env.get("CONNECT_TUNNELS", "").strip()
    if not raw:
        return list(DEFAULT_TUNNELS)

    tunnels = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        # Allow "3000:3000" shorthand -> local:127.0.0.1:remote
        parts = item.split(":")
        if len(parts) == 2:
            item = f"{parts[0]}:127.0.0.1:{parts[1]}"
        elif len(parts) != 3:
            raise ValueError(f"Invalid CONNECT_TUNNELS item: {item}")
        tunnels.append(item)

    return tunnels or list(DEFAULT_TUNNELS)


def main():
    env = read_env()

    user = env.get("VAST_USER", "root")
    host = env.get("VAST_HOST", "ssh3.vast.ai")
    port = env.get("VAST_PORT", "32069")
    key_path = env.get("VAST_SSH_KEY", "")
    tunnels = parse_tunnels(env)

    # Fix WSL paths for Windows execution
    if sys.platform == "win32" and key_path.startswith("/mnt/"):
        parts = key_path.split("/")
        if len(parts) > 2 and len(parts[2]) == 1:
            drive = parts[2]
            rest = "/".join(parts[3:])
            key_path = f"{drive}:/{rest}"
            print(f"Converted WSL path to Windows: {key_path}")

    print("========================================")
    print(f"Connecting to {user}@{host}:{port}")
    print("Forwarding Ports:")
    for t in tunnels:
        print(f"  - {t}")
    print("========================================")

    cmd = [
        "ssh",
        "-p",
        port,
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ServerAliveInterval=30",
        "-N",
    ]
    
    if key_path:
        cmd.extend(["-i", key_path])
    
    # Add tunnels
    for t in tunnels:
        cmd.extend(["-L", t])
    
    cmd.append(f"{user}@{host}")

    print("\nStarting Tunnel... (Press Ctrl+C to stop)")
    print("Once connected, access your services at:")
    print("  -> Web App:       http://localhost:3000")
    print("  -> FastAPI Docs:  http://localhost:8000/docs")
    print("  -> llama.cpp:     http://localhost:8080")

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nTunnel stopped.")

if __name__ == "__main__":
    main()
